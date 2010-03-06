#
# utils module - common functions for reportbug UIs
#   Written by Chris Lawrence <lawrencc@debian.org>
#   Copyright (C) 1999-2008 Chris Lawrence
#   Copyright (C) 2008-2010 Sandro Tosi <morph@debian.org>
#
# This program is freely distributable per the following license:
#
##  Permission to use, copy, modify, and distribute this software and its
##  documentation for any purpose and without fee is hereby granted,
##  provided that the above copyright notice appears in all copies and that
##  both that copyright notice and this permission notice appear in
##  supporting documentation.
##
##  I DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
##  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL I
##  BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
##  DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
##  WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
##  ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
##  SOFTWARE.
#
# Version ##VERSION##; see changelog for revision history
#
# $Id: reportbug.py,v 1.35.2.24 2008-04-18 05:38:28 lawrencc Exp $

import sys
import os
import re
import platform
try:
    import pwd
    from tempfiles import TempFile, tempfile_prefix
except ImportError, e:
    if platform.system() == 'Windows':
        pass
    else:
        print e
        sys.exit(1)
import commands
import shlex
import rfc822
import socket
import subprocess

import debianbts
from string import ascii_letters, digits

# needed for MUA send
import ui.text_ui as ui

# Paths for dpkg
DPKGLIB = '/var/lib/dpkg'
AVAILDB = os.path.join(DPKGLIB, 'available')
STATUSDB = os.path.join(DPKGLIB, 'status')

# Headers other than these become email headers for debbugs servers
PSEUDOHEADERS = ('Package', 'Source', 'Version', 'Severity', 'File', 'Tags',
                 'Justification', 'Followup-For', 'Owner', 'User', 'Usertags')

from reportbug.ui import AVAILABLE_UIS

MODES = {'novice': 'Offer simple prompts, bypassing technical questions.',
         'standard': 'Offer more extensive prompts, including asking about '
         'things that a moderately sophisticated user would be expected to '
         'know about Debian.',
         'advanced' : 'Like standard, but assumes you know a bit more about '
         'Debian, including "incoming".',
         'expert': 'Bypass most handholding measures and preliminary triage '
         'routines.  This mode should not be used by people unfamiliar with '
         'Debian\'s policies and operating procedures.'}
MODELIST = ['novice', 'standard', 'advanced', 'expert']
for mode in MODELIST:
    exec 'MODE_%s=%d' % (mode.upper(), MODELIST.index(mode))
del mode

NEWBIELINE = '*** Please type your report below this line ***'

fhs_directories = ['/', '/usr', '/usr/share', '/var', '/usr/X11R6',
                   '/usr/man', '/usr/doc', '/usr/bin']

def realpath(filename):
    filename = os.path.abspath(filename)

    bits = filename.split('/')
    for i in range(2, len(bits)+1):
        component = '/'.join(bits[0:i])
        if component in fhs_directories:
            continue

        if os.path.islink(component):
            resolved = os.readlink(component)
            (dir, file) = os.path.split(component)
            resolved = os.path.normpath(os.path.join(dir, resolved))
            newpath = apply(os.path.join, [resolved] + bits[i:])
            return realpath(newpath)

    return filename

pathdirs = ['/usr/sbin', '/usr/bin', '/sbin', '/bin', '/usr/X11R6/bin',
            '/usr/games']

def search_path_for(filename):
    d, f = os.path.split(filename)
    if d: return realpath(filename)

    path = os.environ.get("PATH", os.defpath).split('/')
    for d in pathdirs:
        if not d in path:
            path.append(d)

    for d in path:
        fullname = os.path.join(d, f)
        if os.path.exists(fullname):
            return realpath(fullname)
    return None

def which_editor(specified_editor=None):
    """ Determine which editor program to use.

        :parameters:
          `specified_editor`
            Specified editor for reportbug, to be used in preference
            to other settings.

        :return value:
            Command to invoke for selected editor program.

        """
    debian_default_editor = "/usr/bin/sensible-editor"
    for editor in [
        specified_editor,
        os.environ.get("VISUAL"),
        os.environ.get("EDITOR"),
        debian_default_editor]:
        if editor:
            break

    return editor

