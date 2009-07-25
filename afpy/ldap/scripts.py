# -*- coding: utf-8 -*-
from optparse import OptionParser
import afpy.ldap
import string
import base64
import sys

parser = OptionParser()
parser.add_option('-s', '--section', dest='section', default='default',
                  help='A config section to get ldap info from')
parser.add_option('-f', '--filter', dest='filter',
                  help='A unique ldap filter. eg: cn=a*')
parser.add_option('-u', '--uid', dest='uid',
                  help='A unique ldap uid. eg: uid=<value>*')

def grep(section, arg):
    adapter = gp.ldap.get(section)
    results = adapter.search('(%s)' % arg)['results']
    for result in sorted(results):
        gp.ldap.pprint(result)

def cat(section):
    for l in string.ascii_letters[26:]:
        grep(section, 'cn=%s*' % l)

def main():
    (options, args) = parser.parse_args()
    if options.filter:
        grep(options.section, options.filter)
    if options.uid:
        grep(options.section, 'uid=%s*' % options.uid)
    else:
        cat(options.section)

