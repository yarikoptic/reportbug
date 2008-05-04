# :vim: filetype=make : -*- makefile; coding: utf-8; -*-

# module.mk
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+debian@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

# Makefile module for reportbug Python package

MODULE_DIR := .

CODE_MODULES += $(shell find ${CODE_PACKAGE_DIR} -name '*.py')

CODE_PROGRAM_NAMES += reportbug
CODE_PROGRAM_NAMES += querybts
CODE_PROGRAM_NAMES += handle_bugscript
CODE_PROGRAM_NAMES += script

CODE_PROGRAMS += $(addprefix ${CODE_PROGRAM_DIR}/,${CODE_PROGRAM_NAMES})

GENERATED_FILES += $(shell find ${MODULE_DIR} -name '*.pyc')

PYTHON = python