def glob_escape(filename):
    filename = re.sub(r'([*?\[\]])', r'\\\1', filename)
    return filename

def search_pipe(searchfile, use_dlocate=True):
    arg = commands.mkarg(searchfile)
    if use_dlocate and os.path.exists('/usr/bin/dlocate'):
        pipe = os.popen('COLUMNS=79 dlocate -S %s 2>/dev/null' % arg)
    else:
        use_dlocate = False
        pipe = os.popen('COLUMNS=79 dpkg --search %s 2>/dev/null' % arg)
    return (pipe, use_dlocate)

def query_dpkg_for(filename, use_dlocate=True):
    try:
        x = os.getcwd()
    except OSError:
        os.chdir('/')
    searchfilename = glob_escape(filename)
    (pipe, dlocate_used) = search_pipe(searchfilename, use_dlocate)
    packages = {}

    for line in pipe:
        line = line.strip()
        # Ignore diversions
        if 'diversion by' in line: continue

        (package, path) = line.split(':', 1)
        path = path.strip()
        packlist = package.split(', ')
        for package in packlist:
            if packages.has_key(package):
                packages[package].append(path)
            else:
                packages[package] = [path]
    pipe.close()
    # Try again without dlocate if no packages found
    if not packages and dlocate_used:
        return query_dpkg_for(filename, use_dlocate=False)

    return filename, packages

def find_package_for(filename, pathonly=False):
    """Find the package(s) containing this file."""
    packages = {}
    if filename[0] == '/':
        fn, pkglist = query_dpkg_for(filename)
        if pkglist: return fn, pkglist

    newfilename = search_path_for(filename)
    if pathonly and not newfilename:
        return (filename, None)
    return query_dpkg_for(newfilename or filename)

def find_rewritten(username):
    for filename in ['/etc/email-addresses']:
        if os.path.exists(filename):
            try:
                fp = file(filename)
            except IOError:
                continue
            for line in fp:
                line = line.strip().split('#')[0]
                if not line:
                    continue
                try:
                    name, alias = line.split(':')
                    if name.strip() == username:
                        return alias.strip()
                except ValueError:
                    print 'Invalid entry in %s' % filename
                    return None

def check_email_addr(addr):
    """Simple check for email validity"""
    if '@' not in addr:
        return False
    if addr.count('@') != 1:
        return False
    localpart, domainpart = addr.split('@')
    if localpart.startswith('.') or localpart.endswith('.'):
        return False
    if '.' not in domainpart:
        return False
    if domainpart.startswith('.') or domainpart.endswith('.'):
        return False
    return True

def get_email_addr(addr):
    addr = rfc822.AddressList(addr)
    return addr.addresslist[0]

def get_email(email='', realname=''):
    return get_email_addr(get_user_id(email, realname))

def get_user_id(email='', realname='', charset='utf-8'):
    uid = os.getuid()
    info = pwd.getpwuid(uid)
    email = (os.environ.get('REPORTBUGEMAIL', email) or
             os.environ.get('DEBEMAIL') or os.environ.get('EMAIL'))

    email = email or find_rewritten(info[0]) or info[0]

    if '@' not in email:
        if os.path.exists('/etc/mailname'):
            domainname = file('/etc/mailname').readline().strip()
        else:
            domainname = socket.getfqdn()

        email = email+'@'+domainname

    # Handle EMAIL if it's formatted as 'Bob <bob@host>'.
    if '<' in email or '(' in email:
        realname, email = get_email_addr(email)

    if not realname:
        realname = (os.environ.get('DEBFULLNAME') or os.environ.get('DEBNAME')
                    or os.environ.get('NAME'))
        if not realname:
            realname = info[4].split(',', 1)[0]
            # Convert & in gecos field 4 to capitalized logname: #224231
            realname = realname.replace('&', info[0].upper())

    if not realname:
        return email

    # Decode the realname from the charset -
    # but only if it is not already in Unicode
    if isinstance(realname, str):
        realname = realname.decode(charset, 'replace')

    if re.match(r'[\w\s]+$', realname):
        return u'%s <%s>' % (realname, email)

    addr = rfc822.dump_address_pair( (realname, email) )
    if isinstance(addr, str):
        addr = addr.decode('utf-8', 'replace')
    return addr

