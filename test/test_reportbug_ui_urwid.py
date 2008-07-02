# -*- coding: utf-8; -*-

# test/test_reportbug_ui_urwid.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbuglib.reportbug_ui_urwid module
"""

import scaffold
from scaffold import TestCase

from reportbuglib import reportbug_ui_urwid
from reportbuglib import reportbug_ui_text


class Test_ewrite(TestCase):
    """ Test cases for 'ewrite' """

    def test_is_expected_object(self):
        """ Module should have expected 'ewrite' attribute """
        attribute_name = 'ewrite'
        func = getattr(reportbug_ui_urwid, attribute_name)
        expect_func = getattr(reportbug_ui_text, attribute_name)
        fail_msg = (
            "Module attribute %(attribute_name)r"
            " should be object %(expect_func)r"
            ) % vars()
        self.failUnlessIs(expect_func, func, msg=fail_msg)

class Test_spawn_editor(TestCase):
    """ Test cases for 'spawn_editor' """

    def test_is_expected_object(self):
        """ Module should have expected 'spawn_editor' attribute """
        attribute_name = 'spawn_editor'
        func = getattr(reportbug_ui_urwid, attribute_name)
        expect_func = getattr(reportbug_ui_text, attribute_name)
        fail_msg = (
            "Module attribute %(attribute_name)r"
            " should be object %(expect_func)r"
            ) % vars()
        self.failUnlessIs(expect_func, func, msg=fail_msg)
