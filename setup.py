#!/usr/bin/env python
#
# $Id: setup.py,v 1.8 2005/03/04 04:45:44 lordsutch Exp $

from setuptools import setup
import reportbug
import os
import glob

# i18n = []
# for lang in glob.glob('*.po'):
#     lang = lang[:-3]
#     if lang == 'messages':
#         continue
#     i18n.append( ('share/locale/%s/LC_MESSAGES' % lang,
#                   ['i18n/%s/LC_MESSAGES/foomatic-gui.mo' % lang]) )

setup(name='reportbug', version=reportbug.VERSION_NUMBER,
      description='bug reporting tool',
      author='reportbug maintainence team',
      author_email='reportbug-maint@lists.alioth.debian.org',
      url='http://alioth.debian.org/projects/reportbug',
      data_files=[('share/reportbug', ['handle_bugscript', 'reportbug.el']),
                  ('share/bug/reportbug', ['presubj', 'script'])],
      license='MIT', packages=['reportbug'],
      scripts=['bin/reportbug', 'bin/querybts'])
