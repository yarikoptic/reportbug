# -*- coding: utf-8; -*-

# test/test_reportbug.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbug module
"""

import scaffold
from scaffold import TestCase

import reportbug


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
