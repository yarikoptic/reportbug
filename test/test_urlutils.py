# -*- coding: utf-8; -*-

# test/test_urlutils.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for urlutils module
"""

import httplib

import scaffold
from scaffold import TestCase

import reportbug_exceptions
import urlutils


class StubObject(object):
    """ A stub object that allows any access. """

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return StubObject()

    def __call__(self, *args, **kwargs):
        return StubObject()


class Test_open_url(TestCase):
    """ Test cases for urlopen function """

    def setUp(self):
        """ Set up test fixtures """
        self.stub_opener = StubObject()
        def stub_build_opener(*args, **kwargs):
            return self.stub_opener

        self.urllib2_prev = urlutils.urllib2
        self.stub_urllib2 = StubObject()
        urlutils.urllib2 = self.stub_urllib2

        self.stub_urllib2.Request = StubObject
        self.stub_urllib2.build_opener = stub_build_opener

    def tearDown(self):
        """ Tear down test fixtures """
        urlutils.urllib2 = self.urllib2_prev

    def test_raises_no_network_when_http_exception(self):
        """ Should raise NoNetwork when opener raises HTTPExeception """
        class ArbitraryHTTPException(httplib.HTTPException):
            pass
        def stub_raise_bad_status_line(self, *args, **kwargs):
            message = "Bad HTTP stuff happened!"
            raise ArbitraryHTTPException(message)
        self.stub_opener.open = stub_raise_bad_status_line

        url = "foo"
        expect_exception = reportbug_exceptions.NoNetwork
        self.failUnlessRaises(
            expect_exception,
            urlutils.open_url, url)
