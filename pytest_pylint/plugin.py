# -*- coding: utf-8 -*-
"""
    pytest plugins. Both pylint wrapper and PylintPlugin

"""


from collections import defaultdict
from configparser import ConfigParser, NoSectionError, NoOptionError
from os import makedirs
from os.path import getmtime, exists, join, dirname

from pylint import lint
from pylint.config import PYLINTRC
import pytest
import toml

from .pylint_util import ProgrammaticReporter
from .util import get_rel_path, PyLintException, should_include_file

HISTKEY = 'pylint/mtimes'
PYLINT_CONFIG_CACHE_KEY = 'pylintrc'
FILL_CHARS = 80
MARKER = 'pylint'


def pytest_addoption(parser):
    """Add all our command line options"""
    group = parser.getgroup("pylint")
    group.addoption(
        "--pylint",
        action="store_true", default=False,
        help="run pylint on all"
    )
    group.addoption(
        "--no-pylint",
        action="store_true", default=False,
        help="disable running pylint "
    )

    group.addoption(
        '--pylint-rcfile',
        default=None,
        help='Location of RC file if not pylintrc'
    )
    group.addoption(
        '--pylint-error-types',
        default='CRWEF',
        help='The types of pylint errors to consider failures by letter'
        ', default is all of them (CRWEF).'
    )
    group.addoption(
        '--pylint-jobs',
        default=None,
        help='Specify number of processes to use for pylint'
    )
    group.addoption(
        '--pylint-output-file',
        default=None,
        help='Path to a file where Pylint report will be printed to.'
    )
    group.addoption(
        '--pylint-ignore',
        default=None,
        help='Files/directories that will be ignored'
    )
    group.addoption(
        '--pylint-ignore-patterns',
        default=None,
        help='Files/directories patterns that will be ignored'
    )


def pytest_configure(config):
    """
    Add plugin class.

    :param _pytest.config.Config config: pytest config object
    """
    config.addinivalue_line(
        'markers',
        "{0}: Tests which run pylint.".format(MARKER)
    )
    if config.option.pylint and not config.option.no_pylint:
        pylint_plugin = PylintPlugin(config)
        config.pluginmanager.register(pylint_plugin)


