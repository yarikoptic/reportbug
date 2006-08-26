# Newt user interface for reportbug
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
# $Id: reportbug_ui_newt.py,v 1.5.2.3 2006-08-26 01:57:09 lawrencc Exp $

import commands, string, sys, re, debianbts
from reportbug_exceptions import *
from urlutils import launch_browser

try:
    import snack
except ImportError:
    raise UINotImportable, 'Please install the python-newt package to use this interface.'

ISATTY = sys.stdin.isatty()

try:
    r, c = string.split(commands.getoutput('stty size'))
    rows, columns = int(r) or 24, int(c) or 79
except:
    rows, columns = 24, 79

def ewrite(message, *args):
    # ewrite shouldn't do anything on newt... maybe should log to a file
    # if specified.
    pass

log_message = ewrite
display_failure = ewrite

# Utility functions for common newt dialogs
def newt_screen():
    "Start a newt windowing session."
    return snack.SnackScreen()

def newt_infobox(text, height=6, width=50, title="", screen=None):
    "Display a message and go on."
    if not screen:
        s = snack.SnackScreen()
    else:
        s = screen
        
    t = snack.TextboxReflowed(width, text, maxHeight = s.height - 12)
    g = snack.GridForm(s, title[:width], 1, 2)
    g.add(t, 0, 0, padding = (0, 0, 0, 1))
    g.draw()
    s.refresh()
    if not screen:
        s.finish()

def newt_dialog(text, buttons=('Ok', 'Cancel'), width=50,
                title="", screen=None):
    "Display a message and wait for a response from the user."
    if not screen:
        s = snack.SnackScreen()
    else:
        s = screen

    selected = snack.ButtonChoiceWindow(s, title[:width], text, buttons,
                                        width=width)

    if not screen:
        s.finish()
    return selected

def newt_msgbox(text, width=50, title="", screen=None):
    "Display a message and wait for an OK from the user."
    return newt_dialog(text, ['Ok'], width, title, screen)

def long_message(message, *args):
    if args:
        message = message % tuple(args)
    newt_msgbox(message)

final_message = long_message

def newt_menu(text, height=20, width=60, menuheight=15, menu=None,
         title="", scroll=0, screen=None, startpos=1):
    "Display a menu of choices for the user."
    if not menu: return None
    if not screen:
        s = snack.SnackScreen()
    else:
        s = screen
    items = []
    for item in menu:
        if item[0]:
            items.append(('%6s: %s' % item)[:width])
        else:
            items.append(item[1])

    if len(items) > menuheight: scroll=1
    res = startpos
    while 1:
        button, res = snack.ListboxChoiceWindow(s, title[:width], text, items,
                                                width=width, height=menuheight,
                                                scroll=scroll, default=res,
                                                buttons=('View', 'Quit'))
        if button == 'quit':
            if not screen:
                s.finish()
            return None
        elif menu[res][0]:
            selected = menu[res][0]
            break

    if not screen:
        s.finish()
    return selected

# XXX - From here on out needs to be rewritten for newt
def select_options(msg, ok, help=None, allow_numbers=0):
    return None

def get_string(prompt, options=None, title=None, force_prompt=0):
    return None

def get_multiline(prompt, options=None, title=None, force_prompt=0):
    return None

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
    
    if isinstance(package, basestring):
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