statuscache = {}
def get_package_status(package, avail=False):
    if not avail and package in statuscache:
        return statuscache[package]

    versionre = re.compile('Version: ')
    packagere = re.compile('Package: ')
    priorityre = re.compile('Priority: ')
    dependsre = re.compile('(Pre-)?Depends: ')
    recsre = re.compile('Recommends: ')
    suggestsre = re.compile('Suggests: ')
    conffilesre = re.compile('Conffiles: ')
    maintre = re.compile('Maintainer: ')
    statusre = re.compile('Status: ')
    originre = re.compile('Origin: ')
    bugsre = re.compile('Bugs: ')
    descre = re.compile('Description: ')
    fullre = re.compile(' ')
    srcre = re.compile('Source: ')

    pkgversion = pkgavail = maintainer = status = origin = None
    bugs = vendor = priority = desc = src_name = None
    conffiles = []
    fulldesc = []
    depends = []
    recommends = []
    suggests = []
    confmode = False
    state = ''

    try:
        x = os.getcwd()
    except OSError:
        os.chdir('/')

    packarg = commands.mkarg(package)
    if avail:
        output = commands.getoutput(
            "COLUMNS=79 dpkg --print-avail %s 2>/dev/null" % packarg)
    else:
        output = commands.getoutput(
            "COLUMNS=79 dpkg --status %s 2>/dev/null" % packarg)

    # dpkg output is in UTF-8 format
    output = output.decode('utf-8', 'replace')

    for line in output.split(os.linesep):
        line = line.rstrip()
        if not line: continue

        if confmode:
            if line[0] != '/':
                confmode = False
            else:
                conffiles = conffiles + (line.split(),)

        if versionre.match(line):
            (crud, pkgversion) = line.split(": ", 1)
        elif statusre.match(line):
            (crud, status) = line.split(": ", 1)
        elif priorityre.match(line):
            (crud, priority) = line.split(": ", 1)
        elif packagere.match(line):
            (crud, pkgavail) = line.split(": ", 1)
        elif originre.match(line):
            (crud, origin) = line.split(": ", 1)
        elif bugsre.match(line):
            (crud, bugs) = line.split(": ", 1)
        elif descre.match(line):
            (crud, desc) = line.split(": ", 1)
        elif dependsre.match(line):
            (crud, thisdepends) = line.split(": ", 1)
            # Remove versioning crud
            thisdepends = [[y.split()[0] for y in x.split('|')]
                           for x in (thisdepends.split(', '))]
            depends.extend(thisdepends)
        elif recsre.match(line):
            (crud, thisdepends) = line.split(": ", 1)
            # Remove versioning crud
            thisdepends = [[y.split()[0] for y in x.split('|')]
                           for x in (thisdepends.split(', '))]
            recommends.extend(thisdepends)
        elif suggestsre.match(line):
            (crud, thisdepends) = line.split(": ", 1)
            # Remove versioning crud
            thisdepends = [[y.split()[0] for y in x.split('|')]
                           for x in (thisdepends.split(', '))]
            suggests.extend(thisdepends)
        elif conffilesre.match(line):
            confmode = True
        elif maintre.match(line):
            crud, maintainer = line.split(": ", 1)
        elif srcre.match(line):
            crud, src_name = line.split(": ", 1)
            src_name = src_name.split()[0]
        elif desc and line[0]==' ':
            fulldesc.append(line)

    installed = False
    if status:
        state = status.split()[2]
        installed = (state not in ('config-files', 'not-installed'))

    reportinfo = None
    if bugs:
        reportinfo = debianbts.parse_bts_url(bugs)
    elif origin:
        if debianbts.SYSTEMS.has_key(origin):
            vendor = debianbts.SYSTEMS[origin]['name']
            reportinfo = (debianbts.SYSTEMS[origin].get('type', 'debbugs'),
                          debianbts.SYSTEMS[origin]['btsroot'])
        else:
            vendor = origin.capitalize()
    else:
        vendor = ''

    info = (pkgversion, pkgavail, tuple(depends), tuple(recommends),
            tuple(conffiles),
            maintainer, installed, origin, vendor, reportinfo, priority,
            desc, src_name, os.linesep.join(fulldesc), state, tuple(suggests))

    if not avail:
        statuscache[package] = info
    return info

