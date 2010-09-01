#! /usr/bin/make -f

.PHONY: checks
checks:
	PYTHONPATH=. $(PYTHON) checks/compare_pseudo-pkgs_lists.py
