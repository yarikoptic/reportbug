# urwid user interface for reportbug
#   Written by Chris Lawrence <lawrencc@debian.org>
#   (C) 2001-06 Chris Lawrence
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
# $Id: reportbug_ui_urwid.py,v 1.1 2006-08-13 17:24:46 lawrencc Exp $

import commands, string, sys, re

import urwid.raw_display
import urwid

from reportbug_exceptions import *
from urlutils import launch_browser
from types import StringTypes

ISATTY = sys.stdin.isatty()

def ewrite(message, *args):
    # ewrite shouldn't do anything on newt... maybe should log to a file
    # if specified.
    if 1:
        return
    
    if not ISATTY:
        return

    if args:
        sys.stderr.write(message % args)
    else:
        sys.stderr.write(message)

log_message = ewrite
display_failure = ewrite

class buttonpush(Exception):
    pass

class dialog(object):
    def __init__(self, message, body=None, width=None, height=None):
        self.body = body
        self.ui = iface
        if not body:
            self.body = body = urwid.Filler(urwid.Divider(), 'top')

        if not width:
            width = ('relative', 80)

        if not height:
            height = ('relative', 40)


        self.frame = urwid.Frame(body, focus_part='footer')
        if message:
            self.frame.header = urwid.Pile([urwid.Text(message),
                                            urwid.Divider()])
        w = self.frame
        # pad area around listbox
        w = urwid.Padding(w, ('fixed left',2), ('fixed right',2))
        w = urwid.Filler(w, ('fixed top',1), ('fixed bottom',1))
        w = urwid.AttrWrap(w, 'body')
        # "shadow" effect
        w = urwid.Columns( [w,('fixed', 2, urwid.AttrWrap( urwid.Filler(urwid.Text(('border',' ')), "top") ,'shadow'))])
        w = urwid.Frame( w, footer = urwid.AttrWrap(urwid.Text(('border',' ')),'shadow'))
        # outermost border area
        w = urwid.Padding(w, 'center', width )
        w = urwid.Filler(w, 'middle', height )
        w = urwid.AttrWrap( w, 'border' )
        self.view = w

    def add_buttons(self, buttons, default=0):
        l = []
        for name, exitcode in buttons:
            b = urwid.Button( name, self.button_press )
            b.exitcode = exitcode
            b = urwid.AttrWrap( b, 'selectable','focus' )
            l.append( b )
        self.buttons = urwid.GridFlow(l, 10, 3, 1, 'center')
        self.buttons.set_focus(default or 0)
        self.frame.footer = urwid.Pile( [ urwid.Divider(), self.buttons ],
                                        focus_item = 1 )

    def button_press(self, button):
        raise buttonpush, button.exitcode

    def run(self):
        self.ui.set_mouse_tracking()
        size = self.ui.get_cols_rows()
        try:
            while True:
                canvas = self.view.render( size, focus=True )
                self.ui.draw_screen( size, canvas )
                keys = None
                while not keys: 
                    keys = self.ui.get_input()
                for k in keys:
                    if urwid.is_mouse_event(k):
                        event, button, col, row = k
                        self.view.mouse_event( size, 
                                               event, button, col, row,
                                               focus=True)
                    if k == 'window resize':
                        size = self.ui.get_cols_rows()
                    k = self.view.keypress( size, k )
                    if k:
                        self.unhandled_key( size, k)
        except buttonpush, e:
            return self.on_exit( e.args[0] )

    def on_exit(self, exitcode):
        return exitcode
    
    def unhandled_key(self, size, key):
        pass

