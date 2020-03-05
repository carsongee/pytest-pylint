# -*- coding: utf-8 -*-
"""Pylint plugin for py.test"""

from os.path import exists, join, dirname
from configparser import ConfigParser, NoSectionError, NoOptionError

from pylint import lint
from pylint.config import PYLINTRC
import pytest

from .pylint_util import ProgrammaticReporter
from .util import get_rel_path, PyLintException, should_include_file

HISTKEY = 'pylint/mtimes'
FILL_CHARS = 80


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


def pytest_configure(config):
    """
    Add plugin class.

    :param _pytest.config.Config config: pytest config object
    """
    config.addinivalue_line('markers', "pylint: Tests which run pylint.")
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
        self.pylint_messages = {}
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
        # collection methods and not pyint's internal
        if pylintrc_file and exists(pylintrc_file):
            self.pylintrc_file = pylintrc_file
            self.pylint_config = ConfigParser()
            self.pylint_config.read(pylintrc_file)

            try:
                ignore_string = self.pylint_config.get('MASTER', 'ignore')
                if ignore_string:
                    self.pylint_ignore = ignore_string.split(',')
            except (NoSectionError, NoOptionError):
                pass

            try:
                self.pylint_ignore_patterns = self.pylint_config.get(
                    'MASTER', 'ignore-patterns')
            except (NoSectionError, NoOptionError):
                pass

            try:
                self.pylint_msg_template = self.pylint_config.get(
                    'REPORTS', 'msg-template'
                )
            except (NoSectionError, NoOptionError):
                pass

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
        if self.pylint_config is None:
            # No pylintrc, therefore no ignores, so return the item.
            item = PyLintItem(path, parent, pylint_plugin=self)
        elif should_include_file(
                rel_path, self.pylint_ignore, self.pylint_ignore_patterns
        ):
            item = PyLintItem(path, parent, pylint_plugin=self)
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
        print('-' * FILL_CHARS)
        print('Linting files')

        # Run pylint over the collected files.
        try:
            result = lint.Run(args_list, reporter=reporter, do_exit=False)
        except RuntimeError:
            return
        messages = result.linter.reporter.data
        # Stores the messages in a dictionary for lookup in tests.
        for message in messages:
            if message.path not in self.pylint_messages:
                self.pylint_messages[message.path] = []
            self.pylint_messages[message.path].append(message)
        print('-' * FILL_CHARS)


class PyLintItem(pytest.Item, pytest.File):
    """pylint test running class."""
    # pylint doesn't deal well with dynamic modules and there isn't an
    # astng plugin for pylint in pypi yet, so we'll have to disable
    # the checks.
    # pylint: disable=no-member,abstract-method
    def __init__(self, fspath, parent, pylint_plugin):
        super().__init__(fspath, parent)

        self.add_marker('pylint')
        self.rel_path = get_rel_path(
            fspath.strpath,
            parent.session.fspath.strpath
        )
        self.plugin = pylint_plugin

        msg_format = self.plugin.pylint_msg_template
        if msg_format is None:
            self._msg_format = '{C}:{line:3d},{column:2d}: {msg} ({symbol})'
        else:
            self._msg_format = msg_format

        self._nodeid += '::PYLINT'
        self.mtime = self.fspath.mtime()
        prev_mtime = self.plugin.mtimes.get(self.name, 0)
        self.should_skip = (prev_mtime == self.mtime)

    def setup(self):
        """Mark unchanged files as SKIPPED."""
        if self.should_skip:
            pytest.skip("file(s) previously passed pylint checks")

    def runtest(self):
        """Check the pylint messages to see if any errors were reported."""
        pylint_output_file = self.config.option.pylint_output_file

        def _loop_errors(writer):
            reported_errors = []
            for error in self.plugin.pylint_messages.get(self.rel_path, []):
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
            with open(pylint_output_file, 'a') as _file:
                reported_errors = _loop_errors(writer=_file.write)
        else:
            reported_errors = _loop_errors(writer=lambda *args, **kwargs: None)

        if reported_errors:
            raise PyLintException('\n'.join(reported_errors))

        # Update the cache if the item passed pylint.
        self.plugin.mtimes[self.name] = self.mtime

    def repr_failure(self, excinfo, style=None):
        """Handle any test failures by checking that they were ours."""
        # pylint: disable=arguments-differ
        if excinfo.errisinstance(PyLintException):
            return excinfo.value.args[0]
        return super().repr_failure(excinfo)

    def reportinfo(self):
        """Generate our test report"""
        return self.fspath, None, "[pylint] {0}".format(self.rel_path)
