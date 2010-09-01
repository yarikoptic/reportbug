import unittest2

from reportbug import tempfiles

class TestTempfiles(unittest2.TestCase):

    def test_tempfile_prefix(self):

        extra = 'dummystring'

        prefix = tempfiles.tempfile_prefix()
        self.assertIn('reportbug', prefix)

        prefix = tempfiles.tempfile_prefix(package='dpkg')
        self.assertIn('dpkg', prefix)

        prefix = tempfiles.tempfile_prefix(package='', extra=extra)
        self.assertIn(extra, prefix)

        prefix = tempfiles.tempfile_prefix(package='dpkg', extra=extra)
        self.assertIn('dpkg', prefix)
        self.assertIn(extra, prefix)
