# -*- coding: utf-8 -*-
"""
Unit testing module for pytest-pylint util.py module
"""
from pytest_pylint.util import get_rel_path, should_include_file


def test_get_rel_path():
    """
    Verify our relative path function.
    """
    correct_rel_path = "How/Are/You/blah.py"
    path = "/Hi/How/Are/You/blah.py"
    parent_path = "/Hi/"
    assert get_rel_path(path, parent_path) == correct_rel_path

    parent_path = "/Hi"
    assert get_rel_path(path, parent_path) == correct_rel_path


def test_should_include_path():
    """
    Files should only be included in the list if none of the directories on
    it's path, of the filename, match an entry in the ignore list.
    """
    ignore_list = ["first", "second", "third", "part", "base.py"]
    # Default includes.
    assert should_include_file("random", ignore_list) is True
    assert should_include_file("random/filename", ignore_list) is True
    assert should_include_file("random/other/filename", ignore_list) is True
    # Basic ignore matches.
    assert should_include_file("first/filename", ignore_list) is False
    assert should_include_file("random/base.py", ignore_list) is False
    # Part on paths.
    assert should_include_file("part/second/filename.py", ignore_list) is False
    assert should_include_file("random/part/filename.py", ignore_list) is False
    assert should_include_file("random/second/part.py", ignore_list) is False
    # Part as substring on paths.
    assert should_include_file("part_it/other/filename.py", ignore_list) is True
    assert should_include_file("random/part_it/filename.py", ignore_list) is True
    assert should_include_file("random/other/part_it.py", ignore_list) is True


def test_pylint_ignore_patterns():
    """Test if the ignore-patterns is working"""
    ignore_patterns = ["first.*", ".*second", "^third.*fourth$", "part", "base.py"]

    # Default includes
    assert should_include_file("random", [], ignore_patterns) is True
    assert should_include_file("random/filename", [], ignore_patterns) is True
    assert should_include_file("random/other/filename", [], ignore_patterns) is True

    # Pattern matches
    assert should_include_file("first1", [], ignore_patterns) is False
    assert should_include_file("first", [], ignore_patterns) is False
    assert should_include_file("_second", [], ignore_patterns) is False
    assert should_include_file("second_", [], ignore_patterns) is False
    assert should_include_file("second_", [], ignore_patterns) is False
    assert should_include_file("third fourth", [], ignore_patterns) is False
    assert should_include_file("_third fourth_", [], ignore_patterns) is True
    assert should_include_file("part", [], ignore_patterns) is False
    assert should_include_file("1part2", [], ignore_patterns) is True
    assert should_include_file("base.py", [], ignore_patterns) is False
