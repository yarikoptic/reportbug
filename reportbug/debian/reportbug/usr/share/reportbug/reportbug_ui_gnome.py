# GNOME user interface for reportbug
#   Written by Robin Putters <rputters@hotpop.com>
#   (C) 2002 Robin Putters, Chris Lawrence
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

import sys
sys.path.append('/usr/lib/python2.1/site-packages')

from reportbug_exceptions import *
import reportbug, gnome
gnome.app_id = "reportbug"
gnome.app_version = "2.42"

from gtk import *
from gnome.ui import *
from GdkImlib import *

def callback_destroy(bla):
	sys.exit(1)

def callback_next(bla, blabla):
	mainquit()

def callback_option_menu_activate(item, self, num):
	self.my_current = num
	self.my_linked_label.set_text(self.my_descriptions[num])

class ReportBugApp(GnomeApp):
	def __init__(self):
		GnomeApp.__init__(self, "Debian Bug Report Druid", "Debian Bug Report Druid")
		self.connect("destroy", callback_destroy)
		self.setup()

	def setup(self):
##		logo = Image("/usr/share/pixmaps/debian-logo.xpm")
		logo = None
		logo_bgcolor = GdkColor(0x02, 0x66, 0x9A)

		self.my_druid = GnomeDruid()
		self.my_screen = GnomeDruidPageStandard("Debian Bug Report Druid", logo)
		self.my_screen.connect("next", callback_next)
		self.my_screen.set_bg_color(logo_bgcolor)
		self.my_screen.set_logo_bg_color(logo_bgcolor)
		self.my_druid.append_page(self.my_screen)
		vbox = self.my_screen.vbox
		vbox.set_border_width(50)
	
	def do_it(self):
		self.set_contents(self.my_druid)
		self.show_all()
		mainloop()
		self.setup()
		
	def add_long_message(self, text):
		vbox = self.my_screen.vbox
		msg = GtkLabel(text)
		msg.set_line_wrap(TRUE)
		vbox.add(msg)

	def do_get_string(self, prompt):
		vbox = self.my_screen.vbox
		msg = GtkLabel(prompt)
		msg.set_line_wrap(TRUE)
		vbox.add(msg)
	
		entry = GtkEntry()
		vbox.add(entry)

		self.do_it()
		return entry.get_text()

	def do_menu(self, par, options, prompt, default):
		vbox = self.my_screen.vbox
		msg = GtkLabel(par)
		msg.set_line_wrap(TRUE)
		vbox.add(msg)

		optionmenu = GtkOptionMenu()
		menu = GtkMenu()
		menu.my_linked_label = GtkLabel()
		menu.my_linked_label.set_line_wrap(TRUE)
		i = 0
		menu.my_current = 0
		menu.my_options = []
		menu.my_descriptions = []

		for name, desc in options:
			item = GtkMenuItem(name)
			menu.append(item)
			item.connect("activate", callback_option_menu_activate, menu, i)
			menu.my_options = menu.my_options + [name]
			menu.my_descriptions = menu.my_descriptions + [desc]
			if default == name:
				menu.my_current = i
			i = i +1

		menu.set_active(menu.my_current)
		# Quick hack (display help on menu item)
		callback_option_menu_activate(None, menu, menu.my_current)
		
		optionmenu.set_menu(menu)
		vbox.add(optionmenu)
		vbox.add(menu.my_linked_label)
		self.do_it()
		return menu.my_options[menu.my_current]

	def do_any_ok_menu(self, par, options, prompt, default):
		vbox = self.my_screen.vbox
		msg = GtkLabel(par)
		msg.set_line_wrap(TRUE)
		vbox.add(msg)

		combo = GtkCombo()
		i = 0
		list = []
		for name, desc in options:
			list = list + [name + " - " + desc]

		combo.set_popdown_strings(list)
		vbox.add(combo)

		self.do_it()
		return combo.entry.get_text().split()[0]

	def yes_no_dialog(self, question, yes_help, no_help, default):
		gd = GnomeDialog("", b1=STOCK_BUTTON_YES, b2=STOCK_BUTTON_NO)
		gd.set_default(default==0)
		gd.set_parent(app)
		vbox = gd.vbox
		label = GtkLabel()
		label.set_line_wrap(TRUE)
		label.set_text(question)
		vbox.add(label)
		gd.show_all()
		return gd.run_and_close()

	def yes_no_dialog(self, question, yes_help, no_help, default):
		gd = GnomeDialog("", b1=STOCK_BUTTON_YES, b2=STOCK_BUTTON_NO)
		gd.set_default(default==0)
		gd.set_parent(app)
		vbox = gd.vbox
		label = GtkLabel()
		label.set_line_wrap(TRUE)
		label.set_text(question)
		vbox.add(label)
		gd.show_all()
		return gd.run_and_close()

	def select_options(self, msg, ok, help, allow_numbers=None):
		# Ugly fast code :)
		button = []
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		
		button = button + [None]		

		i = 1
		for ch in ok:
			button[i] = ch
			i = i + 1

		gd = GnomeDialog("", b1=button[0], b2=button[1], b3=button[2], b4=button[3], b5=button[4], b6=button[5], b7=button[6], b8=button[7])
		gd.set_default(0)
		gd.set_parent(app)
		vbox = gd.vbox
		label = GtkLabel()
		label.set_line_wrap(TRUE)
		label.set_text(msg)
		vbox.add(label)
		gd.show_all()
		return ok[gd.run_and_close()]

		

def long_message(text, *args):
	return app.add_long_message(text % args)
	
def menu(par, options, prompt, default=None, title=None, any_ok=0, order=None, extras=''):

	if type(options) == type({}):
		options = options.copy()
		# Convert to a list
		if order:
			list = []
			for key in order:
				if options.has_key(key):
					list.append( (key, options[key]) )
					del options[key]

			# Append anything out of order
			options = options.items()
			options.sort()
			for option in options:
				list.append( option )
			options = list
		else:
			options = options.items()
			options.sort()
	
	if any_ok:
		return app.do_any_ok_menu(par, options, prompt, default)
	else:
		return app.do_menu(par, options, prompt, default)

def get_string(prompt, options=None, title=None, force_prompt=0):
	return app.do_get_string(prompt)
    
def log_message(message, *args):
	sys.stderr.write(message % args)

def yes_no(question, yes_help, no_help, default):
	return app.yes_no_dialog(question, yes_help, no_help, default) == 0

def select_options(msg, ok, help, allow_numbers=None):
	return app.select_options(msg, ok, help, allow_numbers)

def handle_bts_query(*args, **kw):
        raise NotImplemented

app = ReportBugApp()
