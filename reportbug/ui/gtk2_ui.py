# a graphical (GTK+) user interface
#   Written by Luca Bruno <lethalman88@gmail.com>
#   Based on gnome-reportbug work done by Philipp Kern <pkern@debian.org>
#   Copyright (C) 2006 Philipp Kern
#   Copyright (C) 2008 Luca Bruno
#
# This program is freely distributable per the following license:
#
##  Permission to use, copy, modify, and distribute this software and its
##  documentation for any purpose and without fee is hereby granted,
##  provided that the above copyright notice appears in all copies and that
##  both that copyright notice and this permission notice appear in
##  supporting documentation.
##
##  I DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
##  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL I
##  BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
##  DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
##  WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
##  ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
##  SOFTWARE.
#
# Version ##VERSION##; see changelog for revision history

try:
    import gtk
    from gtk import gdk
    import gobject
except ImportError:
    raise UINotImportable, 'Please install the python-gtk2 package to use this interface.'

gdk.threads_init ()

import sys
import re
import os
import traceback
from Queue import Queue
import threading

from reportbug.exceptions import NoPackage, NoBugs, NoNetwork, NoReport
from reportbug import debianbts
from reportbug.urlutils import launch_browser

ISATTY = True
DEBIAN_LOGO = "/usr/share/pixmaps/debian-logo.png"

global application, assistant

# Utilities

def highlight (s):
    return '<b>%s</b>' % s

re_markup_free = re.compile ("<.*?>")

def markup_free (s):
    return re_markup_free.sub ("", s)

def ask_free (s):
    s = s.strip ()
    if s[-1] in ('?', ':'):
        return s[:-1]
    return s

