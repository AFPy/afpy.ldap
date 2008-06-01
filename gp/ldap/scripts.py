# -*- coding: utf-8 -*-
from optparse import OptionParser
import gp.ldap
import string
import base64
import sys

parser = OptionParser()
parser.add_option('-s', '--section', dest='section', default='default',
                  help='A config section to get ldap info from')
parser.add_option('-f', '--filter', dest='filter',
                  help='A unique ldap filter. eg: cn=a*')
parser.add_option('-p', '--password', dest='password',
                  help='Print encrypted password')


def grep(section, arg):
    adapter = gp.ldap.get(section)
    conn = adapter.getConnection()
    results = conn.search(adapter.base_dn,
                          'sub', '(%s)' % arg)
    for result in sorted(results):
        gp.ldap.pprint(result)

def cat(section):
    for l in string.ascii_letters[26:]:
        grep(section, 'cn=%s*' % l)

def main():
    (options, args) = parser.parse_args()
    if options.password:
        print base64.encodestring(options.password)
        return
    if options.filter:
        grep(options.section, options.filter)
    else:
        cat(options.section)