#dbase = []
#avail = []

# Object that essentially chunkifies the output of apt-cache dumpavail
class AvailDB(object):
    def __init__(self, fp=None, popenob=None):
        self.popenob = popenob
        if fp:
            self.fp = fp
        elif popenob:
            self.fp = popenob.stdout

    def __iter__(self):
        return self

    def next(self):
        chunk = u''
        while True:
            if self.popenob:
                if self.popenob.returncode:
                    break

            line = self.fp.readline()
            if not line:
                break

            if line == '\n':
                return chunk
            chunk += line.decode('utf-8', 'replace')

        if chunk:
            return chunk

        raise StopIteration

    def __del__(self):
        #print >> sys.stderr, 'availdb cleanup', repr(self.popenob), repr(self.fp)
        if self.popenob:
            # Clear the pipe before shutting it down
            while True:
                if self.popenob.returncode:
                    break
                stuff = self.fp.read(65536)
                if not stuff:
                    break
            self.popenob.wait()
        if self.fp:
            self.fp.close()

def get_dpkg_database():
    try:
        fp = open(STATUSDB)
        if fp:
            return AvailDB(fp=fp)
    except IOError:
        print >> sys.stderr, 'Unable to open', STATUSDB
        sys.exit(1)

def get_avail_database():
    #print >> sys.stderr, 'Searching available database'
    subp = subprocess.Popen(('apt-cache', 'dumpavail'), stdout=subprocess.PIPE)
    return AvailDB(popenob=subp)

def available_package_description(package):
    data = commands.getoutput('apt-cache show'+commands.mkarg(package))
    data = data.decode('utf-8', 'replace')
    descre = re.compile(r'^Description: (.*)$')
    for line in data.split('\n'):
        m = descre.match(line)
        if m:
            return m.group(1)
    return None

def get_source_name(package):
    packages = []

    data = commands.getoutput('apt-cache showsrc'+commands.mkarg(package))
    data = data.decode('utf-8', 'replace')
    packre = re.compile(r'^Package: (.*)$')
    for line in data.split('\n'):
        m = packre.match(line)
        if m:
            return m.group(1)
    return None

def get_source_package(package):
    packages = []
    retlist = []
    found = {}

    data = commands.getoutput('apt-cache showsrc'+commands.mkarg(package))
    data = data.decode('utf-8', 'replace')
    binre = re.compile(r'^Binary: (.*)$')
    for line in data.split('\n'):
        m = binre.match(line)
        if m:
            packs = m.group(1)
            packlist = re.split(r',\s*', packs)
            packages += packlist

    for p in packages:
        desc = available_package_description(p)
        if desc and (p not in found):
            retlist += [(p, desc)]
            found[p] = desc

    retlist.sort()
    return retlist

def get_package_info(packages, skip_notfound=False):
    if not packages:
        return []

    packinfo = get_dpkg_database()
    pkgname = r'(?:[\S]+(?:$|,\s+))'

    groupfor = {}
    searchpkgs = []
    searchbits = []
    for (group, package) in packages:
        groupfor[package] = group
        escpkg = re.escape(package)
        searchpkgs.append(escpkg)

    searchbits = [
        # Package regular expression
        r'^(?P<hdr>Package):\s+('+'|'.join(searchpkgs)+')$',
        # Provides regular expression
        r'^(?P<hdr>Provides):\s+'+pkgname+r'*(?P<pkg>'+'|'.join(searchpkgs)+
        r')(?:$|,\s+)'+pkgname+'*$'
        ]

    groups = groupfor.values()
    found = {}

    searchobs = [re.compile(x, re.MULTILINE) for x in searchbits]
    packob = re.compile('^Package: (?P<pkg>.*)$', re.MULTILINE)
    statob = re.compile('^Status: (?P<stat>.*)$', re.MULTILINE)
    versob = re.compile('^Version: (?P<vers>.*)$', re.MULTILINE)
    descob = re.compile('^Description: (?P<desc>.*)$', re.MULTILINE)

    ret = []
    for p in packinfo:
        for ob in searchobs:
            m = ob.search(p)
            if m:
                pack = packob.search(p).group('pkg')
                stat = statob.search(p).group('stat')
                sinfo = stat.split()
                stat = sinfo[0][0] + sinfo[2][0]
                if stat[1] != 'i':
                    continue

                if m.group('hdr') == 'Provides':
                    provides = m.group('pkg')
                else:
                    provides = None

                vers = versob.search(p).group('vers')
                desc = descob.search(p).group('desc')

                info = (pack,stat,vers,desc,provides)
                ret.append(info)
                group = groupfor.get(pack)
                if group:
                    for item in group:
                        found[item] = True
                if provides not in found:
                    found[provides] = True

    if skip_notfound:
        return ret

    for group in groups:
        notfound = [x for x in group if x not in found]
        if len(notfound) == len(group):
            if group not in found:
                ret.append( (' | '.join(group), 'pn', '<none>',
                             '(no description available)', None) )

    return ret

