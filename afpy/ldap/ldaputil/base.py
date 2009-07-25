"""
ldaputil.base - basic LDAP functions
(c) by Michael Stroeder <michael@stroeder.com>

This module is distributed under the terms of the
GPL (GNU GENERAL PUBLIC LICENSE) Version 2
(see http://www.gnu.org/copyleft/gpl.html)

Python compability note:
This module only works with Python 1.6+ since all string parameters
are assumed to be Unicode objects and string methods are used instead
string module.

$Id: base.py,v 1.33 2008/07/18 10:15:44 michael Exp $
"""

__version__ = '$Revision: 1.33 $'.split(' ')[1]


import re,ldap

from ldapurl import LDAPUrl

SEARCH_SCOPE_STR = ['base','one','sub']

SEARCH_SCOPE = {
  # default for empty search scope string
  '':ldap.SCOPE_BASE,
  # the search scope strings defined in RFC22xx(?)
  'base':ldap.SCOPE_BASE,
  'one':ldap.SCOPE_ONELEVEL,
  'sub':ldap.SCOPE_SUBTREE
}

attr_type_pattern = ur'[\w;.-]+(;[\w_-]+)*'
attr_value_pattern = ur'(([^,]|\\,)+|".*?")'
rdn_pattern = attr_type_pattern + ur'[ ]*=[ ]*' + attr_value_pattern
dn_pattern   = rdn_pattern + r'([ ]*,[ ]*' + rdn_pattern + r')*[ ]*'

dc_rdn_pattern = ur'(dc|)[ ]*=[ ]*' + attr_value_pattern
dc_dn_pattern   = dc_rdn_pattern + r'([ ]*,[ ]*' + dc_rdn_pattern + r')*[ ]*'

#rdn_regex   = re.compile('^%s$' % rdn_pattern)
dn_regex      = re.compile(u'^%s$' % unicode(dn_pattern))

# Some widely used types
StringType = type('')
UnicodeType = type(u'')

ROOTDSE_ATTRS = [
  'defaultNamingContext',
  'defaultRnrDN',
  'altServer',
  'namingContexts',
  'subschemaSubentry',
  'supportedLDAPVersion',
  'subschemaSubentry',
  'supportedControl',
  'supportedSASLMechanisms',
  'supportedExtension',
  'supportedFeatures',
  'objectclass',
  'supportedSASLMechanisms',
  'dsServiceName',
  'ogSupportedProfile',
  'netscapemdsuffix',
  'dataversion',
  'dsaVersion',
]

def unicode_list(l,charset='utf-8'):
  """
  return list of Unicode objects
  """
  return [
    unicode(i,charset)
    for i in l
  ]

def unicode_entry(e,charset='utf-8'):
  """
  return dictionary of lists of Unicode objects
  """
  result = {}
  for attrtype,valuelist in e.items():
    result[attrtype]=unicode_list(valuelist,charset)
  return result

def encode_unicode_list(l,charset='utf-8'):
  """
  Encode the list of Unicode objects with given charset
  and return list of encoded strings
  """
  return [ i.encode(charset) for i in l ]

def is_dn(s):
  """returns 1 if s is a LDAP DN"""
  if s:
    rm = dn_regex.match(s)
    return rm!=None
  elif s=='':
    return 1
  else:
    return 0

def explode_rdn_attr(attr_type_and_value):
  """
  explode_rdn_attr(attr_type_and_value) -> tuple

  This function takes a single attribute type and value pair
  describing a characteristic attribute forming part of a RDN
  (e.g. 'cn=Michael Stroeder') and returns a 2-tuple
  containing the attribute type and the attribute value unescaping
  the attribute value according to RFC 2253 if necessary.
  """
  attr_type,attr_value = attr_type_and_value.split('=')
  if attr_value:
    r = []
    start_pos=0
    i = 0
    attr_value_len=len(attr_value)
    while i<attr_value_len:
      if attr_value[i]=='\\':
        r.append(attr_value[start_pos:i])
        start_pos=i+1
      i=i+1
    r.append(attr_value[start_pos:i])
    attr_value = ''.join(r)
  return (attr_type,attr_value)

