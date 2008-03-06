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

from ldapadapter.utility import LDAPAdapter
import gp.config.parsers

IGNORE_KEYS=['uid', 'cn', 'sn', 'givenName',
             'userPassword', 'objectClass']

def get(section=None):
    return LDAP(section or 'default')

def pprint(ldiff):
    def format(x,y):
        if isinstance(y, list):
            y = u'\n'.join(y)
        if isinstance(y, unicode):
            y = y.encode('iso-8859-1')
        print '%s%s%s' % (x,' '*(10-len(x)),y)
    dn, datas = ldiff
    cn = ' '.join(datas['cn'])
    print ''
    print cn
    print '='*len(cn)
    format('dn', dn)
    keys = [k for k in datas if k not in IGNORE_KEYS]
    for key in keys:
        format(key, datas[key])

def xhtml(ldiff):
    def format(x,y):
        if isinstance(y, list):
            y = u'\n'.join(y)
        if isinstance(y, unicode):
            y = y.encode('utf-8')
        return '<dd><label>%s:</label> <span>%s</span></dd>' % (x,y)
    dn, datas = ldiff
    cn = u' '.join(datas['cn']).encode('utf-8')
    out = ['<dl class="ldiff"><dt>%s</dt>' % cn]
    format('dn', dn)
    keys = [k for k in datas if k not in IGNORE_KEYS]
    for key in keys:
        out.append(format(key, datas[key]))
    out.append('</dl>')
    return ''.join(out)

class LDAP(LDAPAdapter):
    def __init__(self, section):
        self.section = section
        super(LDAP, self).__init__(self.get('host', 'localhost'),
                                   int(self.get('port', 389)))


    @property
    def config(self):
        return gp.config.parsers.read('ldap')

    def get(self, key, default=None):
        try:
            return self.config.get(self.section, key)
        except KeyError:
            return default

    def getConnection(self, user=None, passwd=None):
        if user is None:
            user, passwd = self.config.userinfos(self.section)
        elif not user:
            return self.connect()
        return self.connect(user, passwd)

    @property
    def base_dn(self):
        dn = self.get('username')
        dn = ','.join(dn.split(',')[-3:])
        return dn

    def __repr__(self):
        return '<LDAP at %s>' % self.get('host', 'localhost')
