# -*- coding: utf-8; -*-

# test/test_reportbug.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbuglib.reportbug module
"""

import os

import scaffold
from scaffold import TestCase

from reportbug import utils as reportbug


class Test_glob_escape(TestCase):
    """ Test cases for 'glob_escape' function """

    def test_preserves_non_specials(self):
        """ glob_escape should preserve non-special characters
        """
        in_filename = r"foo-bar_baz"
        expect_filename = in_filename
        out_filename = reportbug.glob_escape(in_filename)
        self.failUnlessEqual(expect_filename, out_filename)

    def test_escapes_wildcard(self):
        """ glob_escape should escape wildcard characters

            Filename glob wildcard characters are '?' and '*'. These
            should be escaped by a preceding backslash ('\').

            """
        in_filename = r"foo*bar?baz"
        expect_filename = r"foo\*bar\?baz"
        out_filename = reportbug.glob_escape(in_filename)
        self.failUnlessEqual(expect_filename, out_filename)

    def test_escapes_character_class(self):
        """ glob_escape should escape character-class characters

            Filename globs can have character classes enclosed by
            brackets ('[', ']'). These should be escaped by a
            preceding backslash ('\').

            """
        in_filename = r"foo[bar]baz"
        expect_filename = r"foo\[bar\]baz"
        out_filename = reportbug.glob_escape(in_filename)
        self.failUnlessEqual(expect_filename, out_filename)


class Test_which_editor(TestCase):
    """ Test cases for 'which_editor' function """

    def setUp(self):
        """ Set up test fixtures """

        stub_os_environ = {}
        self.os_environ_prev = os.environ
        os.environ = stub_os_environ

        self.debian_default_editor = "bogus-default"

    def tearDown(self):
        """ Tear down test fixtures """
        os.environ = self.os_environ_prev

    def test_prefers_specified_default_editor_over_all(self):
        """ Should return specified `default_editor`

            The `default_editor` parameter should override all other
            sources for an editor setting.

            """
        specified_editor = "foo-specified"
        os.environ.update({
            "VISUAL": "bogus-visual",
            "EDITOR": "bogus-editor",
            })
        editor = reportbug.which_editor(specified_editor)
        expect_editor = specified_editor
        self.failUnlessEqual(expect_editor, editor)

    def test_prefers_visual_variable_over_editor_variable(self):
        """ Should return 'VISUAL' variable rather than 'EDITOR'

            The 'VISUAL' environment variable should be preferred over
            the 'EDITOR' variable.

            """
        os.environ.update({
            "VISUAL": "foo-visual",
            "EDITOR": "bogus-editor",
            })
        editor = reportbug.which_editor()
        expect_editor = os.environ["VISUAL"]
        self.failUnlessEqual(expect_editor, editor)

    def test_prefers_editor_variable_over_debian_default(self):
        """ Should return 'EDITOR' variable rather than Debian default

            The 'EDITOR' environment variable should be preferred over
            the Debian default editor.

            """
        os.environ.update({
            "EDITOR": "foo-editor",
            })
        editor = reportbug.which_editor()
        expect_editor = os.environ["EDITOR"]
        self.failUnlessEqual(expect_editor, editor)

    def test_prefers_debian_default_over_nothing(self):
        """ Should return Debian default when no other alternative

            The Debian default editor should be returned when no other
            alternative is set.

            """
        self.debian_default_editor = "/usr/bin/sensible-editor"
        editor = reportbug.which_editor()
        expect_editor = self.debian_default_editor
        self.failUnlessEqual(expect_editor, editor)

    def test_empty_string_value_skipped_in_precendence(self):
        """ Should skip an empty string value in the precedence check

            An empty string value should cause the precedence check to
            skip the value as though it were unset.

            """
        specified_editor = ""
        os.environ.update({
            "VISUAL": "",
            "EDITOR": "",
            })
        self.debian_default_editor = "/usr/bin/sensible-editor"
        editor = reportbug.which_editor(specified_editor)
        expect_editor = self.debian_default_editor
        self.failUnlessEqual(expect_editor, editor)
