# Author: Sandro Tosi <morph@debian.org>
# Date: 2008-05-16
# License: Public domain
#
# Python script to compare pseudo-packages listed in reportbug
# agaists the official list on bugs.debian.org

import sys, os
sys.path = ['.'] + sys.path

from reportbug import utils
from reportbug import debianbts

import urllib, re

# separete a sequence of "char not spaces", from at least one space (canonical copy uses tabs), from anything after tabs
# we group the first and the latter, so we get the pseudo-packages name and description
dictparse = re.compile(r'([^\s]+)\s+(.+)',re.IGNORECASE)

bdo_list = {}
pseudo = urllib.urlopen('http://bugs.debian.org/pseudopackages/pseudo-packages.description')
for l in pseudo:
    m = dictparse.search(l)
    bdo_list[m.group(1)] = m.group(2)

bts_keys=debianbts.debother.keys();

diff_rb_bdo = set(bts_keys)-set(bdo_list)
diff_bdo_rb = set(bdo_list)-set(bts_keys)

print "pseudo-pkgs in reportbug not in bugs.debian.org list:", diff_rb_bdo

for pkg in diff_rb_bdo:
    print "   ", pkg,": ", debianbts.debother[pkg]

print "pseudo-pkgs in bugs.debian.org list not in reportbug:", diff_bdo_rb

for pkg in diff_bdo_rb:
    print "   ", pkg,": ", bdo_list[pkg]
