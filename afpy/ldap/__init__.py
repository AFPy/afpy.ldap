# -*- coding: utf-8 -*-
#Copyright (C) 2007 Gael Pasgrimaud
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from connection import LDAP
import os

IGNORE_KEYS=['uid', 'cn', 'sn', 'givenName',
             'userPassword', 'objectClass',
             'jpegPhoto']

def get_conn(section='ldap', prefix='ldap.', filename=os.path.expanduser('~/.ldap.cfg')):
    return LDAP(section=section, prefix=prefix, filename=filename)

def pprint(datas):
    def format(x,y):
        if isinstance(y, list):
            try:
                y = '\n'.join([s for s in y])
            except UnicodeDecodeError:
                print 'XXX',x
                print '%r' % y
        if isinstance(y, unicode):
            y = y.encode('iso-8859-1')
        print '%s%s%s' % (x,' '*(20-len(x)),y)
    cn = ' '.join(datas['cn'])
    print ''
    print cn
    print '='*len(cn)
    keys = [k for k in datas if k not in IGNORE_KEYS]
    for key in keys:
        format(key, datas[key])

def xhtml(datas):
    def format(x,y):
        if isinstance(y, list):
            y = '\n'.join(y)
        if isinstance(y, str):
            y = y
        return '<div><label>%s:</label> <span>%s</span></div>' % (x,y)
    cn = ' '.join(datas['cn']).encode('utf-8')
    out = ['<div class="ldiff"><h3>%s</h3><div class="ldiff_body">' % cn]
    keys = [k for k in datas if k not in IGNORE_KEYS]
    for key in keys:
        out.append(format(key, datas[key]))
    out.append('</div></div>')
    return ''.join(out)

