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
        self.assertFalse(utils.check_email_addr('.nouser@nodomain'))
        self.assertFalse(utils.check_email_addr('nouser.@nodomain'))
        self.assertFalse(utils.check_email_addr('nouser@.nodomain'))
        self.assertFalse(utils.check_email_addr('nouser@nodomain.'))
        self.assertFalse(utils.check_email_addr('too@many@at@signs'))

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

    def test_find_package_for(self):
        result = utils.find_package_for('dpkg')
        self.assertNotEqual(result[1], {})

        result = utils.find_package_for('/usr/bin/reportbug')
        self.assertNotEqual(result[1], {})

        result = utils.find_package_for('/var/lib/dpkg/info/reportbug.md5sums')
        self.assertNotEqual(result[1], {})

        result = utils.find_package_for('/usr/bin/')
        self.assertNotEqual(result[1], {})

    def test_get_package_info(self):

        result = utils.get_package_info([])
        self.assertEqual(result, [])

        pkg = 'reportbug'
        result = utils.get_package_info([((pkg,), pkg)])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], pkg)

        # open package surely not available on my client systems
        #to cover line 568
        pkg = 'slapd'
        result = utils.get_package_info([((pkg,), pkg)])

        self.assertEqual(result[0][0], pkg)
        self.assertEqual(result[0][2], '<none>')

        result = utils.get_package_info([((pkg,), pkg)], skip_notfound=True)

        self.assertEqual(result, [])

        # package with a Provides
        #pkg = 'emacs'
        #result = utils.get_package_info([((pkg,), pkg)])

        #self.assertEqual(result[0][0], pkg)

    def test_packages_providing(self):
        pkg = 'editor'
        result = utils.packages_providing(pkg)

        self.assertGreater(len(result), 0)

class TestSourcePackages(unittest2.TestCase):

    @unittest2.skip("Too slow")
    def test_get_source_name(self):
        binpkg = 'python-reportbug'
        src = utils.get_source_name(binpkg)
        self.assertEqual(src, 'reportbug')

    @unittest2.skip("Too slow")
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

class TestMua(unittest2.TestCase):

    def test_mua_is_supported(self):

        for mua in ('mh', 'nmh', 'gnus', 'mutt'):
            self.assertTrue(utils.mua_is_supported(mua))

        self.assertFalse(utils.mua_is_supported('mua-of-my-dreams'))

    def test_mua_exists(self):

        for mua in ('mh', 'nmh', 'gnus', 'mutt'):
            self.assertTrue(utils.mua_exists(mua))

    def test_mua_name(self):

        for mua in ('mh', 'nmh', 'gnus', 'mutt'):
            self.assertIsInstance(utils.mua_name(mua), utils.Mua)

        self.assertEqual(utils.mua_name('mua-of-my-dreams'), 'mua-of-my-dreams')

class TestBugreportBody(unittest2.TestCase):

    def test_get_dependency_info(self):

        pkg = 'reportbug'
        result = utils.get_dependency_info('reportbug', '')

        self.assertIn('no packages', result)

        result = utils.get_dependency_info('reportbug', [['dpkg']])
        self.assertIn('dpkg', result)
