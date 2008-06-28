# Author: Sandro Tosi
# Date: 2008-05-16
# License: Public domain
#
# Python script to compare pseudo-packages listed in reportbug
# agaists the official list on ftp-master

import sys, os
sys.path = ['.'] + sys.path

import reportbuglib.debianbts as debianbts

import urllib, re

# separete a sequence of "char not spaces", from at least one space (ftp-master uses tabs), from anything after tabs
# we group the first and the latter, so we get the pseudo-packages name and description
dictparse = re.compile(r'([^\s]+)\s+(.+)',re.IGNORECASE)

ftpmaster_list = {}
pseudo = urllib.urlopen('http://ftp-master.debian.org/pseudo-packages.description')
for l in pseudo:
    m = dictparse.search(l)
    ftpmaster_list[m.group(1)] = m.group(2)

bts_keys=debianbts.debother.keys();

diff_rb_ftp = set(bts_keys)-set(ftpmaster_list)
diff_ftp_rb = set(ftpmaster_list)-set(bts_keys)

print "pseudo-pkgs in reportbug not in ftpmaster list:", diff_rb_ftp

for pkg in diff_rb_ftp:
    print "   ", pkg,": ", debianbts.debother[pkg]

print "pseudo-pkgs in ftpmaster list not in reprotbug:", diff_ftp_rb

for pkg in diff_ftp_rb:
    print "   ", pkg,": ", ftpmaster_list[pkg]
