"""Pylint plugin for py.test"""
from __future__ import unicode_literals
from __future__ import absolute_import

import pytest

from pylint import lint
from pylint.interfaces import IReporter
from pylint.reporters import BaseReporter


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
        pass


def pytest_addoption(parser):
    """Add all our command line options"""
    group = parser.getgroup("general")
    group.addoption(
        "--pylint",
        action="store_true", default=False,
        help="run pylint on all"
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


def pytest_collect_file(path, parent):
    """Handle running pylint on files discovered"""
    config = parent.config
    if path.ext == ".py":
        if config.option.pylint:
            return PyLintItem(path, parent)


class PyLintException(Exception):
    """Exception to raise if a file has a specified pylint error"""
    pass


class PyLintItem(pytest.Item, pytest.File):
    """pylint test running class."""
    # pylint doesn't deal well with dynamic modules and there isn't an
    # astng plugin for pylint in pypi yet, so we'll have to disable
    # the checks.
    # pylint: disable=no-member,no-init,super-on-old-class
    def runtest(self):
        """Setup and run pylint for the given test file."""
        reporter = ProgrammaticReporter()
        # Build argument list for pylint
        args_list = [str(self.fspath)]
        if self.config.option.pylint_rcfile:
            args_list.append('--rcfile={0}'.format(
                self.config.option.pylint_rcfile
            ))
        lint.Run(args_list, reporter=reporter, exit=False)
        reported_errors = []
        for error in reporter.data:
            if error.C in self.config.option.pylint_error_types:
                reported_errors.append(
                    '{msg.C}:{msg.line:3d},{msg.column:2d}: '
                    '{msg.msg} ({msg.symbol})'.format(msg=error)
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
