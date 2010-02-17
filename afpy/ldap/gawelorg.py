# -*- coding: utf-8 -*-
from afpy.ldap.node import User as BaseUser
from afpy.ldap.scripts import shell
from afpy.ldap import schema
import sys
import os

class User(BaseUser):
    _rdn = 'uid'
    _base_dn = 'ou=people,dc=gawel,dc=org'
    _defaults = dict(
        objectClass = ['inetOrgPerson', 'organizationalPerson', 'person', 'top'],
        st='FR',
       )

    mail=schema.StringProperty('mail', title='E-mail', required=True)
    portable=schema.StringProperty('mobile', title='Port.', required=True)
    tel=schema.StringProperty('telephoneNumber', title='Tel.', required=True)
    address=schema.UnicodeProperty('postalAddress', title='Adresse', required=True)
    cp=schema.StringProperty('postalCode', title='CP', required=True)
    ville=schema.StringProperty('l', title='Ville', required=True)
    extra=schema.StringProperty('description', title='Extra', required=True)

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
    shell.api.to_user_ns('u')
    print u.pprint()

def contacts(self, parameter_s=''):
    """write users with phone in a file"""
    shell.search(User, '(|(mobile=*)(telephoneNumber=*))')
    if os.path.isdir('/Volumes/iPod/Notes'):
        filename = '/Volumes/iPod/Notes/contacts'
    else:
        filename = 'contacts.txt'
    filename = parameter_s or filename
    fd = open(filename, 'w')
    fd.write(shell.nodes['User'].pprint('utf-8'))
    fd.close()
    print filename, 'saved'

def main():
    def callback():
        shell.expose_magic(add_user)
        shell.expose_magic(contacts)
        shell.search(User, '-')
    shell(section='gawel', classes=(User,), callback=callback)

if __name__ == '__main__':
    main()
