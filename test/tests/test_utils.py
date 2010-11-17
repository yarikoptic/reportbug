import unittest2

from reportbug import utils
import os.path

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

    def test_get_email(self):

        name = 'Reportbug Maintainers'
        mail = 'reportbug-maint@lists.alioth.debian.org'

        n, m = utils.get_email(mail, name)

        self.assertEqual(name, n)
        self.assertEqual(mail, m)

    def test_get_user_id(self):

        name = 'Reportbug Maintainers'
        mail = 'reportbug-maint@lists.alioth.debian.org'
        addr = utils.get_user_id(mail, name)
        self.assertEqual(addr, "%s <%s>" % (name, mail))

        name = 'test'
        mail = 'faked'
        addr = utils.get_user_id(mail, name)
        self.assertIn(mail+'@', addr)

        mail = 'Reportbug Maintainers <reportbug-maint@lists.alioth.debian.org>'
        addr = utils.get_user_id(mail)
        self.assertEqual(mail, addr)

        mail = 'reportbug-maint@lists.alioth.debian.org'
        addr = utils.get_user_id(mail)
        self.assertIn(mail, addr)


    def test_find_rewritten(self):
        unittest2.skip("Is utils.find_rewritten actually useful to someone? deprecate it?")

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

        # it exploits the 'statuscache', it's already called before
        # so it's now in the cache
        status = utils.get_package_status('dpkg')

        status = utils.get_package_status('reportbug', avail=True)

        (pkgversion, pkgavail, depends, recommends, conffiles, maintainer,
         installed, origin, vendor, reportinfo, priority, desc, src_name,
         fulldesc, state, suggests) = status

        self.assertIsNotNone(pkgversion)
        self.assertEqual(pkgavail, 'reportbug')
        # let's just check Depends is not null
        self.assertIsNotNone(depends)
        self.assertIsNotNone(maintainer)
        self.assertEqual(priority, 'standard')
        self.assertIsNotNone(desc)
        self.assertIsNotNone(fulldesc)

        status = utils.get_package_status('python-matplotlib')

        (pkgversion, pkgavail, depends, recommends, conffiles, maintainer,
         installed, origin, vendor, reportinfo, priority, desc, src_name,
         fulldesc, state, suggests) = status

        self.assertIsNotNone(recommends)


    def test_get_changed_config_files(self):

        status = utils.get_package_status('dpkg')

        (pkgversion, pkgavail, depends, recommends, conffiles, maintainer,
         installed, origin, vendor, reportinfo, priority, desc, src_name,
         fulldesc, state, suggests) = status

        confinfo, changed = utils.get_changed_config_files(conffiles)
        self.assertIsNotNone(confinfo)

    def test_find_package_for(self):
        result = utils.find_package_for('dpkg')
        self.assertNotEqual(result[1], {})

        filename = 'reportbug-bugfree'
        result = utils.find_package_for(filename, pathonly=True)
        self.assertEqual(result[0], filename)
        self.assertIsNone(result[1])

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

    def test_get_avail_database(self):
        
        avail_db = utils.get_avail_database()
        entry = avail_db.next()
        self.assertIsNotNone(entry)

    def test_available_package_description(self):

        descr = utils.available_package_description('reportbug')
        self.assertEquals(descr, 'reports bugs in the Debian distribution')

        descr = utils.available_package_description('reportbug-bugfree')
        self.assertIsNone(descr)

class TestSourcePackages(unittest2.TestCase):

    #@unittest2.skip("Too slow")
    def test_get_source_name(self):
        binpkg = 'python-reportbug'
        src = utils.get_source_name(binpkg)
        self.assertEqual(src, 'reportbug')

        src = utils.get_source_name('reportbug-bugfree')
        self.assertIsNone(src)

    #@unittest2.skip("Too slow")
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


    def test_lsb_release_info(self):

        res = utils.lsb_release_info()
        self.assertIn('Debian', res)

