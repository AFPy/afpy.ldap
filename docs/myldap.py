# -*- coding: utf-8 -*-
from afpy.ldap.node import User as BaseUser
from afpy.ldap.node import GroupOfNames
from afpy.ldap import schema

class User(BaseUser):
    _rdn = 'uid'
    _base_dn = 'ou=members,dc=exemple,dc=org'

    # default user properties
    _defaults = dict(
        objectClass = ['top', 'person',
                       'organizationalPerson', 'inetOrgPerson'],
        st='FR',
       )
    uid=schema.StringProperty('uid', title='Login')
    sn=schema.UnicodeProperty('sn', title='Nom')
    mail=schema.StringProperty('mail', title='E-mail')

class Group(GroupOfNames):
    _rdn = 'cn'
    _base_dn = 'ou=groups,dc=exemple,dc=org'

