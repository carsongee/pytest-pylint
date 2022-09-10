# -*- coding: utf-8 -*-
"""
Unit testing module for pytest-pylint plugin
"""
import os
import re
from textwrap import dedent
from unittest import mock

import pylint.config
import pytest

pytest_plugins = ("pytester",)  # pylint: disable=invalid-name


def test_basic(testdir):
    """Verify basic pylint checks"""
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint")
    assert "Missing module docstring" in result.stdout.str()
    assert "Unused import sys" in result.stdout.str()
    assert "Final newline missing" in result.stdout.str()
    assert "passed, " not in result.stdout.str()
    assert "1 failed" in result.stdout.str()
    assert "Linting files" in result.stdout.str()


def test_nodeid(testdir):
    """Verify our nodeid adds a suffix"""
    testdir.makepyfile(app="import sys")
    result = testdir.runpytest("--pylint", "--collectonly", "--verbose")
    for expected in "<PylintFile app.py>", "<PyLintItem PYLINT>":
        assert expected in result.stdout.str()


def test_nodeid_no_dupepath(testdir):
    """Verify we don't duplicate the node path in our node id."""
    testdir.makepyfile(app="import sys")
    result = testdir.runpytest("--pylint", "--verbose")
    assert re.search(
        r"^FAILED\s+app\.py::PYLINT$", result.stdout.str(), flags=re.MULTILINE
    )


def test_subdirectories(testdir):
    """Verify pylint checks files in subdirectories"""
    subdir = testdir.mkpydir("mymodule")
    testfile = subdir.join("test_file.py")
    testfile.write("import sys")
    result = testdir.runpytest("--pylint")
    assert "[pylint] mymodule/test_file.py" in result.stdout.str()
    assert "Missing module docstring" in result.stdout.str()
    assert "Unused import sys" in result.stdout.str()
    assert "Final newline missing" in result.stdout.str()
    assert "1 failed" in result.stdout.str()
    assert "Linting files" in result.stdout.str()


def test_disable(testdir):
    """Verify basic pylint checks"""
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint --no-pylint")
    assert "Final newline missing" not in result.stdout.str()
    assert "Linting files" not in result.stdout.str()


def test_error_control(testdir):
    """Verify that error types are configurable"""
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint", "--pylint-error-types=EF")
    assert "1 passed" in result.stdout.str()


def test_pylintrc_file(testdir):
    """Verify that a specified pylint rc file will work."""
    rcfile = testdir.makefile(
        ".rc",
        """
        [FORMAT]

        max-line-length=3
        """,
    )
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "Line too long (10/3)" in result.stdout.str()


def test_pylintrc_file_toml(testdir):
    """Verify that pyproject.toml can be used as a pylint rc file."""
    rcfile = testdir.makefile(
        ".toml",
        pylint="""
        [tool.pylint.FORMAT]
        max-line-length = "3"
        """,
    )
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    # Parsing changed from integer to string in pylint >=2.5. Once
    # support is dropped <2.5 this is removable
    if "should be of type int" in result.stdout.str():
        rcfile = testdir.makefile(
            ".toml",
            pylint="""
            [tool.pylint.FORMAT]
            max-line-length = 3
            """,
        )
        result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")

    assert "Line too long (10/3)" in result.stdout.str()


def test_pylintrc_file_pyproject_toml(testdir):
    """Verify that pyproject.toml can be auto-detected as a pylint rc file."""
    # pylint only auto-detects pyproject.toml from 2.5 onwards
    if not hasattr(pylint.config, "find_default_config_files"):
        return
    testdir.makefile(
        ".toml",
        pyproject="""
        [tool.pylint.FORMAT]
        max-line-length = "3"
        """,
    )
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint")

    assert "Line too long (10/3)" in result.stdout.str()


