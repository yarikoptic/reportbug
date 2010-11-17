import unittest2

from reportbug import tempfiles
import os.path

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

    def test_open_write_safe(self):

        filename = os.path.dirname(__file__) + '/tempfiletest'
        # binary file
        fd = tempfiles.open_write_safe(filename)

        self.assertFalse(fd.closed)
        fd.close()
        self.assertTrue(fd.closed)

        # remove temp file
        tempfiles.cleanup_temp_file(filename)

        filename = os.path.dirname(__file__) + '/tempfiletest'
        # text file
        fd = tempfiles.open_write_safe(filename, mode='w')

        self.assertFalse(fd.closed)
        fd.close()
        self.assertTrue(fd.closed)

        tempfiles.cleanup_temp_file(filename)

    def test_TempFile(self):

        fd, filename = tempfiles.TempFile()

        self.assertIsNotNone(filename)
        self.assertFalse(fd.closed)
        fd.close()
        self.assertTrue(fd.closed)

        tempfiles.cleanup_temp_file(filename)