def packages_providing(package):
    aret = get_package_info([((package,), package)], skip_notfound=True)
    ret = []
    for pkg in aret:
        ret.append( (pkg[0], pkg[3]) )

    return ret

def get_dependency_info(package, depends, rel="depends on"):
    if not depends:
        return ('\n%s %s no packages.\n' % (package, rel))

    dependencies = []
    for dep in depends:
        for bit in dep:
            dependencies.append( (tuple(dep), bit) )

    depinfo = "\nVersions of packages %s %s:\n" % (package, rel)

    packs = {}
    for info in get_package_info(dependencies):
        pkg = info[0]
        if pkg not in packs:
            packs[pkg] = info
        elif info[4]:
            if not packs[pkg][4]:
                packs[pkg] = info

    deplist = packs.values()
    deplist.sort()
    maxlen = max([len(x[2]) for x in deplist] + [10])

    for (pack, status, vers, desc, provides) in deplist:
        if provides:
            pack += ' [' + provides + ']'

        packstuff = '%-*.*s %s' % (39-maxlen, 39-maxlen, pack, vers)

        info = '%-3.3s %-40.40s %-.34s\n' % (status, packstuff, desc)
        depinfo += info

    return depinfo

def get_changed_config_files(conffiles, nocompress=False):
    confinfo = {}
    changed = []
    for (filename, md5sum) in conffiles:
        try:
            fp = file(filename)
        except IOError, msg:
            confinfo[filename] = msg
            continue

        filemd5 = commands.getoutput('md5sum ' + commands.mkarg(filename)).split()[0]
        if filemd5 == md5sum: continue

        changed.append(filename)
        thisinfo = 'changed:\n'
        for line in fp:
            if not line: continue

            if line == '\n' and not nocompress: continue
            if line[0] == '#' and not nocompress: continue

            thisinfo += line

        confinfo[filename] = thisinfo

    return confinfo, changed

DISTORDER = ['stable', 'testing', 'unstable', 'experimental']

def get_debian_release_info():
    debvers = debinfo = verfile = warn = ''
    dists = []
    output = commands.getoutput('apt-cache policy 2>/dev/null')
    if output:
        mre = re.compile('\s+(\d+)\s+.*$\s+release\s.*o=(Ubuntu|Debian),a=([^,]+),', re.MULTILINE)
        found = {}
        ## XXX: When Python 2.4 rolls around, rewrite this
        for match in mre.finditer(output):
            pword, distname = match.group(1, 3)
            if distname in DISTORDER:
                pri, dist = int(pword), DISTORDER.index(distname)
            else:
                pri, dist = int(pword), len(DISTORDER)

            found[(pri, dist, distname)] = True

        if found:
            dists = found.keys()
            dists.sort()
            dists.reverse()
            dists = [(x[0], x[2]) for x in dists]
            debvers = dists[0][1]

    try:
        fob = open('/etc/debian_version')
        verfile = fob.readline().strip()
        fob.close()
    except IOError:
        print >> sys.stderr, 'Unable to open /etc/debian_version'

    if verfile:
        debinfo += 'Debian Release: '+verfile+'\n'
    if debvers:
        debinfo += '  APT prefers '+debvers+'\n'
    if dists:
        # Should wrap this eventually...
        #policystr = pprint.pformat(dists)
        policystr = ', '.join([str(x) for x in dists])
        debinfo += '  APT policy: %s\n' % policystr
    if warn:
        debinfo += warn

    return debinfo