class TestMua(unittest2.TestCase):

    def test_mua_is_supported(self):

        for mua in ('mh', 'nmh', 'gnus', 'mutt'):
            self.assertTrue(utils.mua_is_supported(mua))

        self.assertFalse(utils.mua_is_supported('mua-of-my-dreams'))

    def test_mua_exists(self):

        for mua in ('mh', 'nmh', 'gnus', 'mutt'):
            if not utils.mua_exists(mua):
                self.fail("%s MUA program not available" % mua)

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

        # check for the provides stuff
        result = utils.get_dependency_info('reportbug', [['awk']])
        self.assertIn('awk', result)

    def test_cleanup_msg(self):

        message = """Subject: unblock: reportbug/4.12.6
Package: release.debian.org
User: release.debian.org@packages.debian.org
Usertags: unblock
Severity: normal
Morph: cool
Continuation:
 header

Please unblock package reportbug

(explain the reason for the unblock here)

unblock reportbug/4.12.6

-- System Information:
Debian Release: squeeze/sid
  APT prefers unstable
  APT policy: (500, 'unstable'), (1, 'experimental')
Architecture: amd64 (x86_64)

Kernel: Linux 2.6.31-1-amd64 (SMP w/4 CPU cores)
Locale: LANG=en_US.UTF-8, LC_CTYPE=en_US.UTF-8 (charmap=UTF-8)
Shell: /bin/sh linked to /bin/bash"""
        header = [u'X-Debbugs-CC: reportbug@packages.qa.debian.org']
        pseudos = ['Morph: cool']
        rtype = 'debbugs'
        body, headers, pseudo = utils.cleanup_msg(message, header, pseudos,
                                                  rtype)

        # check body content
        self.assertIn('reportbug/4.12.6', body)
        self.assertIn('System Information', body)

        # check expected headers are there
        h = dict(headers)
        self.assertIn('Subject', h)
        self.assertIn('X-Debbugs-CC', h)

        # check expected pseudo headers are there
        p = dict([p.split(': ') for p in pseudo])
        self.assertIn('Package', p)
        self.assertIn('Severity', p)
        self.assertIn('User', p)
        self.assertIn('Usertags', p)
        self.assertIn('Morph', p)


    def test_generate_blank_report(self):

        report = utils.generate_blank_report('reportbug', '1.2.3', 'normal',
                                             '', '', '', type='debbugs')
        self.assertIsNotNone(report)
        self.assertIn('Package: reportbug', report)
        self.assertIn('Version: 1.2.3', report)
        self.assertIn('Severity: normal', report)


class TestConfig(unittest2.TestCase):

# Find a way to specify an "internal" file for testing
#    def setUp(self):
#        self._FILES = utils.FILES
#        utils.FILES = os.path.dirname(__file__) + '/data/reportbugrc'
#
#    def tearDown(self):
#        utils.FILES = self._FILES
#
# --> check the code in utils.parse_config_files to get all the checked params

    def test_parse_config_files(self):
        args = utils.parse_config_files()
        self.assertIsNot(args, {})


class TestControl(unittest2.TestCase):

    def test_parse_bug_control_file(self):

        ctrl_file = os.path.dirname(__file__) + '/data/control'

        submitas, submitto, reportwith, supplemental = \
            utils.parse_bug_control_file(ctrl_file)

        self.assertEquals(submitas, 'reportbug2')
        self.assertEquals(submitto, 'reportbug-maint@lists.alioth.debian.org')
        self.assertIn('python', reportwith)
        self.assertIn('perl', reportwith)
        self.assertIn('python', supplemental)
        self.assertIn('perl', supplemental)

class TestPaths(unittest2.TestCase):

    def test_search_path_for(self):

        p = 'not-existing'
        res = utils.search_path_for(p)
        self.assertIsNone(res)

        p = '/tmp'
        res = utils.search_path_for(p)
        self.assertEquals(p, res)

        p = 'dpkg'
        res = utils.search_path_for(p)
        self.assertEquals(res, '/usr/bin/dpkg')

class TestEditor(unittest2.TestCase):

    def test_which_editor(self):

        res = utils.which_editor()
        self.assertIsNotNone(res)

        e = 'reportbug-editor'
        res = utils.which_editor(e)
        self.assertEquals(e, res)
        
class TestSearch(unittest2.TestCase):

    def test_search_pipe(self):

        f = 'reportbug'

        dlocate = True
        pipe, dloc = utils.search_pipe(f, dlocate)
        res = pipe.readlines()
        pipe.close()

        self.assertEquals(dloc, dlocate)
        self.assertGreater(len(res), 0)

        dlocate = False
        pipe, dloc = utils.search_pipe(f, dlocate)
        res = pipe.readlines()
        pipe.close()

        self.assertEquals(dloc, dlocate)
        self.assertGreater(len(res), 0)

class TestDpkg(unittest2.TestCase):

    def test_query_dpkg_for(self):

        p = 'reportbug'
        dlocate = True
        res = utils.query_dpkg_for(p, dlocate)

        self.assertEquals(res[0], p)
        self.assertGreater(len(res[1].keys()), 0)

        dlocate = False
        res = utils.query_dpkg_for(p, dlocate)

        self.assertEquals(res[0], p)
        self.assertGreater(len(res[1].keys()), 0)

        # to trigger 'Try again without dlocate if no packages found'
        p = 'blablabla'
        dlocate = True
        res = utils.query_dpkg_for(p, dlocate)

        self.assertEquals(res[0], p)
        self.assertEquals(res[1], {})

class TestMisc(unittest2.TestCase):

    def test_first_run(self):

        isfirstrun = utils.first_run()
        self.assertIsNotNone(isfirstrun)
