# -*- coding: utf-8 -*-
import unittest
import gp.ldap
import gp.ldap.wsgi
from paste.fixture import TestApp

ldap = gp.ldap.LDAP()

def test_credential():
    assert ldap.checkCredentials('gawel', 'toto') is False

def test_dn():
    assert ldap.base_dn == 'ou=people,dc=gawel,dc=org', ldap.base_dn

def test_search():
    results = ldap.search(filter='(uid=gawel)')
    assert results['size'] == 1, results

app = TestApp(gp.ldap.wsgi.application)

def test_perm():
    try:
        response = app.get('/')
    except:
        pass
    else:
        raise AssertionError()

def test_index():
    response = app.get('/', extra_environ={'REMOTE_USER':'gawel'})
    assert response.status == 200, response

def test_page():
    response = app.get('/a', extra_environ={'REMOTE_USER':'gawel'})
    assert response.status == 200, response
    assert response.status == 000, response