def lsb_release_info():
    return commands.getoutput('lsb_release -a 2>/dev/null')

def get_arch():
    arch = commands.getoutput('COLUMNS=79 dpkg --print-installation-architecture 2>/dev/null')
    if not arch:
        un = os.uname()
        arch = un[4]
        arch = re.sub(r'i[456]86', 'i386', arch)
        arch = re.sub(r's390x', 's390', arch)
        arch = re.sub(r'ppc', 'powerpc', arch)
    return arch

def generate_blank_report(package, pkgversion, severity, justification,
                          depinfo, confinfo, foundfile='', incfiles='',
                          system='debian', exinfo=0, type=None, klass='',
                          subject='', tags='', body='', mode=MODE_EXPERT,
                          pseudos=None, debsumsoutput=None):
    # For now...
    import bugreport

    sysinfo = (package not in ('wnpp', 'ftp.debian.org'))

    rep = bugreport.bugreport(package, version=pkgversion, severity=severity,
                              justification=justification, filename=foundfile,
                              mode=mode, subject=subject, tags=tags, body=body,
                              pseudoheaders=pseudos, exinfo=exinfo, type=type,
                              system=system, depinfo=depinfo, sysinfo=sysinfo,
                              confinfo=confinfo, incfiles=incfiles,
                              debsumsoutput=debsumsoutput)
    return unicode(rep)

def get_cpu_cores():
    cpucount = 0
    try:
        fob = open('/proc/cpuinfo')
    except IOError:
        print >> sys.stderr, 'Unable to open /proc/cpuinfo'
        return 0

    for line in fob:
        if line.startswith('processor'):
            cpucount += 1
	#Alpha plateform
	if line.startswith('cpus detected'):
	    cpucount = int(line.split()[-1])
    fob.close()

    return max(cpucount, 1)

class our_lex(shlex.shlex):
    def get_token(self):
        token = shlex.shlex.get_token(self)
        if not len(token): return token
        if (token[0] == token[-1]) and token[0] in self.quotes:
            token = token[1:-1]
        return token

USERFILE = os.path.expanduser('~/.reportbugrc')
FILES = ('/etc/reportbug.conf', USERFILE)

CONFIG_ARGS = (
    'sendto', 'severity', 'mua', 'mta', 'email', 'realname', 'bts', 'verify',
    'replyto', 'http_proxy', 'smtphost', 'editor', 'debconf', 'justification',
    'sign', 'nocc', 'nocompress', 'dontquery', 'noconf', 'mirrors', 'keyid',
    'headers', 'interface', 'template', 'mode', 'check_available', 'query_src',
    'printonly', 'offline', 'check_uid', 'smtptls', 'smtpuser', 'smtppasswd',
    'paranoid')

class Mua:
    command = ""
    name = ""

    def __init__(self, command):
        self.command = command
        self.name = command.split()[0]

    def send(self, filename):
        mua = self.command
        if '%s' not in mua:
            mua += ' %s'
        return ui.system(mua % commands.mkarg(filename)[1:])

    def get_name(self):
        return self.name

class Gnus(Mua):
    name = "gnus"

    def __init__(self):
        pass

    def send(self, filename):
        elisp = """(progn
                      (load-file "/usr/share/reportbug/reportbug.el")
                      (tfheen-reportbug-insert-template "%s"))"""
        filename = re.sub("[\"\\\\]", "\\\\\\g<0>", filename)
        elisp = commands.mkarg(elisp % filename)
        return ui.system("emacsclient --no-wait --eval %s 2>/dev/null"
                         " || emacs --eval %s" % (elisp, elisp))

MUA = {
    'mutt' : Mua('mutt -H'),
    'mh' : Mua('/usr/bin/mh/comp -use -file'),
    'gnus' : Gnus(),
    }
MUA['nmh'] = MUA['mh']

# TODO: convert them to class methods
MUAVERSION = {
    MUA['mutt'] : 'mutt -v',
    MUA['mh'] : '/usr/bin/mh/comp -use -file',
    MUA['gnus'] : 'emacs --version',
    }

