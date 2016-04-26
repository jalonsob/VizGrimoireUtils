#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#    Jesús Alonso Barrionuevo <jalonso@bitergia.com>


import os
import sys
import time
import subprocess
import ConfigParser
import logging
from argparse import ArgumentParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

class Record_machine(object):
    __slots__ = "name", "connection", "log_from"

    def items(self):
        "dict style items"
        return [
            (field_name, getattr(self, field_name))
            for field_name in self.__slots__]
    def __set__(self, attr, value):
        "set a value in an item"
        setattr(self, attr, value)
    def getattrs(self):
        "get the list of attrs"
        return self.__slots__
    def __iter__(self):
        "iterate over fields tuple/list style"
        for field_name in self.__slots__:
            yield getattr(self, field_name)
    def __getitem__(self, index):
        "tuple/list style getitem"
        return getattr(self, self.__slots__[index])


def get_args():
    parser = ArgumentParser(usage='Usage: %(prog)s [options]',
            description='Checks data freshness log of SQL databases in all machines and made a new mail',
            version='0.1')
    parser.add_argument('-g', '--debug', dest='debug',
            help='Debug mode, disabled by default',
            required=False, action='store_true')
    parser.add_argument('--conf', dest='config_file',
            help='Configuration file',
            required=False)
    parser.add_argument('-s', '--send', dest='send',
            help='Sends the information to the mail. Disabled by default.',
            required=False, action='store_true')
    parser.add_argument('-f', '--file', dest='file',
                    help='Generates a file with the content of the report.',
                    required=False, action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return args

def read_conf(file_path):

    Config = ConfigParser.ConfigParser()
    Config.read(file_path)

    machines=[]
    config_machines=[]
    opts={}

    str_machines_option =Config.get("config", "machines")
    machines=str_machines_option.split(',')
    for machine in machines:
        r=Record_machine()
        for attribute in r.getattrs():
            if attribute=="name":
                r.name=machine
            else:
                r.__set__(attribute,Config.get("config", machine+"_"+attribute))
        config_machines.append(r)

    try:
        opts['email_from'] = Config.get('config', 'email_from')
    except ConfigParser.NoOptionError:
        myhost = os.uname()[1]
        opts['email_from'] = myhost
	logging.debug("There is no email_from specify. 'myhost' used by default.")
    
    try:
        opts['email_to'] = Config.get('config', 'email_to')
    except ConfigParser.NoOptionError:
        opts['email_to'] = ''

    try:
        opts['log_files'] = Config.get('config', 'log_files')
    except ConfigParser.NoOptionError:
        opts['log_files'] = os.getcwd()
	logging.debug("There is no path specify for logs. Actual path used by default.")

    return config_machines,opts

def scp_logs(machines,opts):

    for machine in machines:
        try:
            logging.debug('rsync -a '+machine.connection+':'+machine.log_from+'.'+time.strftime("%Y%m%d")+' '+opts['log_files']+'/'+machine.name+'.log.'+time.strftime("%Y%m%d"))
            subprocess.check_call('rsync -a '+machine.connection+':'+machine.log_from+'.'+time.strftime("%Y%m%d")+' '+opts['log_files']+'/'+machine.name+'.log.'+time.strftime("%Y%m%d"),shell=True)
        except:
            if opts['log_files'] == os.getcwd():
                logging.debug("created "+machine.name+'.log.'+time.strftime("%Y%m%d"))
                target = open(opts['log_files']+'/'+machine.name+'.log.'+time.strftime("%Y%m%d"),'w')
            else:
                logging.debug("created "+opts['log_files']+machine.name+'/'+time.strftime("%Y%m%d")+'.log')
                target = open(opts['log_files']+machine.name+'/'+time.strftime("%Y%m%d")+'.log','w')
            target.write("---THERE IS NO DATA FOR TODAY---\n")
            target.close()

def compile_logs(machines,opts):

    body=''
    for machine in machines:
        try:
            if opts['log_files'] == os.getcwd():
                f = open(opts['log_files']+'/'+machine.name+'.log.'+time.strftime("%Y%m%d"),"r")
            else:
                f = open(opts['log_files']+machine.name+'/'+time.strftime("%Y%m%d")+'.log',"r")
            new_str = f.read()
            new_str= '****'+machine.name+'****\n\n'+new_str+'\n'
            body=body+new_str
        except:
            logging.debug("ERROR READING : "+opts['log_files']+machine.name+'/'+time.strftime("%Y%m%d")+'.log',"r")

    return body

def send_mail(text, subject, msg_from, msg_to):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = msg_from
    msg['To'] = msg_to

    body = MIMEText(text, 'plain')

    msg.attach(body)

    s = smtplib.SMTP('localhost')
    s.sendmail(msg_from, msg_to, msg.as_string())
    s.quit()

def send(body,opts):
    if len(opts['email_to'])>0:
        msg_subject = 'SQL Data smells compilation '
        send_mail(body, msg_subject,opts['email_from'], opts['email_to'])
        logging.debug("Mail sent to %s" % (opts['email_to']))
    else:
        logging.debug("There is no destiny email to send.")

def create_file_compilation(body,opts):
    target = open(opts['log_files']+'/'+time.strftime("%Y%m%d")+'.log','w')
    target.write(body)
    target.close()

if __name__ == '__main__':

    args = get_args()
    machines,opts=read_conf(args.config_file)
    scp_logs(machines,opts)
    body=compile_logs(machines,opts)
    if args.send:
        send(body,opts)
    if args.file:
        create_file_compilation(body,opts)
