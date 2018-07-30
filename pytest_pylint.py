"""Pylint plugin for py.test"""
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function
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


class PyLintException(Exception):
    """Exception to raise if a file has a specified pylint error"""
    pass


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
            session.pylint_msg_template = session.pylint_config.get(
                'REPORTS', 'msg-template'
            )
        except (NoSectionError, NoOptionError):
            pass


def pytest_collect_file(path, parent):
    """Collect files on which pylint should run"""
    config = parent.config
    if not config.option.pylint or config.option.no_pylint:
        return None
    if path.ext != ".py":
        return None
    rel_path = get_rel_path(path.strpath, parent.fspath.strpath)
    if parent.pylint_config is None:
        parent.pylint_files.add(rel_path)
        # No pylintrc, therefore no ignores, so return the item.
        return PyLintItem(path, parent)

    if not any(basename in rel_path for basename in parent.pylint_ignore):
        parent.pylint_files.add(rel_path)
        return PyLintItem(
            path, parent, parent.pylint_msg_template, parent.pylintrc_file
        )
    return None


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
    # pylint: disable=no-member,super-on-old-class,abstract-method
    def __init__(self, fspath, parent, msg_format=None, pylintrc_file=None):
        super(PyLintItem, self).__init__(fspath, parent)

        self.add_marker("pylint")
        self.rel_path = get_rel_path(fspath.strpath, parent.fspath.strpath)

        if msg_format is None:
            self._msg_format = '{C}:{line:3d},{column:2d}: {msg} ({symbol})'
        else:
            self._msg_format = msg_format

        self.pylintrc_file = pylintrc_file

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

    def repr_failure(self, excinfo):
        """Handle any test failures by checkint that they were ours."""
        if excinfo.errisinstance(PyLintException):
            return excinfo.value.args[0]
        return super(PyLintItem, self).repr_failure(excinfo)

    def reportinfo(self):
        """Generate our test report"""
        return self.fspath, None, "[pylint] {0}".format(self.name)
