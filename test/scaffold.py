# -*- coding: utf-8 -*-

# scaffold.py
#
# Copyright © 2007-2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Scaffolding for unit test modules
"""

import unittest
import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(test_dir)
if not test_dir in sys.path:
    sys.path.insert(1, test_dir)
if not parent_dir in sys.path:
    sys.path.insert(1, parent_dir)


def suite(module_name):
    """ Create the test suite for named module """
    from sys import modules
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(modules[module_name])
    return suite

def unittest_main(argv=None):
    """ Mainline function for each unit test module """

    from sys import argv as sys_argv
    if not argv:
        argv = sys_argv

    exitcode = None
    try:
        unittest.main(argv=argv, defaultTest='suite')
    except SystemExit, e:
        exitcode = e.code

    return exitcode


def make_module_from_file(module_name, file_name):
    """ Make a new module object from the code in specified file """

    from types import ModuleType
    module = ModuleType(module_name)

    module_file = open(file_name, 'r')
    exec module_file in module.__dict__

    return module


class TestCase(unittest.TestCase):
    """ Test case behaviour """

    def failUnlessRaises(self, exc_class, func, *args, **kwargs):
        """ Fail unless the function call raises the expected exception

            Fail the test if an instance of the exception class
            ``exc_class`` is not raised when calling ``func`` with the
            arguments ``*args`` and ``**kwargs``.

            """

        try:
            super(TestCase, self).failUnlessRaises(
                exc_class, func, *args, **kwargs)
        except self.failureException:
            exc_class_name = exc_class.__name__
            msg = (
                "Exception %(exc_class_name)s not raised"
                " for function call:"
                " func=%(func)r args=%(args)r kwargs=%(kwargs)r"
                ) % vars()
            raise self.failureException(msg)


    def failIfIs(self, first, second, msg=None):
        """ Fail if the two objects are identical

            Fail the test if ``first`` and ``second`` are identical,
            as determined by the ``is`` operator.

            """

        if first is second:
            if msg is None:
                msg = "%(first)r is %(second)r" % vars()
            raise self.failureException(msg)

    def failUnlessIs(self, first, second, msg=None):
        """ Fail unless the two objects are identical

            Fail the test unless ``first`` and ``second`` are
            identical, as determined by the ``is`` operator.

            """

        if first is not second:
            if msg is None:
                msg = "%(first)r is not %(second)r" % vars()
            raise self.failureException(msg)

    assertIs = failUnlessIs
    assertNotIs = failIfIs

    def failIfIn(self, first, second, msg=None):
        """ Fail if the second object is in the first

            Fail the test if ``first`` contains ``second``, as
            determined by the ``in`` operator.

            """

        if second in first:
            if msg is None:
                msg = "%(second)r is in %(first)r" % vars()
            raise self.failureException(msg)

    def failUnlessIn(self, first, second, msg=None):
        """ Fail unless the second object is in the first

            Fail the test unless ``first`` contains ``second``, as
            determined by the ``in`` operator.

            """

        if second not in first:
            if msg is None:
                msg = "%(second)r is not in %(first)r" % vars()
            raise self.failureException(msg)

    assertIn = failUnlessIn
    assertNotIn = failIfIn

    def failUnlessOutputCheckerMatch(self, want, got, msg=None):
        """ Fail unless the specified string matches the expected

            Fail the test unless ``want`` matches ``got``, as
            determined by a ``doctest.OutputChecker`` instance. This
            is not an equality check, but a pattern match according to
            the OutputChecker rules.

            """

        checker = doctest.OutputChecker()
        want = textwrap.dedent(want)
        got = textwrap.dedent(got)
        if not checker.check_output(want, got, doctest.ELLIPSIS):
            if msg is None:
                msg = ("Expected %(want)r, got %(got)r:"
                       "\n--- want: ---\n%(want)s"
                       "\n--- got: ---\n%(got)s") % vars()
            raise self.failureException(msg)

    assertOutputCheckerMatch = failUnlessOutputCheckerMatch

    def failIfIsInstance(self, obj, classes):
        """ Fail if the object is an instance of the specified classes

            Fail the test if the object ``obj`` is an instance of any
            of ``classes``.

            """

        if isinstance(obj, classes):
            msg = "%(obj)r is an instance of one of %(classes)r" % vars()
            raise self.failureException(msg)

    def failUnlessIsInstance(self, obj, classes):
        """ Fail unless the object is an instance of the specified classes

            Fail the test unless the object ``obj`` is an instance of
            any of ``classes``.

            """

        if not isinstance(obj, classes):
            msg = "%(obj)r is not an instance of any of %(classes)r" % vars()
            raise self.failureException(msg)

    assertIsInstance = failUnlessIsInstance
    assertNotIsInstance = failIfIsInstance

    def failUnlessFunctionInTraceback(self, traceback, function):
        """ Fail if the function is not in the traceback

            Fail the test if the function ``function`` is not at any
            of the levels in the traceback object ``traceback``.

            """

        func_in_traceback = False
        expect_code = function.func_code
        current_traceback = traceback
        while current_traceback is not None:
            if expect_code is current_traceback.tb_frame.f_code:
                func_in_traceback = True
                break
            current_traceback = current_traceback.tb_next

        if not func_in_traceback:
            msg = ("Traceback did not lead to original function"
                " %(function)s"
                ) % vars()
            raise self.failureException(msg)

    assertFunctionInTraceback = failUnlessFunctionInTraceback


class Test_Exception(TestCase):
    """ Test cases for exception classes """

    def __init__(self, *args, **kwargs):
        """ Set up a new instance """
        self.valid_exceptions = NotImplemented
        super(Test_Exception, self).__init__(*args, **kwargs)

    def setUp(self):
        """ Set up test fixtures """
        for exc_type, params in self.valid_exceptions.items():
            args = (None,) * params['min_args']
            params['args'] = args
            instance = exc_type(*args)
            params['instance'] = instance

        self.iterate_params = make_params_iterator(
            default_params_dict = self.valid_exceptions
            )

        super(Test_Exception, self).setUp()

    def test_exception_instance(self):
        """ Exception instance should be created """
        for key, params in self.iterate_params():
            instance = params['instance']
            self.failIfIs(None, instance)

    def test_exception_types(self):
        """ Exception instances should match expected types """
        for key, params in self.iterate_params():
            instance = params['instance']
            for match_type in params['types']:
                match_type_name = match_type.__name__
                fail_msg = (
                    "%(instance)r is not an instance of"
                    " %(match_type_name)s"
                    ) % vars()
                self.failUnless(
                    isinstance(instance, match_type),
                    msg=fail_msg)
