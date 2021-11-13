#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dnote (formerly Pygmynote) is a command-line tool for storing and managing heterogeneous bit of data like notes, tasks, links, file attachments, etc. It is written in Python and uses an SQLite database as its back end.

Thanks to Luis Cabrera Sauco for implementing SQLite and i18 support.
"""

__author__ = "Dmitri Popov [dmpop@linux.com]"
__copyright__ = "Copyleft 2011-2016 Dmitri Popov"
__license__ = "GPLv3"
__version__ = "0.11.05"
__URL__ = "http://www.github.com/dmpop/pygmynote"

import sys
import datetime
import os
import time
import calendar
import gettext
import sqlite3 as sqlite
import tempfile
import subprocess
import shutil
import codecs
import webbrowser

### Settings ###

NOTE_DIR = '/home/princdr/Documents/dnote/'
EDITOR = 'vim'
DB = NOTE_DIR + 'dnote.sqlite'
BACKUP = NOTE_DIR + 'dnotebackup/' # Note the trailing slash
EXPORT_FILE = NOTE_DIR + 'dnote.tsv'
HTML_FILE = NOTE_DIR + 'dnote.html'
HTML_FILE_TITLE = NOTE_DIR + 'dnote'

ENC = "UTF-8"
DOMAIN = "dnote"

# Terminal colors

class termcolor:
	GREEN = '\033[1;32m'
	BLUE = '\033[1;34m'
	gray = '\033[0;30m'
	YELLOW = '\033[1;33m'
	RED = '\033[1;31m'
	purple = '\033[0;35m'
	PURPLE = '\033[1;35m'
	MAGENTA = '\033[1;38;5;198m'
	END = '\033[1;m'

	def disable(self):
		self.GREEN = ''
		self.BLUE = ''
		self.gray = ''
		self.YELLOW = ''
		self.RED = ''
		self.END = ''
		self.purple = ''
		self.PURPLE = ''
		self.MAGENTA = ''

try:
	TRANSLATION = gettext.translation(DOMAIN, "./locale")
	_ = TRANSLATION.ugettext
except IOError:
	_ = gettext.gettext


if os.path.exists(DB):
	CREATE = False
else:
	CREATE = True

try:
	conn = sqlite.connect(DB)
	cursor = conn.cursor()
except:
	sys.exit(_("Connection to the SQLite database failed!"))

today = time.strftime("%Y-%m-%d")
sevendays = datetime.datetime.strftime(datetime.datetime.strptime(today, "%Y-%m-%d") + datetime.timedelta(days=7), "%Y-%m-%d")
command = ""
counter = 0

print (termcolor.gray + "dnote: commandline notes & tasks".ljust(36, "~").rjust(40, "~") + termcolor.END)

def smartquotes(selection):
	selection=selection.replace("'", "’")
	selection=selection.replace("\"", "”")
	return selection


if CREATE == True:
	CREATE_SQL = \
		"CREATE TABLE notes (\
		id INTEGER PRIMARY KEY UNIQUE NOT NULL,\
		note VARCHAR(1024),\
		file BLOB,\
		due DATE,\
		new DATE,\
                modify DATE,\
		type VARCHAR(3),\
		ext VARCHAR(3),\
		tags VARCHAR(256));"
	cursor.execute(CREATE_SQL)
	conn.commit()

# Functions
# Delete a record by its ID
def verbose_print(row, bold = False): # id, note, tags, due, new, modify
  print ((termcolor.PURPLE if bold else termcolor.purple) + str(row[3]).ljust(10, ".") + ' ' + termcolor.GREEN +str(row[0]).rjust(3, ' ') + ' ' + termcolor.END + str(row[1]).partition('\n')[0] + termcolor.gray + ' [' + str(row[2]) + ']' + ' (' + str(row[4]) + ')' + termcolor.purple + ' mod ' + str(datetime.datetime.strptime(row[5], "%Y-%m-%d").date() - datetime.date.today()).partition(",")[0] + termcolor.END)

def pin(record_id):
  cursor.execute("UPDATE notes SET type='3' WHERE id='"  +  record_id  + "'")
  conn.commit()
  print (termcolor.GREEN + _('\nRecord has been pinned.') +termcolor.END)

def unpin(record_id):
  cursor.execute("UPDATE notes SET type='1' WHERE id='"  +  record_id  + "'")
  conn.commit()
  print (termcolor.GREEN + _('\nRecord has been unpinned.') +termcolor.END)

def status (command = 'q'):
  status_pinned()
  status_duesoon()
  status_pastdue()
  status_recent()
  return command

def status_pinned ():
  print (termcolor.BLUE + "<pinned:p> records".ljust(36, "=").rjust(40, "=") + termcolor.END)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE type = '3' ORDER BY id ASC")
  for row in cursor:
    verbose_print(row)
  
def status_recent ():
  print (termcolor.BLUE + "<recent:r> records".ljust(36, "=").rjust(40, "=") + termcolor.END)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE modify = '" + today + "' ORDER BY id ASC")
  for row in cursor:
    verbose_print(row)

def status_duesoon ():
  print (termcolor.YELLOW + "<future:f> records due soon".ljust(36, "=").rjust(40, "=") + termcolor.END)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE due > '" + today + "' AND due < '" + sevendays + "' AND type <> '0' ORDER BY due DESC")
  for row in cursor:
    verbose_print(row)
 
def status_pastdue ():
  print (termcolor.MAGENTA + "<overdue:o> records".ljust(36, "=").rjust(40, "=") + termcolor.END)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE due = '" + today + "' AND type <> '0' ORDER BY id ASC")
  for row in cursor:
    verbose_print(row, bold = False)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE due < '" + today + "' AND due <> '' AND type <> '0' ORDER BY due DESC")
  for row in cursor:
    verbose_print(row, bold = True)

def status_tasks ():
  counter = 0
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE due <> '' AND tags NOT LIKE '%private%' AND type = '1' ORDER BY due ASC")
  print ('\n-----')
  now = datetime.datetime.now()
  calendar.prmonth(now.year, now.month)
  for row in cursor:
    verbose_print(row)
    counter = counter + 1
  print ('\n-----')
  print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
  counter = 0

def status_active ():
  print (termcolor.GREEN + _("""========== Active records ==========""") + termcolor.END)
  cursor.execute ("SELECT id, note, tags, due, new, modify FROM notes WHERE type <> '0' ORDER BY id ASC")
  for row in cursor:
    verbose_print(row)    

def view_record (record_id):
  cursor.execute ("SELECT id, due, note, tags, new FROM notes WHERE ID='" + record_id + "'")
  row = cursor.fetchone()  
  print (termcolor.GREEN + str(row[0]) + termcolor.YELLOW + ' [?]' + termcolor.END +str(row[1]) + termcolor.BLUE + ' <' + termcolor.gray + str(row[4]) + termcolor.BLUE + '> #' + termcolor.gray + str(row[3]) + '\n' + termcolor.END + str(row[2]) + termcolor.GREEN + '\n>==v==v==v==v==v==v==v==v==v==v==v==<' + termcolor.END)

def modify_record (record_id):
  record_type = input(_('Update note [0], tags [1], due date [2], or archive [3]: '))
  record_modify = time.strftime('%Y-%m-%d')
  if record_type == '0':
    cursor.execute ("SELECT id, note FROM notes WHERE id='" + record_id + "'")
    row = cursor.fetchone()
    f = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    n = f.name
    f.write(row[1])
    f.close()
    subprocess.call([EDITOR, n])
    with open(n) as f:
    	updated_note = smartquotes(f.read())
    sanitized_sql = smartquotes(updated_note)     
    cursor.execute("UPDATE notes SET note='"  +  sanitized_sql + "', " + "modify='" + record_modify + "' WHERE id='"  +  record_id  +  "'")
  elif record_type == '1':
    cursor.execute ("SELECT id, tags FROM notes WHERE id='" + record_id + "'")
    row = cursor.fetchone()
    f = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    n = f.name
    f.write(row[1])
    f.close()
    subprocess.call([EDITOR, n])
    with open(n) as f:
      updated_tags =smartquotes(f.read()) 
    sanitized_sql = smartquotes(updated_tags)
    cursor.execute("UPDATE notes SET tags='" + sanitized_sql + "', " + "modify='" + record_modify + "' WHERE id='"  +  record_id  +  "'")
  elif record_type == '2':
    cursor.execute ("SELECT id, due FROM notes WHERE id='" + record_id + "'")
    row = cursor.fetchone()
    print (str(row[1]))
    updated_due =smartquotes(input('New due date: ')) 
    cursor.execute("UPDATE notes SET due='" + updated_due + "', " + "modify='" + record_modify + "' WHERE id='"  +  record_id  +  "'")
  elif record_type == '3':
    cursor.execute("UPDATE notes SET type='0' WHERE id='"  +  record_id  + "'")
  else:
    print('Bad modify code')
  conn.commit()
  print (termcolor.GREEN + _('\nRecord has been modified.') +termcolor.END)

def delete_item (record_id, command = 'q'):               # define our function
  cursor.execute("DELETE FROM notes WHERE ID='" + record_id + "'")
  print (termcolor.GREEN + _('\nRecord has been deleted.') + termcolor.END)
  conn.commit()
  return command

def find_note (record_note):
  counter = 0
  cursor.execute("SELECT due, id, note, tags, new FROM notes WHERE note LIKE '%" +  str(record_note)  +  "%' OR tags LIKE '%" + str(record_note) + "%' ORDER BY id ASC")
  for row in cursor:
    print (termcolor.YELLOW + str(row[0]).ljust(11, ".") + termcolor.GREEN +str(row[1]).rjust(3, '.') + ' ' + termcolor.END + str(row[2]).partition('\n')[0] + termcolor.gray + ' [' + str(row[3]) + ']' + termcolor.END)
    counter = counter + 1
  print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter) + termcolor.BLUE + '   Search term: ' + termcolor.END + str(record_note))
  counter = 0

# preserve command line interface default
if len(sys.argv) == 1:
  status()
  command = '' # what to do if no args provided
elif sys.argv[1] == 's' or sys.argv[1] == 'status':
  command = 'q'
  status()
elif sys.argv[1] == 'ls':
  command = 'q'
  if sys.argv[1] == 'ls' and len(sys.argv) == 2:
    status_active()
  elif len(sys.argv) == 2:
    status()
  elif sys.argv[2] == 'recent' or sys.argv[2] == 'r': # added today 
    status_recent()    
  elif sys.argv[2] == 'overdue' or sys.argv[2] == 'o': # pastdue
    status_pastdue()    
  elif sys.argv[2] == 'future' or sys.argv[2] == 'f': # due soon
    status_duesoon()    
  elif sys.argv[2] == 'p' or sys.argv[2] == 'pinned': # pinned
    status_pinned()
  elif sys.argv[2] == 'tl' or sys.argv[2] == 'tasks':
    status_tasks()
  elif sys.argv[2] == 'a' or sys.argv[2] == 'active':
    status_active()
elif sys.argv[1] == 'v' or sys.argv[1] == 'view':
  command = 'q'
  view_record(sys.argv[2])
elif sys.argv[1] == 'p' and len(sys.argv) == 3:
  pin(sys.argv[2])
  command = 'q'
elif sys.argv[1] == 'u' and len(sys.argv) == 3:
  unpin(sys.argv[2])
  command = 'q'
elif sys.argv[1] == 'm' or sys.argv[1] == 'modify' and len(sys.argv) == 3:
  modify_record(sys.argv[2])
  command = 'q'

while command != "q":
	try:
		command = input('dnote>')
		if command == 'h':
			print (termcolor.GREEN + _("""