def test_pylintrc_file_beside_ini(testdir):
    """
    Verify that a specified pylint rc file will work when placed into pytest
    ini dir.
    """
    non_cwd_dir = testdir.mkdir("non_cwd_dir")

    rcfile = non_cwd_dir.join("foo.rc")
    rcfile.write(
        dedent(
            """
        [FORMAT]

        max-line-length=3
        """
        )
    )
    inifile = non_cwd_dir.join("foo.ini")
    inifile.write(
        dedent(
            f"""
        [pytest]
        addopts = --pylint --pylint-rcfile={rcfile.strpath}
        """
        )
    )
    # Per https://github.com/pytest-dev/pytest/pull/8537/ the rootdir
    # is now wherever the ini file is, so we need to make sure our
    # Python file is the right directory.
    pyfile_base = testdir.makepyfile("import sys")
    pyfile = non_cwd_dir / pyfile_base.basename
    pyfile_base.rename(pyfile)

    result = testdir.runpytest(pyfile.strpath)
    assert "Line too long (10/3)" not in result.stdout.str()

    result = testdir.runpytest("-c", inifile.strpath, pyfile.strpath)
    assert "Line too long (10/3)" in result.stdout.str()


@pytest.mark.parametrize("rcformat", ("ini", "toml", "simple_toml"))
@pytest.mark.parametrize("sectionname", ("main", "master"))
def test_pylintrc_ignore(testdir, rcformat, sectionname):
    """Verify that a pylintrc file with ignores will work."""
    if rcformat == "toml":
        rcfile = testdir.makefile(
            ".toml",
            f"""
            [tool.pylint.{sectionname}]
            ignore = ["test_pylintrc_ignore.py", "foo.py"]
            """,
        )
    elif rcformat == "simple_toml":
        rcfile = testdir.makefile(
            ".toml",
            f"""
            [tool.pylint.{sectionname.upper()}]
            ignore = "test_pylintrc_ignore.py,foo.py"
            """,
        )
    else:
        rcfile = testdir.makefile(
            ".rc",
            f"""
            [{sectionname.upper()}]

            ignore = test_pylintrc_ignore.py
            """,
        )
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "collected 0 items" in result.stdout.str()


@pytest.mark.parametrize("rcformat", ("ini", "toml"))
def test_pylintrc_msg_template(testdir, rcformat):
    """Verify that msg-template from pylintrc file is handled."""
    if rcformat == "toml":
        rcfile = testdir.makefile(
            ".toml",
            """
            [tool.pylint.REPORTS]
            msg-template = "start {msg_id} end"
            """,
        )
    else:
        rcfile = testdir.makefile(
            ".rc",
            """
            [REPORTS]

            msg-template=start {msg_id} end
            """,
        )
    testdir.makepyfile("import sys")
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "start W0611 end" in result.stdout.str()


def test_multiple_jobs(testdir):
    """
    Assert that the jobs argument is passed through to pylint if provided
    """
    testdir.makepyfile("import sys")
    with mock.patch("pytest_pylint.plugin.lint.Run") as run_mock:
        jobs = 0
        testdir.runpytest("--pylint", f"--pylint-jobs={jobs}")
    assert run_mock.call_count == 1
    assert run_mock.call_args[0][0][-2:] == ["-j", str(jobs)]


def test_no_multiple_jobs(testdir):
    """
    If no jobs argument is specified it should not appear in pylint arguments
    """
    testdir.makepyfile("import sys")
    with mock.patch("pytest_pylint.plugin.lint.Run") as run_mock:
        testdir.runpytest("--pylint")
    assert run_mock.call_count == 1
    assert "-j" not in run_mock.call_args[0][0]


def test_skip_checked_files(testdir):
    """
    Test a file twice which can pass pylint.
    The 2nd time should be skipped.
    """
    testdir.makepyfile(
        "#!/usr/bin/env python",
        '"""A hello world script."""',
        "",
        "from __future__ import print_function",
        "",
        'print("Hello world!")  # pylint: disable=missing-final-newline',
    )
    # The 1st time should be passed
    result = testdir.runpytest("--pylint")
    assert "1 passed" in result.stdout.str()

    # The 2nd time should be skipped
    result = testdir.runpytest("--pylint")
    assert "1 skipped" in result.stdout.str()

    # Always be passed when cacheprovider disabled
    result = testdir.runpytest("--pylint", "-p", "no:cacheprovider")
    assert "1 passed" in result.stdout.str()


