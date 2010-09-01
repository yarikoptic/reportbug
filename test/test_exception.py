from __future__ import with_statement

import unittest2

from reportbug import exceptions

class TestExceptions(unittest2.TestCase):

    def test_raises_reportbug_exception(self):
        with self.assertRaises(exceptions.reportbug_exception):
            raise exceptions.reportbug_exception

    def test_raises_reportbug_ui_exception(self):
        with self.assertRaises(exceptions.reportbug_ui_exception):
            raise exceptions.reportbug_ui_exception

    def test_raises_UINotImportable(self):
        with self.assertRaises(exceptions.UINotImportable):
            raise exceptions.UINotImportable

    def test_raises_NoPackage(self):
        with self.assertRaises(exceptions.NoPackage):
            raise exceptions.NoPackage

    def test_raises_NoBugs(self):
        with self.assertRaises(exceptions.NoBugs):
            raise exceptions.NoBugs

    def test_raises_NoReport(self):
        with self.assertRaises(exceptions.NoReport):
            raise exceptions.NoReport

    def test_raises_UINotImplemented(self):
        with self.assertRaises(exceptions.UINotImplemented):
            raise exceptions.UINotImplemented

    def test_raises_NoNetwork(self):
        with self.assertRaises(exceptions.NoNetwork):
            raise exceptions.NoNetwork

    def test_raises_InvalidRegex(self):
        with self.assertRaises(exceptions.InvalidRegex):
            raise exceptions.InvalidRegex

    def test_raises_NoMessage(self):
        with self.assertRaises(exceptions.NoMessage):
            raise exceptions.NoMessage