def rdn_dict(dn,charset='utf-8'):
  rdn,rest = SplitRDN(dn)
  if not rdn:
    return {}
  if type(rdn)==UnicodeType:
    rdn = rdn.encode(charset)
  result = {}
  for i in ldap.explode_rdn(rdn.strip()):
    attr_type,attr_value = explode_rdn_attr(i)
#    attr_value = unicode(attr_value,charset)
    if result.has_key(attr_type):
      result[attr_type].append(attr_value)
    else:
      result[attr_type]=[attr_value]
  return result

def explode_dn(dn,charset='utf-8'):
  """
  Wrapper function for explode_dn() which returns [] for 
  a zero-length DN
  """
  if not dn:
    return []
  if type(dn)==UnicodeType:
    dn = dn.encode(charset)
  dn_list = ldap.explode_dn(dn.strip())
  if dn_list and dn_list!=['']:
    return [ unicode(dn.strip(),charset) for dn in dn_list ]
  else:
    return []


def normalize_dn(dn):
  if dn=='\000':
    return ''
  else:
    return dn
#def normalize_dn(dn):
#  result = explode_dn(dn)
#  return ','.join(result)


def matching_dn_components(dn1_components,dn2_components):
  """
  Returns how much levels of two distinguished names
  dn1 and dn2 are matching.
  """
  if not dn1_components or not dn2_components:
    return (0,u'')
  # dn1_cmp has to be shorter than dn2_cmp
  if len(dn1_components)<=len(dn2_components):
    dn1_cmp,dn2_cmp = dn1_components,dn2_components
  else:
    dn1_cmp,dn2_cmp = dn2_components,dn1_components
  i = 1 ; dn1_len = len(dn1_cmp)
  while (dn1_cmp[-i].lower()==dn2_cmp[-i].lower()):
    i = i+1
    if i>dn1_len:
      break
  if i>1:
    return (i-1,','.join(dn2_cmp[-i+1:]))
  else:
    return (0,u'')


def match_dn(dn1,dn2):
  """
  Returns how much levels of two distinguished names
  dn1 and dn2 are matching.
  """
  return matching_dn_components(explode_dn(dn1),explode_dn(dn2))


def match_dnlist(dn,dnlist):
  """find best matching parent DN of dn in dnlist"""
  dnlist = dnlist or [ ]
  dn_components = explode_dn(dn)
  max_match_level, max_match_name = 0, ''
  for dn_item in dnlist:
    match_level,match_name = matching_dn_components(
      explode_dn(dn_item),dn_components
    )
    if match_level>max_match_level:
      max_match_level, max_match_name = match_level, match_name
  return max_match_name


def extract_referrals(e):
  """Extract the referral LDAP URL from a
     ldap.PARTIAL_RESULTS exception object"""
  if e.args[0].has_key('info'):
    info, ldap_url_info = [
      x.strip()
      for x in e.args[0]['info'].split('\n',1)
    ]
  else:
    raise ValueError, "Referral exception object does not have info field"
  ldap_urls = [
    LDAPUrl(l)
    for l in ldap_url_info.split('\n')
  ]
  matched = e.args[0].get('matched',None)
  return (matched,ldap_urls)

def ParentDN(dn):
  """returns parent-DN of dn"""
  dn_comp = explode_dn(dn)
  if len(dn_comp)>1:
    return ','.join(dn_comp[1:])
  elif len(dn_comp)==1:
    return ''
  else:
    return None

def SplitRDN(dn):
  """returns tuple (RDN,base DN) of dn"""
  dn_comp = explode_dn(dn)
  if len(dn_comp)>1:
    return dn_comp[0], ','.join(dn_comp[1:])
  elif len(dn_comp)==1:
    return dn_comp[0], ''
  else:
    return None,None

def ParentDNList(dn,rootdn=''):
  """returns a list of parent-DNs of dn"""
  result = []
  DNComponentList = explode_dn(dn)
  if rootdn:
    max_level = len(explode_dn(rootdn))
  else:
    max_level = len(DNComponentList)
  for i in range(1,max_level):
    result.append(','.join(DNComponentList[i:]))
  return result


