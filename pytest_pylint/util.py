# -*- coding: utf-8 -*-
"""
Utility functions for gathering files, etc.
"""
import re
from os import sep


class PyLintException(Exception):
    """Exception to raise if a file has a specified pylint error"""


def get_rel_path(path, parent_path):
    """
    Give the path to object relative to ``parent_path``.
    """
    replaced_path = path.replace(parent_path, "", 1)

    if replaced_path[0] == sep and replaced_path != path:
        rel_path = replaced_path[1:]
    else:
        rel_path = replaced_path
    return rel_path


def should_include_file(path, ignore_list, ignore_patterns=None):
    """Checks if a file should be included in the collection."""
    if ignore_patterns:
        for pattern in ignore_patterns:
            if re.match(pattern, path):
                return False
    parts = path.split(sep)
    return not set(parts) & set(ignore_list)
