import unittest2

from reportbug.bugreport import bugreport

class TestBugreport(unittest2.TestCase):

# TODO: differentiate for all possible cases? f.e. sysinfo True/False and then change if 'System Information' in self.text?

    def test_bugreport(self):
        self.body = 'test'
        self.package = 'reportbug'
        self.bugreport = bugreport(package=self.package, body=self.body)
        self.text = self.bugreport.__unicode__()

        self.assertIn(self.body, self.text)
        self.assertIn(self.package, self.text)
