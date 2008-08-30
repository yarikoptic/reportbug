# -*- coding: utf-8; -*-

# test/test_rbtempfile.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbuglib.rbtempfile module
"""

import os

import scaffold
from scaffold import TestCase

from reportbug import tempfiles as rbtempfile


class Test_cleanup_temp_file(TestCase):
    """ Test cases for 'cleanup_temp_file' function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_state = {
            'os.unlink': None,
            }
        self.temp_filename = "foo.bar"
        def mock_os_unlink(path):
            if path != self.temp_filename:
                raise IOError("Not found: %(path)s" % vars())
            self.mock_state['os.unlink'] = path

        self.os_unlink_prev = os.unlink
        os.unlink = mock_os_unlink

        def mock_os_path_exists(path):
            exists = (path == self.temp_filename)
            return exists

        self.os_path_exists_prev = os.path.exists
        os.path.exists = mock_os_path_exists

    def tearDown(self):
        """ Tear down test fixtures """
        os.unlink = self.os_unlink_prev
        os.path.exists = self.os_path_exists_prev

    def test_unlink_file_if_exists(self):
        """ Should unlink the named file if it exists """
        path = self.temp_filename
        rbtempfile.cleanup_temp_file(path)
        self.failUnlessEqual(path, self.mock_state['os.unlink'])

    def test_does_not_unlink_if_file_not_exist(self):
        """ Should not call 'os.unlink' if file does not exist """
        path = "bogus"
        rbtempfile.cleanup_temp_file(path)
        self.failUnlessEqual(None, self.mock_state['os.unlink'])
