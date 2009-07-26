# -*- coding: utf-8 -*-
import afpy.ldap


class ExtendedNode(object):

    def extended(self):
        return True

def get_conn():
    ldap = afpy.ldap.Connection()
    return afpy.ldap.Connection(section=ldap.config.tests.section)

