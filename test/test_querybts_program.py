# -*- coding: utf-8; -*-

# test/test_querybts_program.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for querybts program
"""

import os

import scaffold

module_name = 'querybts'
module_file_path = os.path.join(scaffold.bin_dir, "querybts")
querybts = scaffold.make_module_from_file(module_name, module_file_path)
