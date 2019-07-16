"""Pylint plugin for py.test"""
from __future__ import absolute_import, print_function, unicode_literals
import re
from os import sep
from os.path import exists, join, dirname
import sys
from six.moves.configparser import (  # pylint: disable=import-error
    ConfigParser,
    NoSectionError,
    NoOptionError
)

from pylint import lint
from pylint.config import PYLINTRC
from pylint.interfaces import IReporter
from pylint.reporters import BaseReporter
import pytest

HISTKEY = 'pylint/mtimes'


class PyLintException(Exception):
    """Exception to raise if a file has a specified pylint error"""


class ProgrammaticReporter(BaseReporter):
    """Reporter that replaces output with storage in list of dictionaries"""

    __implements__ = IReporter
    extension = 'prog'

    def __init__(self, output=None):
        BaseReporter.__init__(self, output)
        self.current_module = None
        self.data = []

    def add_message(self, msg_id, location, msg):
        """Deprecated, but required"""
        raise NotImplementedError

    def handle_message(self, msg):
        """Get message and append to our data structure"""
        self.data.append(msg)

    def _display(self, layout):
        """launch layouts display"""

    def on_set_current_module(self, module, filepath):
        """Hook called when a module starts to be analysed."""
        print('.', end='')
        sys.stdout.flush()

    def on_close(self, stats, previous_stats):
        """Hook called when all modules finished analyzing."""
        # print a new line when pylint is finished
        print('')


def get_rel_path(path, parent_path):
    """
    Give the path to object relative to ``parent_path``.
    """
    replaced_path = path.replace(parent_path, '', 1)
    if replaced_path[0] == sep:
        rel_path = replaced_path[1:]
    else:
        rel_path = replaced_path
    return rel_path


def pytest_addoption(parser):
    """Add all our command line options"""
    group = parser.getgroup("general")
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


def pytest_sessionstart(session):
    """Storing pylint settings on the session"""
    session.pylint_files = set()
    session.pylint_messages = {}
    session.pylint_config = None
    session.pylintrc_file = None
    session.pylint_ignore = []
    session.pylint_ignore_patterns = []
    session.pylint_msg_template = None
    config = session.config

    # Find pylintrc to check ignore list
    pylintrc_file = config.option.pylint_rcfile or PYLINTRC

    if pylintrc_file and not exists(pylintrc_file):
        # The directory of pytest.ini got a chance
        pylintrc_file = join(dirname(str(config.inifile)), pylintrc_file)

    if pylintrc_file and exists(pylintrc_file):
        session.pylintrc_file = pylintrc_file
        session.pylint_config = ConfigParser()
        session.pylint_config.read(pylintrc_file)

        try:
            ignore_string = session.pylint_config.get('MASTER', 'ignore')
            if ignore_string:
                session.pylint_ignore = ignore_string.split(',')
        except (NoSectionError, NoOptionError):
            pass

        try:
            session.pylint_ignore_patterns = session.pylint_config.get(
                'MASTER', 'ignore-patterns')
        except (NoSectionError, NoOptionError):
            pass

        try:
            session.pylint_msg_template = session.pylint_config.get(
                'REPORTS', 'msg-template'
            )
        except (NoSectionError, NoOptionError):
            pass


def include_file(path, ignore_list, ignore_patterns=None):
    """Checks if a file should be included in the collection."""
    if ignore_patterns:
        for pattern in ignore_patterns:
            if re.match(pattern, path):
                return False
    parts = path.split(sep)
    return not set(parts) & set(ignore_list)


def pytest_configure(config):
    """
    Add a plugin to cache file mtimes.

    :param _pytest.config.Config config: pytest config object
    """
    if config.option.pylint:
        config.pylint = PylintPlugin(config)
        config.pluginmanager.register(config.pylint)
    config.addinivalue_line('markers', "pylint: Tests which run pylint.")


