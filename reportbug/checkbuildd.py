#
# reportbuglib/checkbuildd.py
# Check buildd.debian.org for successful past builds
#
#   Written by Chris Lawrence <lawrencc@debian.org>
#   (C) 2002 Chris Lawrence
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

import sgmllib
import commands

from urlutils import open_url
from reportbug_exceptions import (
    NoNetwork,
    )

BUILDD_URL = 'http://buildd.debian.org/build.php?arch=%s&pkg=%s'

# This is easy; just look for succeeded in an em block...

class BuilddParser(sgmllib.SGMLParser):
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.versions = {}
        self.savedata = None
        self.found_succeeded = False

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

    def start_em(self, attrs):
        self.save_bgn()

    def end_em(self):
        data = self.save_end()
        if data and 'successful' in data:
            self.found_succeeded=True

def archname():
    return commands.getoutput('dpkg --print-architecture')

def check_built(src_package, arch=None, http_proxy=None):
    if not arch:
        arch = archname()

    try:
        page = open_url(BUILDD_URL % (arch, src_package), http_proxy)
    except NoNetwork:
        return {}
    if not page:
        return {}

    parser = BuilddParser()
    parser.feed(page.read())
    parser.close()
    page.close()

    return parser.found_succeeded