===================
Pygmynote commands:
===================

i	Insert a new record
l	Insert a new long record
f	Insert a new record with an attachment
@	Save an attachment
m	Modify a record
p	Pin a record
u	Unpin a record
n	Search records by note
t	Search records by tag
a	Show active records
ar	Show archived records
tl	Show tasks
at	Show records with attachments
sql	Run a user-defined SQL query
e	Export records as CSV file
g	Generate HTML page with records containing a certain tag
d	Delete a record by its ID
b	Backup the database
q	Quit""") + termcolor.END)
		elif command == "s" or command == "status":
			status()

		elif command == "i":

# Insert a new record

			record_note = smartquotes(input(_('Note: ')))
			record_tags = smartquotes(input(_('Tags: ')))
			record_due = input(_('Due date (yyyy-mm-dd). Press ENTER to skip: '))
			record_type = '1'
			sql_query = "INSERT INTO notes (note, due, tags, type) VALUES ('%s', '%s', '%s', '%s')" % (record_note, record_due, record_tags, record_type)
			cursor.execute(sql_query)
			conn.commit()
			cursor.execute("SELECT MAX(id) FROM notes")
			for row in cursor:
				max_id = str(row[0])
			print (termcolor.GREEN + _('\nRecord ') + max_id +_(' has been added.') + termcolor.END)
		elif command == 'l':

# Insert a new long record
# http://stackoverflow.com/questions/3076798/start-nano-as-a-subprocess-from-python-capture-input

			f = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
			n = f.name
			f.close()
			subprocess.call([EDITOR, n])
			with open(n) as f:
				record_note = smartquotes(f.read())
			record_tags = smartquotes(input('Tags: '))
			record_due = input(_('Due date (yyyy-mm-dd). Press Enter to skip: '))
			record_type = '1'
			sql_query = "INSERT INTO notes (note, due, tags, type) VALUES ('%s', '%s', '%s', '%s')" % (record_note, record_due, record_tags, record_type)
			cursor.execute(sql_query)
			conn.commit()
			cursor.execute("SELECT MAX(id) FROM notes")
			for row in cursor:
				max_id = str(row[0])
			print (termcolor.GREEN + _('\nRecord ') + max_id +_(' has been added.') + termcolor.END)
		elif command == 'f':

# Insert a new record with file

			record_note = smartquotes(input(_('Note: ')))
			record_tags = smartquotes(input(_('Tags: ')))
			rfile = smartquotes(input(_('Enter path to file (e.g., /home/user/foo.png): ')))
			record_type='1'
			f=open(rfile.rstrip(), 'rb')
			ablob = f.read()
			f.close()
			cursor.execute("INSERT INTO notes (note, tags, type, ext, file) VALUES('" + record_note + "', '" + record_tags + "', '" + record_type + "', '"  + rfile[-3:] + "', ?)", [sqlite.Binary(ablob)])
			conn.commit()
			cursor.execute("SELECT MAX(id) FROM notes")
			for row in cursor:
				max_id = str(row[0])
			print (termcolor.GREEN + _('\nRecord ') + max_id +_(' has been added.') + termcolor.END)
		elif command == '@':

# Save file

			record_id = input(_('Record id: '))
			output_file=input(_('Specify full path and file name (e.g., /home/user/foo.png): '))
			f=open(output_file, 'wb')
			cursor.execute ("SELECT file FROM notes WHERE id='"  +  record_id  +  "'")
			ablob = cursor.fetchone()
			f.write(ablob[0])
			f.close()
			cursor.close()
			conn.commit()
			print (termcolor.GREEN + _('\nFile has been saved.') +termcolor.END)
		elif command == 'n':

# Search records by note

			record_note = input(_('Search notes for: '))
			cursor.execute("SELECT id, note, tags FROM notes WHERE note LIKE '%"
							 +  record_note  +  "%'ORDER BY id ASC")
			print ("\n-----")
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END + str(row[1]) + termcolor.gray + ' [' + str(row[2]) + ']' + termcolor.END)
				counter = counter + 1
			print ("\n-----")
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 't':

# Search records by tag

			search_tag = input (_('Search by tag: '))
			cursor.execute("SELECT id, note, tags FROM notes WHERE tags LIKE '%" + search_tag + "%' AND type='1' ORDER BY id ASC")
			print ('\n-----')
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END + str(row[1]) + termcolor.gray + ' [' + str(row[2]) + ']' + termcolor.END)
				counter = counter + 1
			print ('\n-----')
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 'a':

# Show active records

			cursor.execute("SELECT id, note, tags FROM notes WHERE type='1' ORDER BY id ASC")
			print ("\n-----")
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END + str(row[1]) + termcolor.gray + ' [' + str(row[2]) + ']' + termcolor.END)
				counter = counter + 1
			print ('\n-----')
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 'ar':

# Show archived records

			cursor.execute("SELECT id, note, tags FROM notes WHERE type='0' ORDER BY id ASC")
			print ('\n-----')
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END + str(row[1]) + termcolor.gray + ' [' + str(row[2]) + ']' + termcolor.END)
				counter = counter + 1
			print ('\n-----')
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 'sql':

# Run a user-defined SQL query

			sql_query = input ('SELECT id, note, due, tags FROM notes ')
			cursor.execute("SELECT id, note, due, tags FROM notes " + sql_query)
			print ('\n-----')
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END  + str(row[1]) + termcolor.gray + str(row[2])+ ' [' + str(row[3]) + ']' + termcolor.END)
				counter = counter + 1
			print ('\n-----')
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 'm':
# Modify a record
			record_id = input(_('Record id: '))
			modify_record(record_id)
		elif command == 'p':
# Pin a record
			record_id = input(_('Record id: '))
			pin(record_id)			
		elif command == 'u':

# Unpin a record
			record_id = input(_('Record id: '))
			unpin(record_id)
		elif command == 'tl':

# Show tasks

			status_tasks()
		elif command == 'at':

# Show records with attachments

			cursor.execute("SELECT id, note, tags, ext FROM notes WHERE ext <> 'None' AND type='1' ORDER BY id ASC")
			print ('\n-----')
			for row in cursor:
				print (termcolor.GREEN + '\n' +str(row[0]) + ' ' + termcolor.END + str(row[1]) + termcolor.gray + ' [' + str(row[2]) + '] ' + termcolor.END + termcolor.HIGHLIGHT + str(row[3]) + termcolor.END)
				counter = counter + 1
			print ('\n-----')
			print (termcolor.BLUE + _('Record count: ') + termcolor.END + str(counter))
			counter = 0
		elif command == 'd':
# Delete a record by its ID
			record_id = input('Delete note ID: ')
			delete_item(record_id = record_id, command = 'status')
		elif command == 'b':

# Backup the database

			if not os.path.exists(BACKUP):
				os.makedirs(BACKUP)
			shutil.copy('dnote.sqlite', BACKUP)
			os.rename(BACKUP + 'dnote.sqlite', BACKUP + today + '-dnote.sqlite')
			print (termcolor.GREEN + _('\nBackup copy of the database has been been saved in ') + BACKUP + termcolor.END)
		elif command == 'e':

# Export records

			cursor.execute("SELECT id, note, tags, due FROM notes ORDER BY id ASC")
			if os.path.exists(EXPORT_FILE):
				os.remove(EXPORT_FILE)
			for row in cursor:
				f = EXPORT_FILE
				file = codecs.open(f, 'a', encoding=ENC)
				file.write('%s\t%s\t[%s]\t%s\n' % (row[0], row[1], row[2], row[3]))
				file.close()
			print (termcolor.GREEN + _('\nRecords have been saved in the ') + EXPORT_FILE + _(' file.') + termcolor.END)
		elif command == 'g':

# Generate an HTML file

			search_tag = smartquotes(input(_('Tag: ')))
			cursor.execute("SELECT note, tags FROM notes WHERE tags LIKE '%" + search_tag + "%' AND type='1' ORDER BY id ASC")
			if os.path.exists(HTML_FILE):
				os.remove(HTML_FILE)
			f = HTML_FILE
			file = codecs.open(f, 'a', encoding=ENC)
			file.write('<html>\n\t<head>\n\t<meta http-equiv="content-type" content="text/html; charset=UTF-8" />\n\t<link href="style.css" rel="stylesheet" type="text/css" media="all" />\n\t<link href="http://fonts.googleapis.com/css?family=Open+Sans:400,300,300italic,400italic,600,600italic,700,700italic,800,800italic" rel="stylesheet" type="text/css">\n\t<title>'+ HTML_FILE_TITLE + '</title>\n\t</head>\n\t<body>\n\n\t<div id="content">\n\t<p class="content"></p>\n\t<h1>Pygmynote</h1>\n\n\t<table border=0>\n')
			for row in cursor:
				file.write('\t<tr><td><p>%s</p></td></tr>\n\t<tr><td><p><small>Tags:<em> %s </small></em></p></td></tr>' % (row[0], row[1]))
			file.write('\n\t</table>\n\n\t<hr>\n\t<center><div class="footer">Generated by <a href="https://github.com/dmpop/pygmynote">Pygmynote</a></div></center>\n\n\t</body>\n</html>')
			file.close()
			print ('\n')
			print (termcolor.GREEN + HTML_FILE + _(' file has been generated.') + termcolor.END)
			webbrowser.open(HTML_FILE)

	except:
		print (_('\n\nError: ') + termcolor.RED + str(sys.exc_info()[0]) + termcolor.END + _(' Please try again.'))

		continue

print (termcolor.gray + "exiting dnote console".ljust(36, "~").rjust(40, "~") + termcolor.END)

cursor.close()
conn.close()
