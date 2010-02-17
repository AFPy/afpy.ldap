# -*- coding: utf-8 -*-
from afpy.ldap.connection import Connection as BaseConnection
from afpy.ldap.node import Node
from afpy.ldap.node import User as BaseUser
from afpy.ldap.utils import to_string, to_python
from afpy.ldap.scripts import shell
from afpy.ldap import schema
import sys

class User(BaseUser):
    _rdn = 'uid'
    _base_dn = 'ou=people,dc=gawel,dc=org'
    _defaults = dict(
        objectClass = ['inetOrgPerson', 'organizationalPerson', 'person', 'top'],
        st='FR',
       )

    mail=schema.StringProperty('mail', title='E-mail', required=True)
    birthDate=schema.DateProperty('birthDate', title="Date de naissance", required=True)
    telephoneNumber=schema.StringProperty('telephoneNumber', title='Tel.', required=True)
    mobile=schema.StringProperty('mobile', title='Port.', required=True)
    postalAddress=schema.UnicodeProperty('postalAddress', title='Adresse', required=True)
    postalCode=schema.StringProperty('postalCode', title='CP', required=True)
    description=schema.StringProperty('description', title='Extra', required=True)

    def pprint(self, *args, **kwargs):
        kwargs.update(show_dn=False)
        return BaseUser.pprint(self, **kwargs)

def add_user(self, parameter_s=''):
    """add a user (uid as optional parameter)
    """
    uid = parameter_s or raw_input('uid: ')
    cn = raw_input('prenom nom: ')
    cn = cn.decode(sys.stdin.encoding)
    u = User()
    u.uid = uid
    u.cn = cn
    u.givenName, u.sn = cn.split(' ')
    __IPYTHON__.api.to_user_ns('u')
    print u.pprint()

def write(self, parameter_s=''):
    """write users with phone in a file"""
    shell.search(User, '(|(mobile=*)(telephoneNumber=*))')
    filename = parameter_s or 'contacts.txt'
    fd = open(filename, 'w')
    fd.write(shell.nodes['User'].pprint('utf-8'))
    fd.close()
    print filename, 'saved'

def main():
    def callback():
        shell.expose_magic('add_user', add_user)
        shell.expose_magic('write', write)
        shell.search(User, '-')
        print shell.nodes['User'].pprint()
    shell(section='gawel', classes=(User,), callback=callback)

