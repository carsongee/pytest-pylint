# -*- coding: utf-8 -*-
"""
Unit testing module for pytest-pylint plugin
"""
import mock


pytest_plugins = ('pytester',)  # pylint: disable=invalid-name


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


def test_pylintrc_file_beside_ini(testdir):
    """
    Verify that a specified pylint rc file will work what placed into pytest
    ini dir.
    """
    non_cwd_dir = testdir.mkdir('non_cwd_dir')

    rcfile = non_cwd_dir.join('foo.rc')
    rcfile.write("""
[FORMAT]

max-line-length=3
""")

    inifile = non_cwd_dir.join('foo.ini')
    inifile.write("""
[pytest]
addopts = --pylint --pylint-rcfile={0}
""".format(rcfile.basename))

    pyfile = testdir.makepyfile("""import sys""")

    result = testdir.runpytest(
        pyfile.strpath
    )
    assert 'Line too long (10/3)' not in result.stdout.str()

    result = testdir.runpytest(
        '-c', inifile.strpath, pyfile.strpath
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


def test_get_rel_path():
    """
    Verify our relative path function.
    """
    from pytest_pylint import get_rel_path
    correct_rel_path = 'How/Are/You/blah.py'
    path = '/Hi/How/Are/You/blah.py'
    parent_path = '/Hi/'
    assert get_rel_path(path, parent_path) == correct_rel_path

    parent_path = '/Hi'
    assert get_rel_path(path, parent_path) == correct_rel_path


def test_multiple_jobs(testdir):
    """
    Assert that the jobs argument is passed through to pylint if provided
    """
    testdir.makepyfile("""import sys""")
    with mock.patch('pytest_pylint.lint.Run') as run_mock:
        jobs = 0
        testdir.runpytest(
            '--pylint', '--pylint-jobs={0}'.format(jobs)
        )
    assert run_mock.call_count == 1
    assert run_mock.call_args[0][0][-2:] == ['-j', str(jobs)]


def test_no_multiple_jobs(testdir):
    """
    If no jobs argument is specified it should not appear in pylint arguments
    """
    testdir.makepyfile("""import sys""")
    with mock.patch('pytest_pylint.lint.Run') as run_mock:
        testdir.runpytest('--pylint')
    assert run_mock.call_count == 1
    assert '-j' not in run_mock.call_args[0][0]
