#!/usr/bin/python
#
# reportbug_submit module - email and GnuPG functions
#   Written by Chris Lawrence <lawrencc@debian.org>
#   Copyright (C) 1999-2006 Chris Lawrence
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
#
# $Id: reportbug_submit.py,v 1.20.2.6 2007-04-19 21:21:31 lawrencc Exp $

import sys

import reportbug
from reportbug import VERSION, VERSION_NUMBER

import os
sys.path = ['/usr/share/reportbug'] + sys.path

import re
import commands
import rfc822
import smtplib
import socket
import debianbts
import time

from rbtempfile import TempFile, open_write_safe, tempfile_prefix

from reportbug_exceptions import *

import email
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEAudio import MIMEAudio
from email.MIMEImage import MIMEImage
from email.MIMEBase import MIMEBase
from email.MIMEMessage import MIMEMessage
from email.Header import Header
from email import Encoders

quietly = False

import reportbug_ui_text as ui

# Obscene hack :)
def system(cmdline):
    try:
        x = os.getcwd()
    except OSError:
        os.chdir('/')
    os.system(cmdline)

ascii_range = ''.join([chr(ai) for ai in range(32,127)])
notascii = re.compile(r'[^'+re.escape(ascii_range)+']')
notascii2 = re.compile(r'[^'+re.escape(ascii_range)+r'\s]')

# Wrapper for MIMEText
class BetterMIMEText(MIMEText):
    def __init__(self, _text, _subtype='plain', _charset=None):
        MIMEText.__init__(self, _text, _subtype, 'us-ascii')
        # Only set the charset paraemeter to non-ASCII if the body
        # includes unprintable characters
        if notascii2.search(_text):
            self.set_param('charset', _charset)

def encode_if_needed(text, charset, encoding='q'):
    needed = False

    if notascii.search(text):
        # Fall back on something vaguely sensible if there are high chars
        # and the encoding is us-ascii
        if charset == 'us-ascii':
            charset = 'iso-8859-15'
        return Header(text, charset)
    else:
        return Header(text, 'us-ascii')

def rfc2047_encode_address(addr, charset, mua=None):
    newlist = []
    addresses = rfc822.AddressList(addr).addresslist
    for (realname, address) in addresses:
        if realname:
            newlist.append( email.Utils.formataddr(
                (str(rfc2047_encode_header(realname, charset, mua)), address)))
        else:
            newlist.append( address )
    return ', '.join(newlist)

def rfc2047_encode_header(header, charset, mua=None):
    if mua: return header
    #print repr(header), repr(charset)

    return encode_if_needed(header, charset)

# Cheat for now.
# ewrite() may put stuff on the status bar or in message boxes depending on UI
def ewrite(*args):
    return quietly or ui.log_message(*args)

def sign_message(body, fromaddr, package='x', pgp_addr=None, sign='gpg'):
    '''Sign message with pgp key.'''
    ''' Return: a signed body.
        On failure, return None.
        kw need to have the following keys
    '''
    if not pgp_addr:
        pgp_addr = reportbug.get_email_addr(fromaddr)[1]

    # Make the unsigned file first
    (unsigned, file1) = TempFile(prefix=tempfile_prefix(package, 'unsigned'))
    unsigned.write(body)
    unsigned.close()

    # Now make the signed file
    (signed, file2) = TempFile(prefix=tempfile_prefix(package, 'signed'))
    signed.close()

    if sign == 'gpg':
        signcmd = "gpg --local-user '%s' --clearsign" % pgp_addr
    else:
        signcmd = "pgp -u '%s' -fast" % pgp_addr

    signcmd += '<'+commands.mkarg(file1)+' >'+commands.mkarg(file2)
    try:
        os.system(signcmd)
        x = file(file2, 'r')
        signedbody = x.read()
        x.close()

        if os.path.exists(file1):
            os.unlink(file1)
        if os.path.exists(file2):
            os.unlink(file2)

        if not signedbody:
            raise NoMessage
        body = signedbody
    except (NoMessage, IOError, OSError):
        fh, tmpfile2 = TempFile(prefix=tempfile_prefix(package))
        fh.write(body)
        fh.close()
        ewrite('gpg/pgp failed; input file in %s\n', tmpfile2)
        body = None
    return body

