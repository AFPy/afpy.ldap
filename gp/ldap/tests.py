# -*- coding: utf-8 -*-
import unittest
import gp.ldap

ldap = gp.ldap.LDAP()

def test_credential():
    assert ldap.checkCredentials('gawel', 'toto') is False

def test_dn():
    assert ldap.base_dn == 'ou=people,dc=gawel,dc=org', ldap.base_dn

def test_search():
    results = ldap.search(filter='(uid=gawel)')
    assert results['size'] == 1, results
