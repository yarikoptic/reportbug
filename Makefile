#! /usr/bin/make -f

# Makefile
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+debian@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

# Makefile for reportbug project

SHELL = /bin/bash
PATH = /usr/bin:/bin

# Directories with semantic meaning
CODE_PACKAGE_DIR := .
CODE_PROGRAM_DIR := .
TEST_DIR := test

# Variables that will be extended by module include files
GENERATED_FILES :=
CODE_MODULES :=
CODE_PROGRAMS :=

# List of modules (directories) that comprise our 'make' project
MODULES += ${CODE_PACKAGE_DIR}
MODULES += ${TEST_DIR}

RM = rm


.PHONY: all
all: build

.PHONY: build
build:

.PHONY: install
install: build


.PHONY: clean
clean:
	$(RM) -rf ${GENERATED_FILES}


.PHONY: test
test:

.PHONY: qa
qa:

# Include the make data for each module
include $(patsubst %,%/module.mk,${MODULES})