def test_invalidate_cache_when_config_changes(testdir):
    """If pylintrc changes, no cache should apply."""
    rcfile = testdir.makefile(
        ".rc", "[MESSAGES CONTROL]", "disable=missing-final-newline"
    )
    testdir.makepyfile('"""hi."""')
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "1 passed" in result.stdout.str()

    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "1 skipped" in result.stdout.str()

    # Change RC file entirely
    alt_rcfile = testdir.makefile(
        ".rc", alt="[MESSAGES CONTROL]\ndisable=unbalanced-tuple-unpacking"
    )
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={alt_rcfile.strpath}")
    assert "1 failed" in result.stdout.str()

    # Change contents of RC file
    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "1 passed" in result.stdout.str()

    with open(rcfile, "w", encoding="utf-8"):
        pass

    result = testdir.runpytest("--pylint", f"--pylint-rcfile={rcfile.strpath}")
    assert "1 failed" in result.stdout.str()


def test_output_file(testdir):
    """Verify pylint report output"""
    testdir.makepyfile("import sys")
    testdir.runpytest("--pylint", "--pylint-output-file=pylint.report")
    output_file = os.path.join(testdir.tmpdir.strpath, "pylint.report")
    assert os.path.isfile(output_file)

    with open(output_file, "r", encoding="utf-8") as _file:
        report = _file.read()

    assert (
        "test_output_file.py:1: [C0304(missing-final-newline), ] Final "
        "newline missing"
    ) in report

    assert (
        "test_output_file.py:1: [C0111(missing-docstring), ] Missing "
        "module docstring"
    ) in report or (
        "test_output_file.py:1: [C0114(missing-module-docstring), ] Missing "
        "module docstring"
    ) in report

    assert (
        "test_output_file.py:1: [W0611(unused-import), ] Unused import sys"
    ) in report


def test_output_file_makes_dirs(testdir):
    """Verify output works with folders properly."""
    testdir.makepyfile("import sys")
    output_path = os.path.join("reports", "pylint.report")
    testdir.runpytest("--pylint", f"--pylint-output-file={output_path}")
    output_file = os.path.join(testdir.tmpdir.strpath, output_path)
    assert os.path.isfile(output_file)
    # Run again to make sure we don't crash trying to make a dir that exists
    testdir.runpytest("--pylint", f"--pylint-output-file={output_path}")


@pytest.mark.parametrize(
    "arg_opt_name, arg_opt_value",
    [("ignore", "test_cmd_line_ignore.py"), ("ignore-patterns", ".+_ignore.py")],
    ids=["ignore", "ignore-patterns"],
)
def test_cmd_line_ignore(testdir, arg_opt_name, arg_opt_value):
    """Verify that cmd line args ignores will work."""
    testdir.makepyfile(test_cmd_line_ignore="import sys")
    result = testdir.runpytest("--pylint", f"--pylint-{arg_opt_name}={arg_opt_value}")
    assert "collected 0 items" in result.stdout.str()
    assert "Unused import sys" not in result.stdout.str()


@pytest.mark.parametrize(
    "arg_opt_name, arg_opt_value",
    [("ignore", "test_cmd_line_ignore_pri_arg.py"), ("ignore-patterns", ".*arg.py$")],
    ids=["ignore", "ignore-patterns"],
)
@pytest.mark.parametrize("sectionname", ("main", "master"))
def test_cmd_line_ignore_pri(testdir, arg_opt_name, arg_opt_value, sectionname):
    """
    Verify that command line ignores and patterns take priority over
    rcfile ignores.
    """
    file_ignore = "test_cmd_line_ignore_pri_file.py"
    cmd_arg_ignore = "test_cmd_line_ignore_pri_arg.py"
    cmd_line_ignore = arg_opt_value

    rcfile = testdir.makefile(
        ".rc",
        f"""
        [{sectionname.upper()}]

        {arg_opt_name} = {file_ignore},foo
        """,
    )
    testdir.makepyfile(**{file_ignore: "import sys", cmd_arg_ignore: "import os"})
    result = testdir.runpytest(
        "--pylint",
        f"--pylint-rcfile={rcfile.strpath}",
        f"--pylint-{arg_opt_name}={cmd_line_ignore}",
        "-s",
    )

    assert "collected 1 item" in result.stdout.str()
    assert "Unused import sys" in result.stdout.str()
