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

from dataflake.ldapconnection.connection import LDAPConnection
from ConfigParser import ConfigParser
from ConfigParser import NoOptionError
import ldap
import os




def ldapconnection_from_config(config, prefix='ldap.', **kwargs):
    """This is useful to get an LDAPConnection from a ConfigParser section
    items.
    """
    options = dict(
            host='localhost',
            port = 386,
            protocol = 'ldap',
            c_factory = ldap.initialize,
            login_attr='',
            rdn_attr='',
            bind_dn='',
            bind_pwd='',
            read_only=0,
            conn_timeout=-1,
            op_timeout=-1)

    options.update(kwargs)

    for key, value in config.items():
        if prefix in key:
            k = key.replace(prefix, '')
            if k in options:
                if isinstance(options[k], int):
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        raise TypeError(
                           '%s must be an integer. Got %s' % (key, value))
                options[k] = value

    if not callable(options['c_factory']):
        raise TypeError(
           'c_factory must be callable. Got %(c_factory)s' % options)

    return LDAPConnection(**options)

IGNORE_KEYS=['uid', 'cn', 'sn', 'givenName',
             'userPassword', 'objectClass',
             'jpegPhoto']

def get(section=None):
    return LDAP(section or 'default')

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

class LDAP(object):
    def __init__(self, section='default', filename=os.path.expanduser('~/.ldap.cfg')):
        self.config = ConfigParser()
        self.config.read([filename])
        self.section = section
        self._conn = self.connection_factory()
        self.bind_dn = self.get('bind_dn')
        self.bind_pw = self.get('bind_pw')


    def get(self, key, default=None):
        try:
            return self.config.get(self.section, key)
        except (NoOptionError, KeyError):
            return default

    def connection_factory(self, user=None, passwd=None):
        config = dict(self.config.items(self.section))
        conn = ldapconnection_from_config(config)
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        ldap.set_option(ldap.OPT_REFERRALS, 0)
        return conn

    @property
    def base_dn(self):
        dn = self.get('bind_dn')
        dn = dn.split(',', 1)[1]
        return dn

    def check(self, cn, password):
        uid = self.get('bind_dn').split('=')[0]
        dn = '%s=%s,%s' % (uid, cn, self.base_dn)
        try:
            self.connection_factory().connect(dn, password)
        except ldap.INVALID_CREDENTIALS, e:
            return False
        return True

    def search(self, *args, **kwargs):
        return self._conn.search(self.base_dn,
                                 ldap.SCOPE_SUBTREE,
                                 bind_dn=self.bind_dn,
                                 bind_pwd=self.bind_pw,
                                 *args, **kwargs)


class User(object):

    def __init__(self, uid, section=None):
        self._uid = uid
        self._conn = get(section)
        self._data = None

    def check(self, password):
        return self._conn.check(self._uid, password)

    def normalized_data(self):
        if self._data:
            return self._data
        self._data = {}
        uid = self._conn.get('bind_dn').split('=')[0]
        filter = self._conn.get('search_filter', '(uid={uid})').replace('{uid}', self._uid)
        data = self._conn.search(filter=filter)
        results = data.get('results', {})
        if len(results) == 1:
            for k, v in results[0].items():
                if len(v) == 1:
                    v = v[0]
                self._data[k] = v

        return self._data

    def save(self):
        self._conn._conn.modify(self.dn, attrs=self._data)

    def __getattr__(self, attr):
        return self.normalized_data().get(attr, None)

    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            object.__setattr__(self, attr, value)
        else:
            data = self.normalized_data()
            data[attr] = value