def create_scrollable (widget):
    scrolled = gtk.ScrolledWindow ()
    scrolled.set_shadow_type (gtk.SHADOW_ETCHED_IN)
    scrolled.set_policy (gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    scrolled.add (widget)
    return scrolled

def info_dialog (message):
    dialog = gtk.MessageDialog (assistant, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, message)
    dialog.connect ('response', lambda *args: dialog.destroy ())
    dialog.set_title ('Reportbug')
    dialog.show_all ()

def error_dialog (message):
    dialog = gtk.MessageDialog (assistant, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, message)
    dialog.connect ('response', lambda *args: dialog.destroy ())
    dialog.set_title ('Reportbug')
    dialog.show_all ()

class CustomDialog (gtk.Dialog):
    def __init__ (self, stock_image, message, buttons, *args, **kwargs):
        gtk.Dialog.__init__ (self, "Reportbug", assistant,
                             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             buttons)
        # Try following the HIG
        self.set_default_response (buttons[-1]) # this is the response of the last button
        self.set_border_width (5)

        vbox = gtk.VBox (spacing=10)
        vbox.set_border_width (6)
        self.vbox.pack_start (vbox)
        
        # The header image + label
        hbox = gtk.HBox (spacing=10)
        vbox.pack_start (hbox, expand=False)

        align = gtk.Alignment (0.5, 0.5, 1.0, 1.0)
        hbox.pack_start (align, expand=False)

        image = gtk.image_new_from_stock (stock_image, gtk.ICON_SIZE_DIALOG)
        hbox.pack_start (image)
        
        label = gtk.Label (message)
        label.set_line_wrap (True)
        label.set_justify (gtk.JUSTIFY_FILL)
        hbox.pack_start (label, expand=False)

        self.setup_dialog (vbox, *args, **kwargs)

class InputStringDialog (CustomDialog):
    def __init__ (self, message):
        CustomDialog.__init__ (self, gtk.STOCK_DIALOG_INFO, message,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

    def setup_dialog (self, vbox):
        self.entry = gtk.Entry ()
        vbox.pack_start (self.entry, expand=False)

    def get_value (self):
        return self.entry.get_text ()

class ExceptionDialog (CustomDialog):
    # Register an exception hook to display an error when the GUI breaks
    @classmethod
    def create_excepthook (cls, oldhook):
        def excepthook (exctype, value, tb):
            if oldhook:
                oldhook (exctype, value, tb)
            application.run_once_in_main_thread (cls.start_dialog,
                                                 ''.join (traceback.format_exception (exctype, value, tb)))
        return excepthook

    @classmethod
    def start_dialog (cls, tb):
        try:
            dialog = cls (tb)
            dialog.show_all ()
        except:
            sys.exit (1)

    def __init__ (self, tb):
        CustomDialog.__init__ (self, gtk.STOCK_DIALOG_ERROR, "An error has occurred while doing an operation in Reportbug.\nPlease report the bug.", (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE), tb)

    def setup_dialog (self, vbox, tb):
        # The traceback
        expander = gtk.Expander ("More details")
        vbox.pack_start (expander)

        view = gtk.TextView ()
        view.set_editable (False)
        view.get_buffer().set_text (tb)
        scrolled = create_scrollable (view)
        expander.add (scrolled)

        self.connect ('response', self.on_response)

    def on_response (self, dialog, res):
        sys.exit (1)

# BTS

class Bug (object):
    def __init__ (self, raw):
        # Skip the '#'
        raw = raw[1:]
        bits = re.split(r'[: ]', raw, 2)
        self.id, self.tag, self.data = bits
        # Remove [ and ]
        self.tag = self.tag[1:-1]
        self.data = self.data.strip ()
        self.package = self.data.split(']', 1)[0][1:]

        self.reporter = self.get_data ("Reported by:")
        self.date = self.get_data ("Date:")
        self.severity = self.get_data("Severity:").capitalize ()
        self.version = self.get_data ("Found in version")
        self.filed_date = self.get_data ("Filed")
        self.modified_date = self.get_data ("Modified")

        # Get rid of [package] which has been stored in self.package
        self.info = self.data.split(']', 1)[1]
        self.info = self.info[:self.info.lower().index ("reported by:")].strip ()
        if not self.info:
            self.info = '(no subject)'   

    def get_data (self, token):
        info = ''
        try:
            index = self.data.lower().index (token.lower ())
        except:
            return '(unknown)'

        i = index + len(token)
        while True:
            c = self.data[i]
            if c == ';':
                break
            info += c
            i += 1
        return info.strip ()

    def __iter__ (self):
        yield self.id
        yield self.tag
        yield self.package
        yield self.info
        yield self.reporter
        yield self.date
        yield self.severity
        yield self.version
        yield self.filed_date
        yield self.modified_date

class BugReport (object):
    def __init__ (self, message):
        lines = message.split ('\n')
        i = 0

        self.headers = []
        while i < len (lines):
            line = lines[i]
            i += 1
            if not line.strip ():
                break
            self.headers.append (line)

        store = 0
        info = []
        while i < len (lines):
            line = lines[i]
            info.append (line)
            i += 1
            if store < 2 and not line.strip():
                store += 1
                continue
            if store == 2 and (line.startswith ('-- ') or line.startswith ('** ')):
                break
            store = 0
        self.original_info = '\n'.join (info[:-3])

        self.others = '\n'.join (lines[i-1:])

    def get_others (self):
        return self.others

    def get_original_info (self):
        return self.original_info

    def get_subject (self):
        for header in self.headers:
            if 'Subject' in header:
                return header[len ('Subject: '):]

    def set_subject (self, subject):
        for i in range (len (self.headers)):
            if 'Subject' in self.headers[i]:
                self.headers[i] = 'Subject: '+subject
                break

    def create_message (self, info):
        message = """%s

%s


%s""" % ('\n'.join (self.headers), info,self.others)
        return message

# BTS GUI

class BugPage (gtk.EventBox, threading.Thread):
    def __init__ (self, dialog, number, queryonly, bts, mirrors, http_proxy, archived):
        threading.Thread.__init__ (self)
        gtk.EventBox.__init__ (self)
        self.dialog = dialog
        self.assistant = self.dialog.assistant
        self.application = self.assistant.application
        self.number = number
        self.queryonly = queryonly
        self.bts = bts
        self.mirrors = mirrors
        self.http_proxy = http_proxy
        self.archived = archived

        vbox = gtk.VBox (spacing=12)
        vbox.pack_start (gtk.Label ("Retrieving bug information."), expand=False)

        self.progress = gtk.ProgressBar ()
        self.progress.set_pulse_step (0.01)
        vbox.pack_start (self.progress, expand=False)

        self.add (vbox)

    def run (self):
        # Start the progress bar
        gobject.timeout_add (10, self.pulse)

        info = debianbts.get_report (int (self.number), self.bts, mirrors=self.mirrors,
                                     http_proxy=self.http_proxy, archived=self.archived)
        if not info:
            self.application.run_once_in_main_thread (self.not_found)
        else:
            self.application.run_once_in_main_thread (self.found, info)

    def drop_progressbar (self):
        child = self.get_child ()
        self.remove (child)
        child.unparent ()

    def pulse (self):
        self.progress.pulse ()
        return self.isAlive ()

    def not_found (self):
        self.drop_progressbar ()
        self.add (gtk.Label ("The bug can't be fetched or it doesn't exist."))
        self.show_all ()
        
    def found (self, info):
        self.drop_progressbar ()
        desc = info[0].split(':', 1)[1].strip ()
        bodies = info[1]
        vbox = gtk.VBox (spacing=12)
        vbox.set_border_width (12)
        label = gtk.Label ('Description: '+desc)
        label.set_line_wrap (True)
        vbox.pack_start (label, expand=False)
        
        view = gtk.TreeView ()
        view.get_selection().set_mode (gtk.SELECTION_NONE)
        view.set_rules_hint (True)
        model = gtk.ListStore (str)
        view.set_model (model)
        view.append_column (gtk.TreeViewColumn ('Replies', gtk.CellRendererText (), text=0))
        for body in bodies:
            model.append ([body])
        scrolled = create_scrollable (view)
        vbox.pack_start (scrolled)

        bbox = gtk.HButtonBox ()
        button = gtk.Button ("Open in browser")
        button.connect ('clicked', self.on_open_browser)
        bbox.pack_start (button)
        if not self.queryonly:
            button = gtk.Button ("Reply")
            button.set_image (gtk.image_new_from_stock (gtk.STOCK_EDIT, gtk.ICON_SIZE_BUTTON))
            button.connect ('clicked', self.on_reply)
            bbox.pack_start (button)
        vbox.pack_start (bbox, expand=False)

        self.add (vbox)
        self.show_all ()
            
    def on_open_browser (self, button):
        launch_browser (debianbts.get_report_url (self.bts, int (self.number), self.archived))

    def on_reply (self, button):
        # Return the bug number to reportbug
        self.application.set_next_value (self.number)
        # Forward the assistant to the progress bar
        self.assistant.forward_page ()
        # Though we only a page, we are authorized to destroy our parent :)
        self.dialog.destroy ()

class BugsDialog (gtk.Dialog):
    def __init__ (self, assistant, queryonly):
        gtk.Dialog.__init__ (self, "Reportbug: bug information", assistant,
                             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.assistant = assistant
        self.queryonly = queryonly
        self.application = assistant.application
        self.notebook = gtk.Notebook ()
        self.vbox.pack_start (self.notebook)
        self.connect ('response', self.on_response)
        self.set_default_size (600, 600)

    def on_response (self, *args):
        self.destroy ()

    def show_bug (self, number, *args):
        page = BugPage (self, number, self.queryonly, *args)
        self.notebook.append_page (page, gtk.Label (number))
        page.start ()
        
# Application

class ReportbugApplication (threading.Thread):
    def __init__ (self):
        threading.Thread.__init__ (self)
        self.queue = Queue ()
        self.next_value = None
        
    def run (self):
        gtk.main ()

    def get_last_value (self):
        return self.queue.get ()

    def put_next_value (self):
        self.queue.put (self.next_value)
        self.next_value = None
    
    def set_next_value (self, value):
        self.next_value = value

    @staticmethod
    def create_idle_callback (func, *args, **kwargs):
        def callback ():
            func (*args, **kwargs)
            return False
        return callback

    def run_once_in_main_thread (self, func, *args, **kwargs):
        gobject.idle_add (self.create_idle_callback (func, *args, **kwargs))

# Connection with reportbug

# Syncronize "pipe" with reportbug

class SyncReturn (RuntimeError):
    def __init__ (self, result):
        RuntimeError.__init__ (self, result)
        self.result = result

class ReportbugConnector (object):
    # Executed in the glib thread
    def execute_operation (self, *args, **kwargs):
        pass

    # Executed in sync with reportbug. raise SyncResult (value) to directly return to reportbug
    # Returns args and kwargs to pass to execute_operation
    def sync_pre_operation (cls, *args, **kwargs):
        return args, kwargs
        
# Assistant

class Page (ReportbugConnector):
    next_page_num = 0
    page_type = gtk.ASSISTANT_PAGE_CONTENT
    default_complete = False
    side_image = DEBIAN_LOGO

    def __init__ (self, assistant):
        self.assistant = assistant
        self.application = assistant.application
        self.widget = self.create_widget ()
        self.widget.page = self
        self.widget.set_border_width (6)
        self.widget.show_all ()
        self.page_num = Page.next_page_num

    def execute_operation (self, *args, **kwargs):
        self.switch_in ()
        self.connect_signals ()
        self.empty_ok = kwargs.pop ('empty_ok', False)
        self.execute (*args, **kwargs)
        self.assistant.show ()

    def connect_signals (self):
        pass

    def set_page_complete (self, complete):
        self.assistant.set_page_complete (self.widget, complete)

    def set_page_type (self, type):
        self.assistant.set_page_type (self.widget, type)

    def set_page_title (self, title):
        if title:
            self.assistant.set_page_title (self.widget, title)

    # The user will see this as next page
    def switch_in (self):
        Page.next_page_num += 1
        self.assistant.insert_page (self.widget, self.page_num)
        self.set_page_complete (self.default_complete)
        self.set_page_type (self.page_type)
        self.assistant.set_page_side_image (self.widget, gdk.pixbuf_new_from_file (self.side_image))
        self.assistant.set_next_page (self)
        self.set_page_title ("Reportbug")

    # Setup keyboard focus in the page
    def setup_focus (self):
        self.widget.grab_focus ()

    # The user forwarded the assistant to see the next page
    def switch_out (self):
        pass

    def is_valid (self, value):
        if self.empty_ok:
            return True
        else:
            return bool (value)

    def validate (self, *args, **kwargs):
        value = self.get_value ()
        if self.is_valid (value):
            self.application.set_next_value (value)
            self.set_page_complete (True)
        else:
            self.set_page_complete (False)

class IntroPage (Page):
    page_type = gtk.ASSISTANT_PAGE_INTRO
    default_complete = True

    def create_widget (self):
        vbox = gtk.VBox (spacing=24)

        label = gtk.Label ("""
<b>Reportbug</b> is a tool designed to make the reporting of bugs in Debian and derived distributions relatively painless.

This wizard will guide you through the bug reporting process step by step.""")
        label.set_use_markup (True)
        label.set_line_wrap (True)
        label.set_justify (gtk.JUSTIFY_FILL)
        vbox.pack_start (label, expand=False)

        link = gtk.LinkButton ("http://alioth.debian.org/projects/reportbug",
                               "Homepage of reportbug project")
        vbox.pack_start (link, expand=False)
        return vbox

class GetStringPage (Page):
    def setup_focus (self):
        self.entry.grab_focus ()

    def create_widget (self):
        vbox = gtk.VBox (spacing=12)
        self.label = gtk.Label ()
        self.label.set_line_wrap (True)
        self.entry = gtk.Entry ()
        vbox.pack_start (self.label, expand=False)
        vbox.pack_start (self.entry, expand=False)
        return vbox

    def connect_signals (self):
        self.entry.connect ('changed', self.validate)

    def get_value (self):
        return self.entry.get_text ()

    def execute (self, prompt, options=None, force_prompt=False, default=''):
        if 'blank OK' in prompt:
            self.empty_ok = True
        else:
            self.empty_ok = False
        self.label.set_text (prompt)
        self.entry.set_text (default)

        if options:
            options.sort ()
            completion = gtk.EntryCompletion ()
            model = gtk.ListStore (str)
            for option in options:
                model.append ([option])
            completion.set_model (model)
            completion.set_inline_selection (True)
            completion.set_text_column (0)
            self.entry.set_completion (completion)
        else:
            self.completion = None

        self.validate ()

class GetMultilinePage (Page):
    def setup_focus (self):
        self.view.grab_focus ()

    def create_widget (self):
        vbox = gtk.VBox (spacing=12)
        self.label = gtk.Label ()
        vbox.pack_start (self.label, expand=False)

        self.view = gtk.TextView ()
        self.buffer = view.get_buffer ()
        scrolled = create_scrollable (self.view)
        vbox.pack_start (scrolled)
        return vbox

    def connect_signals (self):
        self.buffer.connect ('changed', self.validate)

    def get_value (self):
        text = self.buffer.get_text (self.buffer.get_start_iter (), self.buffer.get_end_iter ())
        lines = text.split ('\n')
        # Remove the trailing empty line at the end
        if len (lines) > 0 and not lines[-1].strip ():
            del lines[-1]
        return text.split ('\n')

    def execute (self, prompt):
        self.empty_ok = True
        # The result must be iterable for reportbug even if it's empty and not modified
        self.label.set_text (prompt)
        self.buffer.set_text ("")
        self.buffer.emit ('changed')

class TreePage (Page):
    value_column = None

    def __init__ (self, *args, **kwargs):
        Page.__init__ (self, *args, **kwargs)
        self.selection = self.view.get_selection()

    def setup_focus (self):
        self.view.grab_focus ()

    def connect_signals (self):
        self.selection.connect ('changed', self.validate)

    def get_value (self):
        model, paths = self.selection.get_selected_rows ()
        multiple = self.selection.get_mode () == gtk.SELECTION_MULTIPLE
        result = []
        for path in paths:
            value = model.get_value (model.get_iter (path), self.value_column)
            if value is not None:
                result.append (markup_free (value))
        if result and not multiple:
            return result[0]
        return result

class GetListPage (TreePage):
    value_column = 0

    def create_widget (self):
        vbox = gtk.VBox (spacing=12)
        self.label = gtk.Label ()
        vbox.pack_start (self.label, expand=False)

        hbox = gtk.HBox (spacing=6)

        self.view = gtk.TreeView ()
        self.view.set_rules_hint (True)
        self.view.get_selection().set_mode (gtk.SELECTION_MULTIPLE)
        scrolled = create_scrollable (self.view)
        hbox.pack_start (scrolled)

        bbox = gtk.VButtonBox ()
        bbox.set_spacing (6)
        bbox.set_layout (gtk.BUTTONBOX_START)
        button = gtk.Button (stock=gtk.STOCK_ADD)
        button.connect ('clicked', self.on_add)
        bbox.pack_start (button, expand=False)
        button = gtk.Button (stock=gtk.STOCK_REMOVE)
        button.connect ('clicked', self.on_remove)
        bbox.pack_start (button, expand=False)
        hbox.pack_start (bbox, expand=False)

        vbox.pack_start (hbox)
        return vbox

    def get_value (self):
        values = []
        for row in self.model:
            values.append (row[self.value_column])
        return values

    def on_add (self, button):
        dialog = InputStringDialog ("Add a new item to the list")
        dialog.show_all ()
        dialog.connect ('response', self.on_add_dialog_response)

    def on_add_dialog_response (self, dialog, res):
        if res == gtk.RESPONSE_ACCEPT:
            self.model.append ([dialog.get_value ()])
        dialog.destroy ()

    def on_remove (self, button):
        model, paths = self.selection.get_selected_rows ()
        # We need to transform them to iters, since paths change when removing rows
        iters = []
        for path in paths:
            iters.append (self.model.get_iter (path))
        for iter in iters:
            self.model.remove (iter)

    def execute (self, prompt):
        self.empty_ok = True

        self.label.set_text (prompt)

        self.model = gtk.ListStore (str)
        self.model.connect ('row-changed', self.validate)
        self.view.set_model (self.model)

        self.selection.set_mode (gtk.SELECTION_MULTIPLE)

        self.view.append_column (gtk.TreeViewColumn ('Item', gtk.CellRendererText (), text=0))

class MenuPage (TreePage):
    value_column = 0

    def create_widget (self):
        vbox = gtk.VBox (spacing=12)
        self.label = gtk.Label ()
        vbox.pack_start (self.label, expand=False)

        self.view = gtk.TreeView ()
        self.view.set_rules_hint (True)
        scrolled = create_scrollable (self.view)
        vbox.pack_start (scrolled)
        vbox.show_all ()
        return vbox

    def execute (self, par, options, prompt, default=None, any_ok=False,
                 order=None, extras=None, multiple=False):
        self.label.set_text (par)

        self.model = gtk.ListStore (str, str)
        self.view.set_model (self.model)

        if multiple:
            self.selection.set_mode (gtk.SELECTION_MULTIPLE)

        self.view.append_column (gtk.TreeViewColumn ('Option', gtk.CellRendererText (), markup=0))
        self.view.append_column (gtk.TreeViewColumn ('Description', gtk.CellRendererText (), text=1))

        default_iter = None
        if isinstance (options, dict):
            for option, desc in options.iteritems ():
                iter = self.model.append ((highlight (option), desc))
                if option == default:
                    default_iter = iter
        else:
            for row in options:
                iter = self.model.append ((highlight (row[0]), row[1]))
                if row[0] == default:
                    default_iter = iter

        if default_iter:
            self.selection.select_iter (default_iter)

class HandleBTSQueryPage (TreePage):
    default_complete = True
    value_column = 0

    def sync_pre_operation (self, package, bts, mirrors=None, http_proxy="", queryonly=False, screen=None,
                            archived='no', source=False, title=None, version=None):
        self.bts = bts
        self.mirrors = mirrors
        self.http_proxy = http_proxy
        self.archived = archived

        self.queryonly = queryonly
        if queryonly:
            self.page_type = gtk.ASSISTANT_PAGE_CONFIRM

        sysinfo = debianbts.SYSTEMS[bts]
        root = sysinfo.get('btsroot')
        if not root:
            # do we need to make a dialog for this?
            return

        if isinstance(package, basestring):
            pkgname = package
            if source:
                pkgname += ' (source)'

            progress_label = 'Querying %s bug tracking system for reports on %s' % (debianbts.SYSTEMS[bts]['name'], pkgname)
        else:
            progress_label = 'Querying %s bug tracking system for reports %s' % (debianbts.SYSTEMS[bts]['name'], ' '.join([str(x) for x in package]))


        self.application.run_once_in_main_thread (self.assistant.set_progress_label, progress_label)

        try:
            (count, sectitle, hierarchy) = debianbts.get_reports (
                package, bts, mirrors=mirrors, version=version,
                http_proxy=http_proxy, archived=archived, source=source)

            if not count:
                if hierarchy == None:
                    raise NoPackage
                else:
                    raise NoBugs
            else:
                if count > 1:
                    sectitle = '%d bug reports found' % (count,)
                else:
                    sectitle = 'One bug report found'

                report = []
                for category, bugs in hierarchy:
                    buglist = []
                    for bug in bugs:
                        buglist.append (Bug (bug))
                    report.append ((category, buglist))

                return (report, sectitle), {}

        except (IOError, NoNetwork):
            error_dialog ("Unable to connect to %s BTS." % sysinfo['name'])
        except NoPackage:
            error_dialog ('No record of this package found.')
            raise NoPackage

        raise SyncReturn (None)

    def setup_focus (self):
        self.entry.grab_focus ()

    def create_widget (self):
        vbox = gtk.VBox (spacing=6)
        self.label = gtk.Label ("List of bugs. Select a bug to retrieve and submit more information.")
        vbox.pack_start (self.label, expand=False, padding=6)

        hbox = gtk.HBox (spacing=6)
        label = gtk.Label ("Filter:")
        hbox.pack_start (label, expand=False)
        self.entry = gtk.Entry ()
        hbox.pack_start (self.entry)
        button = gtk.Button ()
        button.set_image (gtk.image_new_from_stock (gtk.STOCK_CLEAR, gtk.ICON_SIZE_BUTTON))
        button.connect ('clicked', self.on_filter_clear)
        hbox.pack_start (button, expand=False)
        vbox.pack_start (hbox, expand=False)

        self.view = gtk.TreeView ()
        self.view.set_rules_hint (True)
        scrolled = create_scrollable (self.view)
        self.columns = ['ID', 'Tag', 'Package', 'Description', 'Reporter', 'Date', 'Severity', 'Version',
                        'Filed date', 'Modified date']
        for col in zip (self.columns, range (len (self.columns))):
            self.view.append_column (gtk.TreeViewColumn (col[0], gtk.CellRendererText (), text=col[1]))
        vbox.pack_start (scrolled)

        button = gtk.Button ("Retrieve and submit bug information")
        button.set_image (gtk.image_new_from_stock (gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON))
        button.connect ('clicked', self.on_retrieve_info)
        vbox.pack_start (button, expand=False)
        return vbox

    def connect_signals (self):
        TreePage.connect_signals (self)
        self.view.connect ('row-activated', self.on_retrieve_info)
        self.entry.connect ('changed', self.on_filter_changed)

    def on_filter_clear (self, button):
        self.entry.set_text ("")

    def on_filter_changed (self, entry):
        self.model.filter_text = entry.get_text().lower ()
        self.filter.refilter ()

    def on_retrieve_info (self, *args):
        bug_ids = TreePage.get_value (self)
        if not bug_ids:
            info_dialog ("Please select one ore more bugs")
            return

        dialog = BugsDialog (self.assistant, self.queryonly)
        for id in bug_ids:
            dialog.show_bug (id, self.bts, self.mirrors, self.http_proxy, self.archived)
        dialog.show_all ()

    def is_valid (self, value):
        return True

    def get_value (self):
        # The value returned to reportbug doesn't depend by a selection, but by the dialog of a bug
        return None

    def match_filter (self, iter):
        # Flatten the columns into a single string
        text = ""
        for col in range (len (self.columns)):
            value = self.model.get_value (iter, col)
            if value:
                text += self.model.get_value (iter, col) + " "

        text = text.lower ()
        # Tokens shouldn't be adjacent by default
        for token in self.model.filter_text.split (' '):
            if token in text:
                return True
        return False

    def filter_visible_func (self, model, iter):
        matches = self.match_filter (iter)
        if not self.model.iter_parent (iter) and not matches:
            # If no children are visible, hide it
            it = model.iter_children (iter)
            while it:
                if self.match_filter (it):
                    return True
                it = model.iter_next (it)
            return False

        return matches

    def execute (self, buglist, sectitle):
        self.label.set_text ("%s. Double-click a bug to retrieve and submit more information." % sectitle)

        self.model = gtk.TreeStore (*([str] * len (self.columns)))
        for category in buglist:
            row = [None] * len (self.columns)
            row[3] = category[0]
            iter = self.model.append (None, row)
            for bug in category[1]:
                self.model.append (iter, list (bug))

        self.selection.set_mode (gtk.SELECTION_MULTIPLE)

        self.model.filter_text = ""
        self.filter = self.model.filter_new ()
        self.filter.set_visible_func (self.filter_visible_func)
        self.view.set_model (self.filter)

class DisplayReportPage (Page):
    default_complete = True

    def create_widget (self):
        self.view = gtk.TextView ()
        self.view.set_editable (False)
        scrolled = create_scrollable (self.view)
        return scrolled

    def execute (self, message, *args):
        self.view.get_buffer().set_text (message % args)

class LongMessagePage (Page):
    default_complete = True
    
    def create_widget (self):
        self.label = gtk.Label ()
        self.label.set_line_wrap (True)
        self.label.set_justify (gtk.JUSTIFY_FILL)
        eb = gtk.EventBox ()
        eb.add (self.label)
        return eb

    def execute (self, message, *args):
        message = message % args
        self.label.set_text (message)
        # Reportbug should use final_message, so emulate it
        if ('999999' in message):
            self.set_page_type (gtk.ASSISTANT_PAGE_CONFIRM)
            self.set_page_title ("Thanks for your report")

class FinalMessagePage (LongMessagePage):
    page_type = gtk.ASSISTANT_PAGE_CONFIRM
    default_complete = True

    def execute (self, *args, **kwargs):
        LongMessagePage.execute (self, *args, **kwargs)
        self.set_page_title ("Thanks for your report")

class EditorPage (Page):
    def create_widget (self):
        vbox = gtk.VBox (spacing=6)
        hbox = gtk.HBox (spacing=12)
        hbox.pack_start (gtk.Label ("Subject: "), expand=False)
        self.subject = gtk.Entry ()
        hbox.pack_start (self.subject)
        vbox.pack_start (hbox, expand=False)

        self.view = gtk.TextView ()
        self.info_buffer = self.view.get_buffer ()
        scrolled = create_scrollable (self.view)
        vbox.pack_start (scrolled)

        expander = gtk.Expander ("Other system information")
        view = gtk.TextView ()
        view.set_editable (False)
        self.others_buffer = view.get_buffer ()
        scrolled = create_scrollable (view)
        expander.add (scrolled)
        vbox.pack_start (expander)
        return vbox

    def switch_out (self):
        f = file (self.filename, "w")
        f.write (self.get_value()[0])
        f.close ()

    def connect_signals (self):
        self.info_buffer.connect ('changed', self.validate)
        self.subject.connect ('changed', self.validate)

    def get_value (self):
        info = self.info_buffer.get_text (self.info_buffer.get_start_iter (),
                                          self.info_buffer.get_end_iter ())
        if not info.strip ():
            return None
        subject = self.subject.get_text().strip ()
        if not subject.strip ():
            return None

        self.report.set_subject (subject)
        message = self.report.create_message (info)
        message = message.decode (self.charset, 'replace')
        return (message, message != self.message)

    def handle_first_info (self):
        self.focus_in_id = self.view.connect ('focus-in-event', self.on_view_focus_in_event)

    def on_view_focus_in_event (self, view, *args):
        # Empty the buffer only the first time
        self.info_buffer.set_text ("")
        view.disconnect (self.focus_in_id)

    def execute (self, message, filename, editor, charset='utf-8'):
        self.message = message
        self.report = BugReport (message)
        self.filename = filename
        self.charset = charset
        self.subject.set_text (self.report.get_subject ())
        self.others_buffer.set_text (self.report.get_others ())

        info = self.report.get_original_info ()
        if info.strip () == "*** Please type your report below this line ***":
            info = "Please type your report here..."
            self.handle_first_info ()
        self.info_buffer.set_text (info)

class SelectOptionsPage (Page):
    default_complete = False

    def create_widget (self):
        self.label = gtk.Label ()
        self.vbox = gtk.VBox (spacing=6)
        self.vbox.pack_start (self.label, expand=False, padding=6)
        self.default = None
        return self.vbox

    def on_clicked (self, button, menuopt):
        self.application.set_next_value (menuopt)
        self.assistant.forward_page ()

    def setup_focus (self):
        if self.default:
            self.default.set_flags (gtk.CAN_DEFAULT | gtk.HAS_DEFAULT)
            self.default.grab_default ()
            self.default.grab_focus ()

    def execute (self, prompt, menuopts, options):
        self.label.set_text (prompt)

        buttons = []
        for menuopt in menuopts:
            desc = options[menuopt.lower ()]
            # do we really need to launch an external editor?
            if 'Change editor' in desc:
                continue
            button = gtk.Button (options[menuopt.lower ()])
            button.connect ('clicked', self.on_clicked, menuopt.lower ())
            if menuopt.isupper ():
                self.default = button
                buttons.insert (0, gtk.HSeparator ())
                buttons.insert (0, button)
            else:
                buttons.append (button)

        for button in buttons:
            self.vbox.pack_start (button, expand=False)

        self.vbox.show_all ()

class ProgressPage (Page):
    page_type = gtk.ASSISTANT_PAGE_PROGRESS

    def pulse (self):
        self.progress.pulse ()
        return True

    def create_widget (self):
        vbox = gtk.VBox (spacing=6)
        self.label = gtk.Label ()
        self.label.set_line_wrap (True)
        self.progress = gtk.ProgressBar ()
        self.progress.set_pulse_step (0.01)
        vbox.pack_start (self.label, expand=False)
        vbox.pack_start (self.progress, expand=False)
        gobject.timeout_add (10, self.pulse)
        return vbox

    def set_label (self, text):
        self.label.set_text (text)

    def reset_label (self):
        self.set_label ("This operation may take a while")

class ReportbugAssistant (gtk.Assistant):
    def __init__ (self, application):
        gtk.Assistant.__init__ (self)
        self.set_title ('Reportbug')
        self.application = application
        self.showing_page = None
        self.requested_page = None
        self.progress_page = None
        self.set_default_size (600, 400)
        self.set_forward_page_func (self.forward)
        self.connect_signals ()
        self.setup_pages ()

    def connect_signals (self):
        self.connect ('cancel', self.close)
        self.connect ('prepare', self.on_prepare)
        self.connect ('delete-event', self.close)
        self.connect ('apply', self.close)
        
    def on_prepare (self, assistant, widget):
        # If the user goes back then forward, we must ensure the feedback value to reportbug must be sent
        # when the user clicks on "Forward" to the requested page by reportbug
        if self.showing_page and self.showing_page == self.requested_page and self.get_current_page () > self.showing_page.page_num:
            self.application.put_next_value ()
            # Reportbug doesn't support going back, so make widgets insensitive
            self.showing_page.widget.set_sensitive (False)
            self.showing_page.switch_out ()

        self.showing_page = widget.page
        # Some pages might have changed the label in the while
        if self.showing_page == self.progress_page:
            self.progress_page.reset_label ()

        self.showing_page.setup_focus ()

    def close (self, *args):
        sys.exit (0)
        
    def forward (self, page_num):
        return page_num + 1

    def forward_page (self):
        self.set_current_page (self.forward (self.showing_page.page_num))

    def set_next_page (self, page):
        self.requested_page = page
        # If we're in progress immediately show this guy
        if self.showing_page == self.progress_page:
            self.set_current_page (page.page_num)

    def set_progress_label (self, text, *args, **kwargs):
        self.progress_page.set_label (text % args)

    def setup_pages (self):
        # We insert pages between the intro and the progress, so that we give the user the feedback
        # that the applications is still running when he presses the "Forward" button
        self.showing_page = IntroPage (self)
        self.showing_page.switch_in ()
        self.progress_page = ProgressPage (self)
        self.progress_page.switch_in ()
        self.set_current_page (0)
        Page.next_page_num = 1


# Dialogs


class YesNoDialog (ReportbugConnector, gtk.MessageDialog):
    def __init__ (self, application):
        gtk.MessageDialog.__init__ (self, assistant, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
        self.application = application
        self.connect ('response', self.on_response)

    def on_response (self, dialog, res):
        self.application.set_next_value (res == gtk.RESPONSE_YES)
        self.application.put_next_value ()
        self.destroy ()

    def execute_operation (self, msg, yeshelp=None, nohelp=None, default=True, nowrap=False):
        self.set_markup (msg+"?")
        if default:
            self.set_default_response (gtk.RESPONSE_YES)
        else:
            self.set_default_response (gtk.RESPONSE_NO)
        self.show_all ()

class DisplayFailureDialog (ReportbugConnector, gtk.MessageDialog):
    def __init__ (self, application):
        gtk.MessageDialog.__init__ (self, assistant, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                    gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE)
        self.application = application
        self.connect ('response', self.on_response)

    def on_response (self, dialog, res):
        self.application.put_next_value ()
        self.destroy ()

    def execute_operation (self, msg):
        self.set_markup (msg)
        self.show_all ()
             
class GetFilenameDialog (ReportbugConnector, gtk.FileChooserDialog):
    def __init__ (self, application):
        gtk.FileChooserDialog.__init__ (self, '', assistant, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                                      gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.application = application
        self.connect ('response', self.on_response)

    def on_response (self, dialog, res):
        value = None
        if res == gtk.RESPONSE_OK:
            value = self.get_filename ()

        self.application.set_next_value (value)
        self.application.put_next_value ()
        self.destroy ()

    def execute_operation (self, title, force_prompt=False):
        self.set_title (ask_free (title))
        self.show_all ()
   
def log_message (*args, **kwargs):
    return assistant.set_progress_label (*args, **kwargs)

def select_multiple (*args, **kwargs):
    kwargs['multiple'] = True
    kwargs['empty_ok'] = True
    return menu (*args, **kwargs)

def get_multiline (prompt, *args, **kwargs):
    if 'ENTER' in prompt:
        # This is a list, let's handle it the best way
        return get_list (prompt, *args, **kwargs)
    else:
        return get_multiline (prompt, *args, **kwargs)

pages = { 'get_string': GetStringPage,
          'menu': MenuPage,
          'handle_bts_query': HandleBTSQueryPage,
          'long_message': LongMessagePage,
          'display_report': DisplayReportPage,
          'final_message': FinalMessagePage,
          'spawn_editor': EditorPage,
          'select_options': SelectOptionsPage,
          'get_list': GetListPage }
dialogs = { 'yes_no': YesNoDialog,
            'get_filename': GetFilenameDialog,
            'display_failure': DisplayFailureDialog, }

def create_forwarder (parent, klass):
    def func (*args, **kwargs):
        op = klass (parent)
        try:
            args, kwargs = op.sync_pre_operation (*args, **kwargs)
        except SyncReturn, e:
            return e.result
        application.run_once_in_main_thread (op.execute_operation, *args, **kwargs)
        return application.get_last_value ()
    return func
      
def forward_operations (parent, operations):
    for operation, klass in operations.iteritems ():
        globals()[operation] = create_forwarder (parent, klass)

def initialize ():
    global application, assistant
    # Exception hook
    oldhook = sys.excepthook
    sys.excepthook = ExceptionDialog.create_excepthook (oldhook)

    # GTK settings
    gtk.window_set_default_icon_from_file (DEBIAN_LOGO)
    gtk.link_button_set_uri_hook (lambda button, uri: launch_browser (uri))

    application = ReportbugApplication ()
    assistant = ReportbugAssistant (application)

    # Forwarders
    forward_operations (assistant, pages)
    forward_operations (application, dialogs)

    application.start ()

def test ():
    # Write some tests here
    print select_options ('test', 'A', {'a': 'A test'})
    print get_multiline ('ENTER', empty_ok=True)
    print get_string ("test")
    page = HandleBTSQueryPage (assistant)
    application.run_once_in_main_thread (page.execute_operation, [('test', (Bug ('#123 [test] [we] we we Reported by: test;' ), Bug ('#123 [test] [we] we we Reported by: test;')))], 'test')
    return application.get_last_value ()

if __name__ == '__main__':
    initialize ()
    test ()