def mime_attach(body, attachments, charset, body_charset=None):
    import mimetypes
    mimetypes.init()

    message = MIMEMultipart('mixed')
    bodypart = BetterMIMEText(body, _charset=(body_charset or charset))
    bodypart.add_header('Content-Disposition', 'inline')
    message.preamble = 'This is a multi-part MIME message sent by reportbug.\n\n'
    message.epilogue = ''
    message.attach(bodypart)
    failed = False
    for attachment in attachments:
        try:
            fp = file(attachment)
            fp.close()
        except EnvironmentError, x:
            ewrite("Warning: opening '%s' failed: %s.\n", attachment,
                   x.strerror)
            failed = True
            continue
        ctype = None
        cset = charset
        info = commands.getoutput('file --mime --brief' +
                                   commands.mkarg(attachment) +
                                  ' 2>/dev/null')
        if info:
            match = re.match(r'([^;, ]*)(,[^;]+)?(?:; )?(.*)', info)
            if match:
                ctype, junk, extras = match.groups()
                match = re.search(r'charset=([^,]+|"[^,"]+")', extras)
                if match:
                    cset = match.group(1)
                # If we didn't get a real MIME type, fall back
                if '/' not in ctype:
                    ctype = None
        # If file doesn't work, try to guess based on the extension
        if not ctype:
            ctype, encoding = mimetypes.guess_type(
                attachment, strict=False)
        if not ctype:
            ctype = 'application/octet-stream'

        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            fp = file(attachment, 'rU')
            part = BetterMIMEText(fp.read(), _subtype=subtype,
                                  _charset=cset)
            fp.close()
        elif maintype == 'message':
            fp = file(attachment, 'rb')
            part = MIMEMessage(email.message_from_file(fp),
                               _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = file(attachment, 'rb')
            part = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = file(attachment, 'rb')
            part = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = file(attachment, 'rb')
            part = MIMEBase(maintype, subtype)
            part.set_payload(fp.read())
            fp.close()
            email.Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment',
                        filename=os.path.basename(attachment))
        message.attach(part)
    return (message, failed)

