# -*- coding: utf-8; -*-

# test/test_reportbug_program.py
# Part of reportbug, a Debian bug reporting tool.
#
# Copyright © 2008 Ben Finney <ben+python@benfinney.id.au>
# This is free software; you may copy, modify and/or distribute this work
# under the terms of the GNU General Public License, version 2 or later.
# No warranty expressed or implied. See the file LICENSE for details.

""" Unit test for reportbug program
"""

import __builtin__
import os
from StringIO import StringIO

import scaffold
from scaffold import TestCase

module_name = 'reportbug'
module_file_path = os.path.join(scaffold.bin_dir, "reportbug")
reportbug = scaffold.make_module_from_file(module_name, module_file_path)


def setup_include_file_in_report_fixture(testcase):
    """ Set up test fixtures for 'include_file_in_report' function """

    testcase.temp_filename = "bogus"
    testcase.temp_file = StringIO()
    testcase.temp_file.actually_close = testcase.temp_file.close
    testcase.temp_file.close = lambda: None

    def stub_temp_file(
        suffix="", prefix=None, dir=None, text=True,
        mode="w+", bufsize=-1):
        """ Return a stub file and filename


            :return value:
                Tuple (`temp_file`, `temp_filename`)

                The filename will be as set in the testcase's
                `temp_filename` attribute.

                The file returned will be a StringIO buffer, with the
                `close` method disabled. The `actually_close` method
                will free the buffer.

            """
        temp_filename = testcase.temp_filename
        temp_file = testcase.temp_file
        return (temp_file, temp_filename)
    testcase.stub_temp_file = stub_temp_file


class Test_include_file_in_report(TestCase):
    """ Test cases for 'include_file_in_report' function """

    def setUp(self):
        """ Set up test fixtures """

        setup_include_file_in_report_fixture(self)

        self.temp_file_func_prev = reportbug.TempFile
        reportbug.TempFile = self.stub_temp_file

    def tearDown(self):
        """ Tear down test fixtures """
        reportbug.TempFile = self.temp_file_func_prev

    def test_adds_include_filename_to_attachments(self):
        """ Filename of include file should be added to attachments

            When the `inline` parameter is not True, the filename of
            the include file should be appended to the
            attachment_filenames list.

            """
        message = ""
        message_filename = "report"
        attachment_filenames = ["foo", "bar"]
        package_name = "spam"
        include_filename = self.temp_filename
        expect_attachment_filenames = attachment_filenames
        expect_attachment_filenames.append(include_filename)
        (nil, nil, attachment_filenames) = reportbug.include_file_in_report(
            message, message_filename, attachment_filenames, package_name,
            include_filename)
        self.failUnlessEqual(
            expect_attachment_filenames, attachment_filenames)

class Test_include_file_in_report_inline(TestCase):
    """ Test cases for 'include_file_in_report' function, inline=True """

    def setUp(self):
        """ Set up test fixtures """

        setup_include_file_in_report_fixture(self)

        self.temp_file_func_prev = reportbug.TempFile
        reportbug.TempFile = self.stub_temp_file

        self.message = """
            Lorem ipsum.
            Lorem ipsum.
            """
        self.message_filename = "report"
        self.attachment_filenames = []
        self.package_name = "spam"

        self.include_filename = "bogus_include"
        self.include_file_content = """
            Phasellus posuere. Nulla malesuada lacinia justo.
            Nunc condimentum ante vitae erat.
            """
        self.include_file = StringIO(self.include_file_content)

        self.builtin_file_prev = __builtin__.file
        def stub_builtin_file(path, mode=None, buffering=None):
            if path != self.include_filename:
                raise IOError("Not found: %(path)s" % vars())
            return self.include_file
        __builtin__.file = stub_builtin_file

        self.os_unlink_prev = os.unlink
        def stub_os_unlink(filename):
            pass
        os.unlink = stub_os_unlink

    def tearDown(self):
        """ Tear down test fixtures """
        self.temp_file.actually_close()
        reportbug.TempFile = self.temp_file_func_prev
        __builtin__.file = self.builtin_file_prev
        os.unlink = self.os_unlink_prev

    def test_adds_include_file_content_to_message(self):
        """ Content of include file should be added to message

            When the `inline` parameter is True, the content of the
            include file should be added into the report message.

            """
        (message, nil, nil) = reportbug.include_file_in_report(
            self.message, self.message_filename,
            self.attachment_filenames, self.package_name,
            self.include_filename, inline=True)
        self.failUnlessIn(message, self.include_file_content)

    def test_returns_new_temp_filename_as_message_filename(self):
        """ New message filename should be as generated by TempFile

            When the `inline` parameter is True, the returned message
            filename should be that of the generated temporary file.

            """
        (nil, message_filename, nil) = reportbug.include_file_in_report(
            self.message, self.message_filename,
            self.attachment_filenames, self.package_name,
            self.include_filename, inline=True)
        temp_filename = self.temp_filename
        self.failUnlessEqual(message_filename, temp_filename)

    def test_writes_new_message_content_to_report_file(self):
        """ New message content should be written to report file

            When the `inline` parameter is True, the updated content
            of the message should be written to the report file.

            """
        (message, nil, nil) = reportbug.include_file_in_report(
            self.message, self.message_filename,
            self.attachment_filenames, self.package_name,
            self.include_filename, inline=True)
        temp_filename = self.temp_filename
        temp_file = self.temp_file
        self.failUnlessEqual(message, temp_file.getvalue())
