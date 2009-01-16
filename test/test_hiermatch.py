# -*- coding: utf-8; -*-

# test/test_hiermatch.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbuglib.hiermatch module
"""

import scaffold
from scaffold import TestCase

from reportbug import hiermatch

test_strings_list = ['Beautiful is better than ugly.',
                     'Explicit is better than implicit.',
                     'Simple is better than complex.',
                     'Complex is better than complicated.']


class Test_egrep_list(TestCase):
    """Test cases for 'egrep_list' """

    def test_it_works(self):
        """ Should return '4' matches """
        counts = hiermatch.egrep_list(test_strings_list, 'better')
        
        self.failUnlessEqual(len(counts), 4, "Not 4 matches")
