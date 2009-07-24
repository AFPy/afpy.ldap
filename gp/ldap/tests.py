# -*- coding: utf-8 -*-
import unittest
import gp.ldap
import gp.ldap.wsgi
from webtest import TestApp

ldap = gp.ldap.LDAP()


def test_dn():
    assert ldap.config.tests.base_dn in ldap.base_dn, ldap.base_dn

def test_search():
    results = ldap.search(filter='(uid=gawel)')
    assert results['size'] == 1, results

def test_credential():
    user = ldap.get_node(ldap.config.tests.uid)
    assert user.check('toto') is False

def test_normalized_data():
    user = ldap.get_node(ldap.config.tests.uid)
    assert 'objectClass' in user.normalized_data(), (user.dn, user._data)

def test_user():
    user = ldap.get_node(ldap.config.tests.uid)
    assert 'person' in user.objectClass

    assert user._dn == user.dn, user.dn

    phone = user.homePhone
    user.homePhone = '+34'
    user.save()

    user = ldap.get_node(ldap.config.tests.uid)
    assert user.homePhone == '+34', user._data

    user.homePhone = phone
    user.save()

def test_groups():
    user = ldap.get_node(ldap.config.tests.uid)
    assert ldap.config.tests.group in user.groups

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

