# -*- coding: utf-8 -*-
import unittest
import gp.ldap
import gp.ldap.wsgi
from webtest import TestApp

ldap = gp.ldap.LDAP()

user = gp.ldap.User('gawel')

def test_dn():
    assert 'dc=gawel,dc=org' in ldap.base_dn, ldap.base_dn

def test_search():
    results = ldap.search(filter='(uid=gawel)')
    assert results['size'] == 1, results

def test_credential():
    assert user.check('toto') is False

def test_normalized_data():
    assert 'objectClass' in user.normalized_data(), (user.dn, user._data)

def test_user():
    assert 'person' in user.objectClass

    assert user._dn == user.dn, user.dn

    phone = '+33144530555'
    user.homePhone = '+34'
    user.save()
    assert user.homePhone == '+34', user._data


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
    assert response.status == '200 OK', response

def test_page():
    response = app.get('/a', extra_environ={'REMOTE_USER':'gawel'})
    assert response.status == '200 OK', response

