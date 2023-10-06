# -*- coding: utf-8 -*-
"""Pylint reporter classes."""
import sys

from pylint.reporters import BaseReporter


class ProgrammaticReporter(BaseReporter):
    """Reporter that replaces output with storage in list of dictionaries"""

    extension = "prog"

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
        print(".", end="")
        sys.stdout.flush()

    def on_close(self, stats, previous_stats):
        """Hook called when all modules finished analyzing."""
        # print a new line when pylint is finished
        print("")
