# -*- coding: utf-8 -*-
#Copyright (C) 2009 Gael Pasgrimaud
__doc__ = """This module provide a Node class that you can extend
"""
from ldaputil.passwd import UserPassword
import datetime
import utils

class Node(object):

    _defaults = {}
    _field_types = {}

    def __init__(self, uid=None, dn=None, conn=None, attrs={}):
        self._conn = conn
        if dn:
            self._dn = dn
        elif uid and '=' in uid:
            self._dn = uid
        elif uid and conn:
            self._dn = self._conn.uid2dn(uid)
        else:
            raise ValueError('You must provide an uid or dn')
        if '=' not in self._dn:
            raise ValueError('Invalid dn %s' % self._dn)
        if attrs:
            self._data = self._defaults.copy()
            for k, v in attrs.items():
                if isinstance(v, (list, tuple)) and len(v) == 1:
                    v = v[0]
                self._data[k] = utils.to_string(v)
        else:
            self._data = None
        self._new_data = {}

    def bind(self, conn):
        """rebind node to conn"""
        self._conn = conn

    def normalized_data(self):
        """return ldap datas as dict"""
        if self._data:
            return self._data
        self._data = {}
        data = self._conn.get_dn(self._dn)
        results = data.get('results', {})
        if len(results) == 1:
            for k, v in results[0].items():
                if len(v) == 1:
                    v = v[0]
                self._data[k] = v

        return self._data

    def get(self, attr, default=None):
        """get a node attribute"""
        value = self.normalized_data().get(attr, default)
        type = self._field_types.get(attr, None)
        if type:
            return utils.to_python(value, type)
        return value

    def __getattr__(self, attr):
        """get a node attribute"""
        try:
            value = self.normalized_data()[attr]
        except KeyError:
            raise AttributeError('%r as no attribute %s' % (self, attr))
        type = self._field_types.get(attr, None)
        if type:
            return utils.to_python(value, type)
        return value

    def __setattr__(self, attr, value):
        """set a node attribute"""
        if attr.startswith('_'):
            object.__setattr__(self, attr, value)
        else:
            data = self.normalized_data()
            data[attr] = utils.to_string(value)
            self._new_data[attr] = value

    def __eq__(self, node):
        return node._dn == self._dn

    def __ne__(self, node):
        return node._dn != self._dn

    def __str__(self):
        return self._dn.split(',', 1)[0].split('=')[1]

    def __repr__(self):
        return '<%s at %s>' % (self.__class__.__name__, self._dn)

class GroupOfNames(Node):
    @property
    def member_nodes(self):
        """return group members as nodes"""
        members = [self._conn.node_class(dn=m) for m in self.member]

class User(Node):

    def check(self, password):
        """check credential by binding a new connection"""
        return self._conn.check(self._dn, password)

    def change_password(self, passwd, scheme='ssha', charset='utf-8', multiple=0):
        """allow to change password"""
        password = UserPassword(self._conn._conn.connect(), self._dn, charset=charset, multiple=multiple)
        password.changePassword(None, passwd, scheme)

    @property
    def groups(self):
        """return groups as string"""
        groups = self._conn.get_groups(self._dn)
        return [str(g) for g in groups]

    @property
    def groups_nodes(self):
        """return  groups as nodes"""
        return self._conn.get_groups(self._dn)