def send_report(body, attachments, mua, fromaddr, sendto, ccaddr, bccaddr,
                headers, package='x', charset="us-ascii", mailing=True,
                sysinfo=None,
                rtype='debbugs', exinfo=None, replyto=None, printonly=False,
                template=False, outfile=None, mta='', kudos=False,
                smtptls=False, smtphost='localhost',
                smtpuser=None, smtppasswd=None, paranoid=False):
    '''Send a report.'''

    failed = using_sendmail = False
    msgname = ''
    # Disable smtphost if mua is set
    if mua and smtphost:
        smtphost = ''

    # No, I'm not going to do a full MX lookup on every address... get a
    # real MTA!
    if kudos and smtphost == 'bugs.debian.org':
        smtphost = 'packages.debian.org'

    body_charset = charset
    if isinstance(body, unicode):
        # Since the body is Unicode, utf-8 seems like a sensible body encoding
        # to choose pretty much all the time.
        body = body.encode('utf-8', 'replace')
        body_charset = 'utf-8'

    tfprefix = tempfile_prefix(package)
    if attachments and not mua:
        (message, failed) = mime_attach(body, attachments, charset, body_charset)
        if failed:
            ewrite("Error: Message creation failed, not sending\n")
            mua = mta = smtphost = None
    else:
        message = BetterMIMEText(body, _charset=body_charset)

    # Standard headers
    message['From'] = rfc2047_encode_address(fromaddr, 'utf-8', mua)
    message['To'] = rfc2047_encode_address(sendto, charset, mua)

    for (header, value) in headers:
        if header in ['From', 'To', 'Cc', 'Bcc', 'X-Debbugs-CC', 'Reply-To',
                      'Mail-Followup-To']:
            message[header] = rfc2047_encode_address(value, charset, mua)
        else:
            message[header] = rfc2047_encode_header(value, charset, mua)

    if ccaddr:
        message['Cc'] = rfc2047_encode_address(ccaddr, charset, mua)

    if bccaddr:
        message['Bcc'] = rfc2047_encode_address(bccaddr, charset, mua)

    replyto = os.environ.get("REPLYTO", replyto)
    if replyto:
        message['Reply-To'] = rfc2047_encode_address(replyto, charset, mua)

    if mailing:
        message['Message-ID'] = email.Utils.make_msgid('reportbug')
        message['X-Mailer'] = VERSION
        message['Date'] = email.Utils.formatdate(localtime=True)
    elif mua and not (printonly or template):
        message['X-Reportbug-Version'] = VERSION_NUMBER

    addrs = [str(x) for x in (message.get_all('To', []) +
                              message.get_all('Cc', []) +
                              message.get_all('Bcc', []))]
    alist = email.Utils.getaddresses(addrs)

    cclist = [str(x) for x in message.get_all('X-Debbugs-Cc', [])]
    debbugs_cc = email.Utils.getaddresses(cclist)
    if cclist:
        del message['X-Debbugs-Cc']
        addrlist = ', '.join(cclist)
        message['X-Debbugs-Cc'] = rfc2047_encode_address(addrlist, charset, mua)

    # Drop any Bcc headers from the message to be sent
    if not outfile and not mua:
        try:
            del message['Bcc']
        except:
            pass

    message = message.as_string()
    if paranoid and not (template or printonly):
        pager = os.environ.get('PAGER', 'sensible-pager')
        os.popen(pager, 'w').write(message)
        if not ui.yes_no('Does your report seem satisfactory', 'Yes, send it.',
                         'No, don\'t send it.'):
            smtphost = mta = None
            
    filename = None
    if template or printonly:
        pipe = sys.stdout
    elif mua:
        pipe, filename = TempFile(prefix=tfprefix)
    elif outfile or not mta or not os.path.exists(mta):
        msgname = outfile or ('/var/tmp/%s.bug' % package)
        if os.path.exists(msgname):
            try:
                os.rename(msgname, msgname+'~')
            except OSError:
                ewrite('Unable to rename existing %s as %s~\n',
                       msgname, msgname)
        try:
            pipe = open_write_safe(msgname, 'w')
        except OSError:
            fh, newmsgname = TempFile(prefix=tfprefix)
            fh.write(message.as_string())
            fh.close()
            ewrite('Writing to %s failed; '
                   'wrote bug report to %s\n', msgname, newmsgname)
            msgname = newmsgname
    elif mta and not smtphost:
        try:
            x = os.getcwd()
        except OSError:
            os.chdir('/')

        malist = [commands.mkarg(a[1]) for a in alist]
        jalist = ' '.join(malist)
        
        faddr = rfc822.parseaddr(fromaddr)[1]
        ewrite("Sending message via %s...\n", mta)
        pipe = os.popen('%s -f %s -oi -oem %s' % (
            mta, commands.mkarg(faddr), jalist), 'w')
        using_sendmail = True

    if smtphost:
        toaddrs = [x[1] for x in alist]
        smtp_message = re.sub(r'(?m)^[.]', '..', message)

        tryagain = True
        refused = None
        while tryagain:
            tryagain = False
            ewrite("Connecting to %s via SMTP...\n", smtphost)
            try:
                conn = smtplib.SMTP(smtphost)
                response = conn.ehlo()
                if not (200 <= response[0] <= 299):
                    conn.helo()
                if smtptls:
                    conn.starttls()
                    response = conn.ehlo()
                    if not (200 <= response[0] <= 299):
                        conn.helo()
                if smtpuser:
                    if not smtppasswd:
                        smtppasswd = ui.get_password(
                            'Enter SMTP password for %s@%s: ' %
                            (smtpuser, smtphost))
                    conn.login(smtpuser, smtppasswd)
                refused = conn.sendmail(fromaddr, toaddrs, smtp_message)
                conn.quit()
            except (socket.error, smtplib.SMTPException), x:
                # If wrong password, try again...
                if isinstance(x, smtplib.SMTPAuthenticationError):
                    ewrite('SMTP error: authentication failed.  Try again.\n')
                    tryagain = True
                    smtppasswd = None
                    continue
            
                failed = True
                ewrite('SMTP send failure: %s\n', x)

                fh, msgname = TempFile(prefix=tfprefix)
                fh.write(message)
                fh.close()

                ewrite('Wrote bug report to %s\n', msgname)
        # Handle when some recipients are refused.
        if refused:
            for (addr, err) in refused.iteritems():
                ewrite('Unable to send report to %s: %d %s\n', addr, err[0],
                       err[1])
            fh, msgname = TempFile(prefix=tfprefix)
            fh.write(message)
            fh.close()

            ewrite('Wrote bug report to %s\n', msgname)
    else:
        try:
            pipe.write(message)
            pipe.flush()
            if msgname:
                ewrite("Bug report written as %s\n", msgname)
        except IOError:
            failed = True
            pipe.close()

        if failed or (pipe.close() and using_sendmail):
            failed = True
            fh, msgname = TempFile(prefix=tfprefix)
            fh.write(message)
            fh.close()
            ewrite('Original write failed, wrote bug report to %s\n', msgname)

    if mua:
        for bit in mua.split():
            if '%s' not in bit: break
        ewrite("Spawning %s...\n", bit or mua)
        if '%s' not in mua:
            mua += ' %s'
        system(mua % commands.mkarg(filename)[1:])
    elif not failed and (using_sendmail or smtphost):
        if kudos:
            ewrite('\nMessage sent to: %s\n', sendto)
        else:
            ewrite("\nBug report submitted to: %s\n", sendto)

        addresses = []
        for addr in alist:
            if addr[1] != rfc822.parseaddr(sendto)[1]:
                addresses.append(addr)

        if len(addresses):
            ewrite("Copies sent to:\n")
            for address in addresses:
                ewrite('  %s\n', rfc822.dump_address_pair(address))

        if debbugs_cc and rtype == 'debbugs':
            ewrite("Copies will be sent after processing to:\n")
            for address in debbugs_cc:
                ewrite('  %s\n', rfc822.dump_address_pair(address))

        if not (exinfo or kudos) and rtype == 'debbugs' and sysinfo:
            ewrite('\n')
            ui.long_message(
"""If you want to provide additional information, please wait to
receive the bug tracking number via email; you may then send any extra
information to %s (e.g. %s), where n is the bug number.  Normally you
will receive an acknowledgement via email including the bug report number
within an hour.\n""",
            (sysinfo['email'] % 'n'), (sysinfo['email'] % '999999'))

    # If we've stored more than one copy of the message, delete the
    # one without the SMTP headers.
    if filename and os.path.exists(msgname) and os.path.exists(filename):
        try:
            os.unlink(filename)
        except:
            pass

    if filename and os.path.exists(filename) and not mua:
        # Message is misleading if an MUA is used.
        ewrite("A copy of the report is stored as: %s\n" % filename)
    return

def main():
    'o'

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        ewrite("\nreportbug: exiting due to user interrupt.\n")
    except debianbts.Error, x:
        ewrite('error accessing BTS: %s\n' % x)

# vim:ts=8:sw=4:expandtab
