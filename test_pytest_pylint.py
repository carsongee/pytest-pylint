# -*- coding: utf-8 -*-
"""
Unit testing module for pytest-pylti plugin
"""

pytest_plugins = 'pytester',  # pylint: disable=invalid-name


def test_basic(testdir):
    """Verify basic pylint checks"""
    testdir.makepyfile("""import sys""")
    result = testdir.runpytest('--pylint')
    assert 'Missing module docstring' in result.stdout.str()
    assert 'Unused import sys' in result.stdout.str()
    assert 'Final newline missing' in result.stdout.str()
    assert 'passed' not in result.stdout.str()


def test_error_control(testdir):
    """Verify that error types are configurable"""
    testdir.makepyfile("""import sys""")
    result = testdir.runpytest('--pylint', '--pylint-error-types=EF')
    assert '1 passed' in result.stdout.str()


def test_pylintrc_file(testdir):
    """Verify that a specified pylint rc file will work."""
    rcfile = testdir.makefile('rc', """
[FORMAT]

max-line-length=3
""")
    testdir.makepyfile("""import sys""")
    result = testdir.runpytest(
        '--pylint', '--pylint-rcfile={0}'.format(rcfile.strpath)
    )
    assert 'Line too long (10/3)' in result.stdout.str()


def test_pylintrc_ignore(testdir):
    """Verify that a pylintrc file with ignores will work."""
    rcfile = testdir.makefile('rc', """
[MASTER]

ignore = test_pylintrc_ignore.py
""")
    testdir.makepyfile("""import sys""")
    result = testdir.runpytest(
        '--pylint', '--pylint-rcfile={0}'.format(rcfile.strpath)
    )
    assert 'collected 0 items' in result.stdout.str()


def test_pylintrc_msg_template(testdir):
    """Verify that msg-template from pylintrc file is handled."""
    rcfile = testdir.makefile('rc', """
[REPORTS]

msg-template=start {msg_id} end
""")
    testdir.makepyfile("""import sys""")
    result = testdir.runpytest(
        '--pylint', '--pylint-rcfile={0}'.format(rcfile.strpath)
    )
    assert 'start W0611 end' in result.stdout.str()
