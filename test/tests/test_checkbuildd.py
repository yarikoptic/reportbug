import unittest2

from reportbug import checkbuildd

class TestCheckbuildd(unittest2.TestCase):

    def test_archname(self):
        archname = checkbuildd.archname()
        self.assertNotEqual(archname, '')