def mua_is_supported(mua):
    # check if the mua is supported by reportbug
    if mua == 'mh' or mua == MUA['mh']:
        mua_tmp = 'mh'
    elif mua == 'nmh' or mua == MUA['nmh']:
        mua_tmp = 'mh'
    elif mua == 'gnus' or mua == MUA['gnus']:
        mua_tmp = 'gnus'
    elif mua == 'mutt' or mua == MUA['mutt']:
        mua_tmp = 'mutt'
    else:
        mua_tmp = mua
    if mua_tmp not in MUA:
        return False
    else:
        return True

def mua_exists(mua):
    # check if the mua is available on the system
    if mua == 'mh' or mua == MUA['mh']:
        mua_tmp = MUA['mh']
    elif mua == 'nmh' or mua == MUA['nmh']:
        mua_tmp = MUA['mh']
    elif mua == 'gnus' or mua == MUA['gnus']:
        mua_tmp = MUA['gnus']
    elif mua == 'mutt' or mua == MUA['mutt']:
        mua_tmp = MUA['mutt']
    else:
        mua_tmp = MUA[mua]
    output = '/dev/null'
    if os.path.exists(output):
        try:
            returnvalue = subprocess.call(MUAVERSION[mua_tmp], stdout=open(output, 'w'), stderr=subprocess.STDOUT, shell=True)
        except IOError, OSError:
            returnvalue = subprocess.call(MUAVERSION[mua_tmp], shell=True)
    else:
        returnvalue = subprocess.call(MUAVERSION[mua_tmp], shell=True)
    # 127 is the shell standard return value to indicate a 'command not found' result
    if returnvalue == 127:
        return False
    else:
        return True

def mua_name(mua):
    # in case the user specifies only the mua name in --mua, returns the default options
    if mua in MUA:
        return MUA[mua]
    else:
        return mua

def first_run():
    return not os.path.exists(USERFILE)

def parse_config_files():
    args = {}
    for filename in FILES:
        if os.path.exists(filename):
            try:
                lex = our_lex(file(filename))
            except IOError, msg:
                continue

            lex.wordchars = lex.wordchars + '-.@/:<>'

            token = lex.get_token().lower()
            while token:
                if token in ('quiet', 'maintonly', 'submit'):
                    args['sendto'] = token
                elif token == 'severity':
                    token = lex.get_token().lower()
                    if token in debianbts.SEVERITIES.keys():
                        args['severity'] = token
                elif token == 'header':
                    args['headers'] = args.get('headers', []) + \
                                      [lex.get_token()]
                elif token in ('no-cc', 'cc'):
                    args['nocc'] = (token == 'no-cc')
                elif token in ('no-compress', 'compress'):
                    args['nocompress'] = (token == 'no-compress')
                elif token in ('no-query-bts', 'query-bts'):
                    args['dontquery'] = (token == 'no-query-bts')
                elif token in ('config-files', 'no-config-files'):
                    args['noconf'] = (token == 'no-config-files')
                elif token in ('printonly', 'template', 'offline'):
                    args[token] = True
                elif token in ('email', 'realname', 'replyto', 'http_proxy',
                               'smtphost', 'editor', 'mua', 'mta', 'smtpuser',
                               'smtppasswd', 'justification', 'keyid'):
                    bit = lex.get_token()
                    args[token] = bit.decode('utf-8', 'replace')
                elif token in ('no-smtptls', 'smtptls'):
                    args['smtptls'] = (token == 'smtptls')
                elif token == 'sign':
                    token = lex.get_token().lower()
                    if token in ('pgp', 'gpg'):
                        args['sign'] = token
                    elif token == 'gnupg':
                        args['sign'] = 'gpg'
                    elif token == 'none':
                        args['sign'] = ''
                elif token == 'ui':
                    token = lex.get_token().lower()
                    if token in AVAILABLE_UIS.keys():
                        args['interface'] = token
                elif token == 'mode':
                    arg = lex.get_token().lower()
                    if arg in MODES.keys():
                        args[token] = arg
                elif token == 'bts':
                    token = lex.get_token().lower()
                    if token in debianbts.SYSTEMS.keys():
                        args['bts'] = token
                elif token == 'mirror':
                    args['mirrors'] = args.get('mirrors', []) + \
                                      [lex.get_token()]
                elif token in ('no-check-available', 'check-available'):
                    args['check_available'] = (token == 'check-available')
                elif token == 'reportbug_version':
                    # Currently ignored; might be used for compat purposes
                    # eventually
                    w_version = lex.get_token().lower()
                elif token in MUA:
                    args['mua'] = MUA[token]
                elif token in ('query-source', 'no-query-source'):
                    args['query_src'] = (token == 'query-source')
                elif token in ('debconf', 'no-debconf'):
                    args['debconf'] = (token == 'debconf')
                elif token in ('verify', 'no-verify'):
                    args['verify'] = (token == 'verify')
                elif token in ('check-uid', 'no-check-uid'):
                    args['check_uid'] = (token == 'check-uid')
                elif token in ('paranoid', 'no-paranoid'):
                    args['paranoid'] = (token == 'paranoid')
                else:
                    sys.stderr.write('Unrecognized token: %s\n' % token)

                token = lex.get_token().lower()

    return args

