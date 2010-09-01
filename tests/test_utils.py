import unittest2

from reportbug import utils

class TestUtils(unittest2.TestCase):

    def test_modes_and_modelist(self):
        """Check MODES items and MODELIST are in sync"""

        self.assertItemsEqual(utils.MODES.keys(), utils.MODELIST)

class TestEmail(unittest2.TestCase):

    def test_check_email_addr(self):
        
        real_addr = 'reportbug-maint@lists.alioth.debian.org'

        self.assertTrue(utils.check_email_addr(real_addr))
        self.assertFalse(utils.check_email_addr('dummy'))
        self.assertFalse(utils.check_email_addr('nouser@nodomain'))

    def test_get_email_addr(self):

        email = 'Reportbug Maintainers <reportbug-maint@lists.alioth.debian.org>'
        name, email_addr = utils.get_email_addr(email)

        self.assertEqual(name, 'Reportbug Maintainers')
        self.assertEqual(email_addr, 'reportbug-maint@lists.alioth.debian.org')

class TestPackages(unittest2.TestCase):

    def test_get_package_status(self):

        status = utils.get_package_status('non-existing-package')

        (pkgversion, pkgavail, depends, recommends, conffiles, maintainer,
         installed, origin, vendor, reportinfo, priority, desc, src_name,
         fulldesc, state, suggests) = status

        self.assertIsNone(pkgversion)
        self.assertIsNone(pkgavail)
        self.assertEqual(depends, ())
        self.assertEqual(recommends, ())
        self.assertEqual(conffiles, ())
        self.assertIsNone(maintainer)
        self.assertFalse(installed)
        self.assertIsNone(origin)
        self.assertEqual(vendor, '')
        self.assertIsNone(reportinfo)
        self.assertIsNone(priority)
        self.assertIsNone(desc)
        self.assertIsNone(src_name)
        self.assertEqual(fulldesc, '')
        self.assertEqual(state, '')
        self.assertEqual(suggests, ())

        # Using an 'Essential: yes' package, what's better than 'dpkg'?
        status = utils.get_package_status('dpkg')

        (pkgversion, pkgavail, depends, recommends, conffiles, maintainer,
         installed, origin, vendor, reportinfo, priority, desc, src_name,
         fulldesc, state, suggests) = status

        self.assertIsNotNone(pkgversion)
        self.assertEqual(pkgavail, 'dpkg')
        # let's just check Depends is not null
        self.assertIsNotNone(depends)
        self.assertIsNotNone(maintainer)
        self.assertTrue(installed)
        self.assertEqual(origin, 'debian')
        self.assertEqual(priority, 'required')
        self.assertIsNotNone(desc)
        self.assertIsNotNone(fulldesc)
        self.assertEqual(state, 'installed')

@unittest2.skip("Too slow")
class TestSourcePackages(unittest2.TestCase):

    def test_get_source_name(self):
        binpkg = 'python-reportbug'
        src = utils.get_source_name(binpkg)
        self.assertEqual(src, 'reportbug')

    def test_get_source_package(self):
        src = 'reportbug'
        binpkgs = utils.get_source_package(src)
        self.assertItemsEqual([bin[0] for bin in binpkgs], ['python-reportbug', 'reportbug'])

        bin = 'python-reportbug'
        binpkgs_frombin = utils.get_source_package(bin)
        self.assertEqual(binpkgs, binpkgs_frombin)

class TestSystemInformation(unittest2.TestCase):

    def test_get_cpu_cores(self):

        cores = utils.get_cpu_cores()
        self.assertGreaterEqual(cores, 1)
