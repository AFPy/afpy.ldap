# -*- coding: utf-8 -*-
import gp.ldap
import string
import sys

def grep():
    section = None
    if len(sys.argv) == 3:
        section, arg = sys.argv[1:3]
    else:
        arg = sys.argv[1]
    adapter = gp.ldap.get(section)
    conn = adapter.getConnection()
    results = conn.search(adapter.dase_dn,
                          'sub', '(%s)' % arg)
    for result in results:
        gp.ldap.pprint(result)

def cat():
    section = None
    if len(sys.argv) == 2:
        section = sys.argv[1]
    for l in string.ascii_letters[26:]:
        sys.argv[1:3] = [section, 'cn=%s*' % l]
        grep()