class textentry(dialog):
    def __init__(self, text, width=None, height=None, multiline=False):
        self.edit = urwid.Edit(multiline=multiline)
        body = urwid.ListBox([self.edit])
        body = urwid.AttrWrap(body, 'selectable','focustext')
        dialog.__init__(self, text, body, width, height)

        self.frame.set_focus('body')

    def unhandled_key(self, size, k):
        if k in ('up','page up'):
            self.frame.set_focus('body')
        if k in ('down','page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            self.view.keypress( size, k )

    def on_exit(self, exitcode):
        return exitcode, self.edit.get_edit_text()

class blank_screen(dialog):
    def __init__(self):
        self.ui = iface
        self.ui.set_mouse_tracking()
        size = self.ui.get_cols_rows()
        self.view = urwid.Filler(urwid.Divider(), 'top')
        self.view = urwid.AttrWrap(self.view, 'border')
        canvas = self.view.render(size)
        self.ui.draw_screen(size, canvas)

def long_message(message, *args):
    if args:
        message = message % tuple(args)

    box = dialog(message)
    box.add_buttons([ ("OK", 0) ])
    box.run()
    blank_screen()

final_message = long_message

def select_options(msg, ok, help=None, allow_numbers=False, nowrap=False):
    box = dialog(msg)
    if not help:
        help = {}

    buttons = []
    default = None
    for i, option in enumerate(ok):
        if option.isupper():
            default = i
            option = option.lower()
        buttons.append( (help.get(option, option), option) )

    box.add_buttons(buttons, default)
    result = box.run()
    blank_screen()
    return result

def yes_no(msg, yeshelp, nohelp, default=True, nowrap=False):
    box = dialog(msg)
    box.add_buttons([ ('Yes', True), ('No', False) ], default=1-int(default))
    result = box.run()
    blank_screen()
    return result

def get_string(prompt, options=None, title=None, force_prompt=0):
    box = textentry(prompt)
    box.add_buttons([ ("OK", 0) ])
    code, text = box.run()
    blank_screen()
    return text

def get_multiline(prompt, options=None, title=None, force_prompt=0):
    box = textentry(prompt, multiline=True)
    box.add_buttons([ ("OK", 0) ])
    code, text = box.run()
    blank_screen()
    l = text.split('\n')
    return l

def menu(par, options, prompt, default=None, title=None, any_ok=0, order=None):
    return None

# Things that are very UI dependent go here
def show_report(number, system, mirrors, http_proxy, screen=None, queryonly=0,
                title='', archived='no'):
    import debianbts

    s = screen
    if not s:
        s = newt_screen()

    sysinfo = debianbts.SYSTEMS[system]
    newt_infobox('Retrieving report #%d from %s bug tracking system...' % (
        number, sysinfo['name']), title=title, screen=s)

    width = columns-8
    info = debianbts.get_report(number, system, mirrors=mirrors,
                                http_proxy=http_proxy, archived=archived)
    if not info:
        s.popWindow()
        newt_msgbox('Bug report #%d not found.' % number,
                    screen=s, title=title)
        if not screen:
            s.finish()
        return

    buttons = ['Ok', 'More details (launch browser)', 'Quit']
    if not queryonly:
        buttons.append('Submit more information')
        
    s.popWindow()
    while 1:
        (bugtitle, bodies) = info
        body = bodies[0]

        lines = string.split(body, '\n')
        lines = map(lambda x, y=width: x[:y], lines)
        body = string.join(lines, '\n')

        r = newt_dialog(text=body, title=bugtitle, screen=s, width=width,
                        buttons=buttons)
        if not r or (r == 'ok'):
            break
        elif r == 'quit':
            if not screen:
                s.finish()
            return -1
        elif r == 'submit more information':
            if not screen:
                s.finish()
            return number

        s.suspend()
        # print chr(27)+'c'
        # os.system('stty sane; clear')
        launch_browser(debianbts.get_report_url(system, number, archived))
        s.resume()
        
    if not screen:
        s.finish()
    return

def handle_bts_query(package, bts, mirrors=None, http_proxy="",
                     queryonly=0, screen=None, title="", archived='no',
                     source=0):
    import debianbts

    sysinfo = debianbts.SYSTEMS[bts]
    root = sysinfo.get('btsroot')
    if not root:
        ewrite("%s bug tracking system has no web URL; bypassing query.\n",
               sysinfo['name'])
        return

    scr = screen
    if not scr:
        scr = newt_screen()
    
    if isinstance(package, StringTypes):
        if source:
            newt_infobox('Querying %s bug tracking system for reports on'
                         ' src:%s\n' % (debianbts.SYSTEMS[bts]['name'],
                                        package),
                         screen=scr, title=title)
        else:
            newt_infobox('Querying %s bug tracking system for reports on %s\n'%
                         (debianbts.SYSTEMS[bts]['name'], package),
                         screen=scr, title=title)
    else:
        newt_infobox('Querying %s bug tracking system for reports %s\n' %
                     (debianbts.SYSTEMS[bts]['name'], ' '.join([str(x) for x in
                                                                package])),
                     screen=scr, title=title)

    result = None
    try:
        (count, sectitle, hierarchy) = debianbts.get_reports(
            package, bts, mirrors=mirrors,
            http_proxy=http_proxy, archived=archived, source=source)

        if not count:
            scr.popWindow()
            if hierarchy == None:
                raise NoPackage
            else:
                raise NoBugs
        else:
            if count > 1:
                sectitle = '%d bug reports found' % (count)
            else:
                sectitle = '%d bug report found' % (count)

            list = []
            for (t, bugs) in hierarchy:
                bcount = len(bugs)
                list.append( ('', t) )
                for bug in bugs:
                    bits = string.split(bug[1:], ':', 1)
                    tag, info = bits
                    info = string.strip(info)
                    if not info:
                        info = '(no subject)'
                    list.append( (tag, info) )

            p = 1
            scr.popWindow()
            while True:
                info = newt_menu('Select a bug to read the report:', rows-6,
                                 columns-10, rows-15, list, sectitle,
                                 startpos=p, screen=scr)
                if not info:
                    break
                else:
                    p = i = 0
                    for (number, subject) in list:
                        if number == info: p = i
			i += 1

                    res = show_report(int(info), bts, mirrors,
                                      http_proxy, screen=scr,
                                      queryonly=queryonly, title=title)
                    if res:
                        result = res
                        break

    except (IOError, NoNetwork):
        scr.popWindow()
        newt_msgbox('Unable to connect to %s BTS.' % sysinfo['name'],
                    screen=scr, title=title)
    except NoPackage:
        #scr.popWindow()
        newt_msgbox('No record of this package found.',
                    screen=scr, title=title)

    if not screen:
        scr.finish()
    return result

palette = [
    ('body','black','light gray', 'standout'),
    ('border','black','dark blue'),
    ('shadow','white','black'),
    ('selectable','black', 'dark cyan'),
    ('focus','white','dark blue','bold'),
    ('focustext','light gray','dark blue'),
    ]

# The interface must be run within a wrapper for urwid
def run_interface(function):
    global iface
    
    iface = urwid.raw_display.Screen()
    iface.register_palette(palette)
    return iface.run_wrapper(function)

def test():
    import time

    fp = file('/tmp/blah', 'w')
    
##     long_message('This is a test.  This is only a test.\nPlease do not adjust your set.')
##     time.sleep(1)
##     output = get_string('Tell me your name, biatch.')
##     print >> fp, output
##     output = get_multiline('List all of your aliases now.')
##     print >> fp, output
    result = select_options('This is really lame', 'ynM', {
        'y' : 'You bet', 'n' : 'Never!', 'm' : 'Maybe'})
    print >> fp, result
    yn = yes_no('Do you like green eggs and ham?', 'Yes sireee', 'No way!')
    print >> fp, yn

if __name__ == '__main__':
    run_interface(test)