def escape_dn_chars(s):
  """
  Replace all special characters found in s
  by quoted notation
  """
  if s:
    s = s.replace('\\','\\\\')
    s = s.replace(',' ,'\\,')
    s = s.replace('+' ,'\\+')
    s = s.replace('"' ,'\\"')
    s = s.replace('<' ,'\\<')
    s = s.replace('>' ,'\\>')
    s = s.replace(';' ,'\\;')
    s = s.replace('=' ,'\\=')
    if s[0]=='#':
      s = ''.join(('\\',s))
    if s[-1]==' ':
      s = ''.join((s[:-1],'\\ '))
  return s


def test():
  """Test functions"""

  print '\nTesting function is_dn():'
  ldap_dns = {
    u'o=Michaels':1,
    u'iiii':0,
    u'"cn="Mike"':0,
  }
  for ldap_dn in ldap_dns.keys():
    result_is_dn = is_dn(ldap_dn)
    if result_is_dn !=ldap_dns[ldap_dn]:
      print 'is_dn("%s") returns %d instead of %d.' % (
        ldap_dn,result_is_dn,ldap_dns[ldap_dn]
      )

  print '\nTesting function escape_dn_chars():'
  ldap_dns = {
    u'#\\,+"<>; ':u'\\#\\\\\\,\\+\\"\\<\\>\\;\\ ',
    '#\\,+"<>; ':'\\#\\\\\\,\\+\\"\\<\\>\\;\\ ',
    u'Str\xf6der':u'Str\xf6der',
    'Str\xc3\xb6der':'Str\xc3\xb6der',
    '':'',
  }
  for ldap_dn in ldap_dns.keys():
    result_escape_dn_chars = escape_dn_chars(ldap_dn)
    if result_escape_dn_chars !=ldap_dns[ldap_dn]:
      print 'escape_dn_chars(%s) returns %s instead of %s.' % (
        repr(ldap_dn),
        repr(result_escape_dn_chars),repr(ldap_dns[ldap_dn])
      )

  print '\nTesting function explode_rdn_attr():'
  ldap_dns = {
    'cn=Michael Stroeder':('cn','Michael Stroeder'),
    'cn=whois\+\+':('cn','whois++'),
    'cn=\#dummy\ ':('cn','#dummy '),
    'cn;lang-en-EN=Michael Stroeder':('cn;lang-en-EN','Michael Stroeder'),
    'cn=':('cn',''),
  }
  for ldap_dn in ldap_dns.keys():
    result_explode_rdn_attr = explode_rdn_attr(ldap_dn)
    if result_explode_rdn_attr !=ldap_dns[ldap_dn]:
      print 'explode_rdn_attr(%s) returns %s instead of %s.' % (
        repr(ldap_dn),
        repr(result_explode_rdn_attr),repr(ldap_dns[ldap_dn])
      )

  print '\nTesting function match_dn():'
  match_dn_tests = {
    ('O=MICHAELS','o=michaels'):(1,u'O=MICHAELS'),
    ('CN=MICHAEL STROEDER,O=MICHAELS','o=michaels'):(1,u'O=MICHAELS'),
    ('CN=MICHAEL STROEDER,O=MICHAELS',''):(0,u''),
    ('CN=MICHAEL STROEDER,O=MICHAELS','     '):(0,u''),
    ('CN=MICHAEL STROEDER,O=MICHAELS','  cn=Michael Stroeder,o=Michaels  '):(2,u'cn=Michael Stroeder,o=Michaels'),
    ('CN=MICHAEL STROEDER,O=MICHAELS','mail=michael@stroeder.com,  cn=Michael Stroeder,o=Michaels  '):(2,u'cn=Michael Stroeder,o=Michaels'),
  }
  for dn1,dn2 in match_dn_tests.keys():
    result_match_dn = match_dn(dn1,dn2)
    if result_match_dn[0] !=match_dn_tests[(dn1,dn2)][0] or \
       result_match_dn[1].lower() !=match_dn_tests[(dn1,dn2)][1].lower():
      print 'match_dn(%s,%s) returns:\n%s\ninstead of:\n%s\n' % (
        repr(dn1),repr(dn2),
        repr(result_match_dn),
        repr(match_dn_tests[(dn1,dn2)])
      )


if __name__ == '__main__':
  test()