class PylintPlugin(object):
    """
    A Plugin object for pylint, which loads and records file mtimes.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, config):
        if hasattr(config, 'cache'):
            self.mtimes = config.cache.get(HISTKEY, {})
        else:
            self.mtimes = {}

    def pytest_sessionfinish(self, session):
        """
        Save file mtimes to pytest cache.

        :param _pytest.main.Session session: the pytest session object
        """
        if hasattr(session.config, 'cache'):
            session.config.cache.set(HISTKEY, self.mtimes)


def pytest_collect_file(path, parent):
    """Collect files on which pylint should run"""
    config = parent.session.config
    if not config.option.pylint or config.option.no_pylint:
        return None
    if path.ext != ".py":
        return None
    rel_path = get_rel_path(path.strpath, parent.session.fspath.strpath)
    session = parent.session
    if session.pylint_config is None:
        # No pylintrc, therefore no ignores, so return the item.
        item = PyLintItem(path, parent)
    elif include_file(rel_path, session.pylint_ignore,
                      session.pylint_ignore_patterns):
        item = PyLintItem(
            path, parent, session.pylint_msg_template, session.pylintrc_file
        )
    else:
        return None
    if not item.should_skip:
        session.pylint_files.add(rel_path)
    return item


def pytest_collection_finish(session):
    """Lint collected files and store messages on session."""
    if not session.pylint_files:
        return

    jobs = session.config.option.pylint_jobs
    reporter = ProgrammaticReporter()
    # Build argument list for pylint
    args_list = list(session.pylint_files)
    if session.pylintrc_file:
        args_list.append('--rcfile={0}'.format(
            session.pylintrc_file
        ))
    if jobs is not None:
        args_list.append('-j')
        args_list.append(jobs)
    print('-' * 65)
    print('Linting files')
    # Disabling keyword arg to handle both 1.x and 2.x pylint API calls
    # pylint: disable=unexpected-keyword-arg

    # Run pylint over the collected files.
    try:
        result = lint.Run(args_list, reporter=reporter, exit=False)
    except TypeError:  # Handle pylint 2.0 API
        result = lint.Run(args_list, reporter=reporter, do_exit=False)
    except RuntimeError:
        return
    messages = result.linter.reporter.data
    # Stores the messages in a dictionary for lookup in tests.
    for message in messages:
        if message.path not in session.pylint_messages:
            session.pylint_messages[message.path] = []
        session.pylint_messages[message.path].append(message)
    print('-' * 65)


class PyLintItem(pytest.Item, pytest.File):
    """pylint test running class."""
    # pylint doesn't deal well with dynamic modules and there isn't an
    # astng plugin for pylint in pypi yet, so we'll have to disable
    # the checks.
    # pylint: disable=no-member,abstract-method
    def __init__(self, fspath, parent, msg_format=None, pylintrc_file=None):
        super(PyLintItem, self).__init__(fspath, parent)

        self.add_marker("pylint")
        self.rel_path = get_rel_path(
            fspath.strpath,
            parent.session.fspath.strpath
        )

        if msg_format is None:
            self._msg_format = '{C}:{line:3d},{column:2d}: {msg} ({symbol})'
        else:
            self._msg_format = msg_format

        self.pylintrc_file = pylintrc_file
        self.__mtime = self.fspath.mtime()
        prev_mtime = self.config.pylint.mtimes.get(self.nodeid, 0)
        self.should_skip = (prev_mtime == self.__mtime)

    def setup(self):
        """Mark unchanged files as SKIPPED."""
        if self.should_skip:
            pytest.skip("file(s) previously passed pylint checks")

    def runtest(self):
        """Check the pylint messages to see if any errors were reported."""
        reported_errors = []
        for error in self.session.pylint_messages.get(self.rel_path, []):
            if error.C in self.config.option.pylint_error_types:
                reported_errors.append(
                    error.format(self._msg_format)
                )
        if reported_errors:
            raise PyLintException('\n'.join(reported_errors))

        # Update the cache if the item passed pylint.
        self.config.pylint.mtimes[self.nodeid] = self.__mtime

    def repr_failure(self, excinfo):
        """Handle any test failures by checkint that they were ours."""
        if excinfo.errisinstance(PyLintException):
            return excinfo.value.args[0]
        return super(PyLintItem, self).repr_failure(excinfo)

    def reportinfo(self):
        """Generate our test report"""
        return self.fspath, None, "[pylint] {0}".format(self.rel_path)