class PylintPlugin:
    """
    The core plugin for pylint
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, config):
        if hasattr(config, 'cache'):
            self.mtimes = config.cache.get(HISTKEY, {})
        else:
            self.mtimes = {}

        self.pylint_files = set()
        self.pylint_messages = defaultdict(list)
        self.pylint_config = None
        self.pylintrc_file = None
        self.pylint_ignore = []
        self.pylint_ignore_patterns = []
        self.pylint_msg_template = None

    def pytest_configure(self, config):
        """Configure pytest after it is already enabled"""

        # Find pylintrc to check ignore list
        pylintrc_file = config.option.pylint_rcfile or PYLINTRC

        if pylintrc_file and not exists(pylintrc_file):
            # The directory of pytest.ini got a chance
            pylintrc_file = join(dirname(str(config.inifile)), pylintrc_file)

        # Try getting ignores from pylintrc since we use pytest
        # collection methods and not pylint's internal mechanism
        if pylintrc_file and exists(pylintrc_file):
            self.pylintrc_file = pylintrc_file

            # Check if pylint config has a different filename or date
            # and invalidate the cache if it has changed.
            pylint_mtime = getmtime(pylintrc_file)
            cache_key = PYLINT_CONFIG_CACHE_KEY + pylintrc_file
            cache_value = self.mtimes.get(cache_key)
            if cache_value is None or cache_value < pylint_mtime:
                self.mtimes = {}
            self.mtimes[cache_key] = pylint_mtime

            if pylintrc_file.endswith(".toml"):
                self._load_pyproject_toml(pylintrc_file)
            else:
                self._load_rc_file(pylintrc_file)

        # Command line arguments take presedence over rcfile ones if set
        if config.option.pylint_ignore is not None:
            self.pylint_ignore = config.option.pylint_ignore.split(',')
        if config.option.pylint_ignore_patterns is not None:
            self.pylint_ignore_patterns = (
                config.option.pylint_ignore_patterns.split(',')
            )

    def _load_rc_file(self, pylintrc_file):
        self.pylint_config = ConfigParser()
        self.pylint_config.read(pylintrc_file)

        try:
            ignore_string = self.pylint_config.get('MASTER', 'ignore')
            if ignore_string:
                self.pylint_ignore = ignore_string.split(',')
        except (NoSectionError, NoOptionError):
            pass

        try:
            ignore_patterns = self.pylint_config.get(
                'MASTER', 'ignore-patterns'
            )
            if ignore_patterns:
                self.pylint_ignore_patterns = ignore_patterns.split(',')
        except (NoSectionError, NoOptionError):
            pass

        try:
            self.pylint_msg_template = self.pylint_config.get(
                'REPORTS', 'msg-template'
            )
        except (NoSectionError, NoOptionError):
            pass

    def _load_pyproject_toml(self, pylintrc_file):
        with open(pylintrc_file, "r") as f_p:
            try:
                content = toml.load(f_p)
            except (TypeError, toml.decoder.TomlDecodeError):
                return

        try:
            self.pylint_config = content["tool"]["pylint"]
        except KeyError:
            return

        master_section = {}
        reports_section = {}
        for key, value in self.pylint_config.items():
            if not master_section and key.lower() == "master":
                master_section = value
            elif not reports_section and key.lower() == "reports":
                reports_section = value

        ignore = master_section.get("ignore")
        if ignore:
            self.pylint_ignore = (
                ignore.split(",")
                if isinstance(ignore, str)
                else ignore
            )
        self.pylint_ignore_patterns = (
            master_section.get("ignore-patterns") or []
        )
        self.pylint_msg_template = reports_section.get("msg-template")

    def pytest_sessionfinish(self, session):
        """
        Save file mtimes to pytest cache.

        :param _pytest.main.Session session: the pytest session object
        """
        if hasattr(session.config, 'cache'):
            session.config.cache.set(HISTKEY, self.mtimes)

    def pytest_collect_file(self, path, parent):
        """Collect files on which pylint should run"""
        if path.ext != ".py":
            return None

        rel_path = get_rel_path(path.strpath, parent.session.fspath.strpath)
        if should_include_file(
                rel_path, self.pylint_ignore, self.pylint_ignore_patterns
        ):
            item = PylintFile.from_parent(
                parent, fspath=path, plugin=self
            )
        else:
            return None

        # Check the cache if we should run it
        if not item.should_skip:
            self.pylint_files.add(rel_path)
        return item

    def pytest_collection_finish(self, session):
        """Lint collected files"""
        if not self.pylint_files:
            return

        jobs = session.config.option.pylint_jobs
        reporter = ProgrammaticReporter()
        # Build argument list for pylint
        args_list = list(self.pylint_files)
        if self.pylintrc_file:
            args_list.append('--rcfile={0}'.format(
                self.pylintrc_file
            ))
        if jobs is not None:
            args_list.append('-j')
            args_list.append(jobs)
        # These allow the user to override the pylint configuration's
        # ignore list
        if self.pylint_ignore:
            args_list.append(
                '--ignore={0}'.format(','.join(self.pylint_ignore))
            )
        if self.pylint_ignore_patterns:
            args_list.append(
                '--ignore-patterns={0}'.format(
                    ','.join(self.pylint_ignore_patterns)
                )
            )
        print('-' * FILL_CHARS)
        print('Linting files')

        # Run pylint over the collected files.

        # Pylint has changed APIs, but we support both
        # pylint: disable=unexpected-keyword-arg
        try:
            # pylint >= 2.5.1 API
            result = lint.Run(args_list, reporter=reporter, exit=False)
        except TypeError:
            # pylint < 2.5.1 API
            result = lint.Run(args_list, reporter=reporter, do_exit=False)
        except RuntimeError:
            return
        messages = result.linter.reporter.data
        # Stores the messages in a dictionary for lookup in tests.
        for message in messages:
            self.pylint_messages[message.path].append(message)
        print('-' * FILL_CHARS)


class PylintFile(pytest.File):
    """File that pylint will run on."""
    rel_path = None  # : str
    plugin = None  # : PylintPlugin
    should_skip = False  # : bool
    mtime = None  # : float

    @classmethod
    def from_parent(cls, parent, *, fspath, plugin):
        # We add the ``plugin`` kwarg to get plugin level information so the
        # signature differs
        # pylint: disable=arguments-differ
        _self = getattr(super(), 'from_parent', cls)(parent, fspath=fspath)
        _self.plugin = plugin

        _self.rel_path = get_rel_path(
            fspath.strpath,
            parent.session.fspath.strpath
        )
        _self.mtime = fspath.mtime()
        prev_mtime = _self.plugin.mtimes.get(_self.rel_path, 0)
        _self.should_skip = (prev_mtime == _self.mtime)

        return _self

    def collect(self):
        """Create a PyLintItem for the File."""
        yield PyLintItem.from_parent(
            parent=self,
            name='PYLINT'
        )


class PyLintItem(pytest.Item):
    """pylint test running class."""

    parent = None  # : PylintFile
    plugin = None  # : PylintPlugin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_marker(MARKER)
        self.plugin = self.parent.plugin

        msg_format = self.plugin.pylint_msg_template
        if msg_format is None:
            self._msg_format = '{C}:{line:3d},{column:2d}: {msg} ({symbol})'
        else:
            self._msg_format = msg_format

    @classmethod
    def from_parent(cls, parent, **kw):
        return getattr(super(), 'from_parent', cls)(parent, **kw)

    def setup(self):
        """Mark unchanged files as SKIPPED."""
        if self.parent.should_skip:
            pytest.skip("file(s) previously passed pylint checks")

    def runtest(self):
        """Check the pylint messages to see if any errors were reported."""
        pylint_output_file = self.config.option.pylint_output_file

        def _loop_errors(writer):
            reported_errors = []
            for error in self.plugin.pylint_messages.get(
                    self.parent.rel_path, []
            ):
                if error.C in self.config.option.pylint_error_types:
                    reported_errors.append(
                        error.format(self._msg_format)
                    )

                writer(
                    '{error_path}:{error_line}: [{error_msg_id}'
                    '({error_symbol}), {error_obj}] '
                    '{error_msg}\n'.format(
                        error_path=error.path,
                        error_line=error.line,
                        error_msg_id=error.msg_id,
                        error_symbol=error.symbol,
                        error_obj=error.obj,
                        error_msg=error.msg,
                    )
                )

            return reported_errors

        if pylint_output_file:
            output_dir = dirname(pylint_output_file)
            if output_dir:
                makedirs(output_dir, exist_ok=True)
            with open(pylint_output_file, 'a') as _file:
                reported_errors = _loop_errors(writer=_file.write)
        else:
            reported_errors = _loop_errors(writer=lambda *args, **kwargs: None)

        if reported_errors:
            raise PyLintException('\n'.join(reported_errors))

        # Update the cache if the item passed pylint.
        self.plugin.mtimes[self.parent.rel_path] = self.parent.mtime

    def repr_failure(self, excinfo, style=None):
        """Handle any test failures by checking that they were ours."""
        # pylint: disable=arguments-differ
        if excinfo.errisinstance(PyLintException):
            return excinfo.value.args[0]
        return super().repr_failure(excinfo)

    def reportinfo(self):
        """Generate our test report"""
        return self.fspath, None, "[pylint] {0}".format(self.parent.rel_path)
