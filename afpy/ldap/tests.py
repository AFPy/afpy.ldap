# -*- coding: utf-8 -*-
import unittest
import datetime
import afpy.ldap
import afpy.ldap.utils
from afpy.ldap import custom

ldap = afpy.ldap.Connection(section='afpy')
ldap.bind(custom.User, custom.Group)

def test_datetime_serializer():
    date = afpy.ldap.utils.to_python('20100504122300Z', klass=datetime.datetime)
    assert date.year == 2010, date
    assert date.minute == 23, date

    assert afpy.ldap.utils.to_string(date) == '20100504122300Z'

def test_date_serializer():
    date = afpy.ldap.utils.to_python('20100504122300Z', klass=datetime.date)
    assert date.year == 2010, date

    assert afpy.ldap.utils.to_string(date) == '20100504000000Z'

def test_int_serializer():
    value = afpy.ldap.utils.to_python('2', klass=int)
    assert value == 2

    assert afpy.ldap.utils.to_string(value) == '2'

def test_dn():
    assert ldap.config.tests.base_dn in ldap.base_dn, ldap.base_dn

def test_search():
    results = ldap.search(filter='(uid=gawel)')
    assert len(results) == 1, results

    results = ldap.search_nodes(filter='(uid=gawel)')
    assert len(results) == 1, results

def test_credential():
    user = ldap.get_user(ldap.config.tests.uid)
    assert user.check('toto') is False

def test_normalized_data():
    user = ldap.get_user(ldap.config.tests.uid)
    assert 'objectClass' in user.normalized_data(), (user.dn, user._data)

def test_user():
    user = ldap.get_user(ldap.config.tests.uid)
    assert 'person' in user.objectClass, user._data

    assert user._dn == user.dn, user.dn

    phone = user.homePhone
    user.homePhone = '+34'
    assert ldap.save(user) is True, user.save()

    user = ldap.get_user(ldap.config.tests.uid)
    assert user.homePhone == '+34', user._data

    user.homePhone = phone
    ldap.save(user)

def test_groups():
    user = ldap.get_user(ldap.config.tests.uid)
    assert ldap.config.tests.group in user.groups

    group = ldap.get_group(ldap.config.tests.group)
    assert user.dn in group.member