def parse_bug_control_file(filename):
    submitas = submitto = None
    reportwith = []
    supplemental = []
    fh = file(filename)
    for line in fh:
        line = line.strip()
        parts = line.split(': ')
        if len(parts) != 2:
            continue

        header, data = parts[0].lower(), parts[1]
        if header == 'submit-as':
            submitas = data
        elif header == 'send-to':
            submitto = data
        elif header == 'report-with':
            reportwith += data.split(' ')
        elif header == 'package-status':
            supplemental += data.split(' ')

    return submitas, submitto, reportwith, supplemental

def cleanup_msg(dmessage, headers, pseudos, type):
    pseudoheaders = []
    # Handle non-pseduo-headers
    headerre = re.compile(r'^([^:]+):\s*(.*)$', re.I)
    newsubject = message = ''
    parsing = lastpseudo = True

    # Include the headers that were passed in too!
    newheaders = []
    for header in headers:
        mob = headerre.match(header)
        if mob:
            newheaders.append(mob.groups())

    # Get the pseudo-headers fields
    PSEUDOS = []
    for ph in pseudos:
        mob = headerre.match(ph)
        if mob:
            PSEUDOS.append(mob.group(1))

    for line in dmessage.split(os.linesep):
        if not line and parsing:
            parsing = False
        elif parsing:
            mob = headerre.match(line)
            # GNATS and debbugs have different ideas of what a pseudoheader
            # is...
            if mob and ((type == 'debbugs' and
                         mob.group(1) not in PSEUDOHEADERS and
                         mob.group(1) not in PSEUDOS) or
                        (type == 'gnats' and mob.group(1)[0] != '>')):
                newheaders.append(mob.groups())
                lastpseudo = False
                continue
            elif mob:
                # Normalize pseudo-header
                lastpseudo = False
                key, value = mob.groups()
                if key[0] != '>':
                    # Normalize hyphenated headers to capitalize each word
                    key = '-'.join([x.capitalize() for x in key.split('-')])
                pseudoheaders.append((key, value))
            elif not lastpseudo and len(newheaders):
                # Assume we have a continuation line
                lastheader = newheaders[-1]
                newheaders[-1] = (lastheader[0], lastheader[1] + '\n' + line)
                continue
            else:
                # Permit bogus headers in the pseudoheader section
                headers.append(re.split(':\s+', line, 1))
        elif line.strip() != NEWBIELINE:
            message += line + '\n'

    ph = []
    if type == 'gnats':
        for header, content in pseudoheaders:
            if content:
                ph += ["%s: %s" % (header, content)]
            else:
                ph += [header]
    else:
        ph2 = {}
        for header, content in pseudoheaders:
            # if either in the canonical pseudo-headers list or in those passed on the command line
            if header in list(PSEUDOHEADERS) + PSEUDOS:
                ph2[header] = content
            else:
                newheaders.append( (header, content) )

        for header in list(PSEUDOHEADERS) + PSEUDOS:
            if header in ph2:
                ph += ['%s: %s' % (header, ph2[header])]

    return message, newheaders, ph
