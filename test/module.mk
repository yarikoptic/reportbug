# :vim: filetype=make : -*- makefile; coding: utf-8; -*-

# test/module.mk
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+debian@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

# Makefile module for test suite

MODULE_DIR := ${TEST_DIR}

NOSETESTS = nosetests
NOSETESTS_OPTS = --exclude='^(?!test_)'
PYFLAKES = pyflakes
PYLINT = pylint
COVERAGE = python-coverage
DATE = date
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
INWAIT = inotifywait
INWAIT_OPTS = -q -r -e modify -e create -t 0
TEST_INWAIT_FILES = ${CODE_PACKAGE_DIR} ${CODE_PROGRAMS} ${TEST_DIR}

NOSETESTS_FILES = ${TEST_DIR}
nosetests_cmd = $(NOSETESTS) ${NOSETESTS_OPTS} ${NOSETESTS_FILES}

coverage_files += ${CODE_MODULES}
# Not until python-coverage is updated with upstream fixes (2008-05-04)
#coverage_files += ${CODE_PROGRAMS}

GENERATED_FILES += .coverage


# usage: $(call test-output-banner,message)
define test-output-banner
	@ echo -n ${1} ; \
	$(DATE) +${DATE_FORMAT}
endef


.PHONY: nosetests
nosetests:
	$(call test-output-banner, "Test run: " )
	$(nosetests_cmd)

test: nosetests

# usage: $(call test-wait)
define test-wait
	$(INWAIT) ${INWAIT_OPTS} ${TEST_INWAIT_FILES}
endef

.PHONY: test-continuous
test-continuous:
	while true ; do \
		clear ; \
		$(MAKE) test ; \
		$(call test-wait) ; \
	done


.PHONY: pyflakes
pyflakes:
	$(PYFLAKES) .

.PHONY: pylint
pylint:
	$(PYLINT) ${CODE_PACKAGE_DIR}
	$(PYLINT) ${CODE_PROGRAMS}
	$(PYLINT) ${TEST_DIR}

.PHONY: coverage
coverage: NOSETEST_OPTS += --with-coverage
coverage:
	$(nosetests_cmd)
	$(COVERAGE) -r -m ${coverage_files}

qa: pyflakes coverage
