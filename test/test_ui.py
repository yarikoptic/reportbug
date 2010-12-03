""" Unit test for reportbug.ui module """

import unittest2

from reportbug import utils
from reportbug import ui
from reportbug.ui import __LOADED_UIS as LOADED_UIS

class TestUI(unittest2.TestCase):

    def test_ui(self):
        self.assertItemsEqual(ui.AVAILABLE_UIS, ['text', 'urwid', 'gtk2'])

    def test_getUI(self):
        for loaded_ui in LOADED_UIS.keys():
            self.assertEqual(ui.getUI(loaded_ui), LOADED_UIS[loaded_ui])

        self.assertEqual(ui.getUI('non-existing'), LOADED_UIS['text'])
