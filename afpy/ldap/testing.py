# -*- coding: utf-8 -*-
import afpy.ldap

def get_conn():
    ldap = afpy.ldap.Connection()
    return afpy.ldap.Connection(section=ldap.config.tests.section)

