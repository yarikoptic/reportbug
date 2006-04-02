#
# checkversions.py - Find if the installed version of a package is the latest
#
#   Written by Chris Lawrence <lawrencc@debian.org>
#   (C) 2002-04 Chris Lawrence
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
# $Id: checkversions.py,v 1.4 2006-04-02 06:16:12 lawrencc Exp $
#
# Version ##VERSION##; see changelog for revision history

import sgmllib, os, re, sys, urllib2
from urlutils import open_url
from reportbug_exceptions import *

PACKAGES_URL = 'http://packages.debian.org/%s'
INCOMING_URL = 'http://incoming.debian.org/'

# The format is an unordered list

class PackagesParser(sgmllib.SGMLParser):
    def __init__(self, arch='i386'):
        sgmllib.SGMLParser.__init__(self)
        self.versions = {}
        self.savedata = None
        self.row = None
        arch = r'\b(all|'+re.escape(arch)+r')\b'
        self.arch = re.compile(arch)
        self.dist = None

    # --- Formatter interface, taking care of 'savedata' mode;
    # shouldn't need to be overridden

    def handle_data(self, data):
        if self.savedata is not None:
            self.savedata = self.savedata + data

    # --- Hooks to save data; shouldn't need to be overridden
    def save_bgn(self):
        self.savedata = ''

    def save_end(self, mode=0):
        data = self.savedata
        self.savedata = None
        if not mode and data is not None: data = ' '.join(data.split())
        return data

    def start_li(self, attrs):
        if self.row is not None:
            self.end_li()
        self.row = []

    def start_a(self, attrs):
        if self.row is not None:
            self.save_bgn()

    def end_a(self):
        if self.row is not None and self.savedata:
            self.dist = self.save_end()

    def lineend(self):
        line = self.save_end().strip()
        if self.arch.search(line):
            version = line.split(': ', 1)
            self.versions[self.dist] = version[0]

    def start_br(self, attrs):
        if self.savedata:
            self.lineend()
        self.save_bgn()

    def end_li(self):
        if self.savedata:
            self.lineend()
        self.row = None

class IncomingParser(sgmllib.SGMLParser):
    def __init__(self, package, arch='i386'):
        sgmllib.SGMLParser.__init__(self)
        self.found = []
        self.savedata = None
        arch = r'(?:all|'+re.escape(arch)+')'
        self.package = re.compile(re.escape(package)+r'_([^_]+)_'+arch+'.deb')

    def start_a(self, attrs):
        for attrib, value in attrs:
            if attrib.lower() != 'href':
                continue
            
            mob = self.package.match(value)
            if mob:
                self.found.append(mob.group(1))

def compare_versions(current, upstream):
    """Return 1 if upstream is newer than current, -1 if current is
    newer than upstream, and 0 if the same."""
    if not upstream: return 0
    rc = os.system('dpkg --compare-versions %s lt %s' % (current, upstream))
    rc2 = os.system('dpkg --compare-versions %s gt %s' % (current, upstream))
    if not rc:
        return 1
    elif not rc2:
        return -1
    return 0

def later_version(a, b):
    if compare_versions(a, b) > 0:
        return b
    return a

def get_versions_available(package, dists=None, http_proxy=None, arch='i386'):
    if not dists:
        dists = ('stable', 'testing', 'unstable')

    try:
        page = open_url(PACKAGES_URL % package, http_proxy)
    except NoNetwork:
        return {}
    except urllib2.HTTPError, x:
        print >> sys.stderr, "Warning:", x
        return {}
    if not page:
        return {}

    content = page.read()
    parser = PackagesParser(arch)
    parser.feed(content)
    parser.close()
    page.close()

    versions = {}
    for dist in dists:
        if dist in parser.versions:
            versions[dist] = parser.versions[dist]

    return versions

def get_incoming_version(package, http_proxy=None, arch='i386'):
    try:
        page = open_url(INCOMING_URL, http_proxy)
    except NoNetwork:
        return None
    except urllib2.HTTPError, x:
        print >> sys.stderr, "Warning:", x
        return None
    if not page:
        return None
    
    parser = IncomingParser(package, arch)
    parser.feed(page.read())
    parser.close()
    page.close()

    if parser.found:
        return reduce(later_version, parser.found, '0')
    
    return None

def check_available(package, version, dists=None, check_incoming=True,
                    http_proxy=None, arch='i386'):
    avail = {}

    if check_incoming:
        iv = get_incoming_version(package, http_proxy, arch)
        if iv:
            avail['incoming'] = iv

    avail.update(get_versions_available(package, dists, http_proxy, arch))

    new = {}
    newer = 0
    for dist in avail:
        if dist == 'incoming':
            if ':' in version:
                ver = version.split(':', 1)[1]
            else:
                ver = version
            comparison = compare_versions(ver, avail[dist])
        else:
            comparison = compare_versions(version, avail[dist])
        if comparison > 0:
            new[dist] = avail[dist]
        elif comparison < 0:
            newer += 1
    if newer and newer == len(avail):
        return new, True
    return new, False

if __name__=='__main__':
    #print check_available('mozilla-browser', '2:1.5-3', arch='s390')
    print check_available('reportbug', '3.17', arch='i386')
    print check_available('reportbug', '3.25', arch='i386')
    print check_available('reportbug', '3.7', arch='i386')
    #print check_available('dpkg', '1.10.2', arch='sparc')
