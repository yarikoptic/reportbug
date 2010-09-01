""" Unit test for reportbug.ui module """

import unittest2

from reportbug import utils
from reportbug import ui

class TestUI(unittest2.TestCase):

    def test_ui(self):
        self.assertItemsEqual(ui.AVAILABLE_UIS, ['text', 'urwid', 'gtk2'])
        
