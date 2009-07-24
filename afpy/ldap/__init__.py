# -*- coding: utf-8 -*-
#Copyright (C) 2009 Gael Pasgrimaud
from connection import Connection
import os

IGNORE_KEYS=['uid', 'cn', 'sn', 'givenName',
             'userPassword', 'objectClass',
             'jpegPhoto']

def get_conn(section='ldap', prefix='ldap.', filename=os.path.expanduser('~/.ldap.cfg')):
    return Connection(section=section, prefix=prefix, filename=filename)

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

