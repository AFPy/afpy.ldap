# -*- coding: utf-8 -*-
import datetime
import utils

class Node(object):

    _field_types = {}

    def __init__(self, uid=None, dn=None, conn=None, attrs={}):
        self._conn = conn or get_conn()
        if dn:
            self._dn = dn
        elif uid and '=' in uid:
            self._dn = uid
        elif uid:
            self._dn = self._conn.uid2dn(uid)
        else:
            raise ValueError('You must provide an uid or dn')
        if '=' not in self._dn:
            raise ValueError('Invalid dn %s' % self._dn)
        if attrs and 'dn' in attrs:
            self._data = attrs
        else:
            self._data = None
        self._new_data = {}

    def bind(self, conn):
        self._conn = conn

    def check(self, password):
        return self._conn.check(self._dn, password)

    def normalized_data(self):
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

    def save(self):
        if self._data and 'dn' in self._data:
            data = self._new_data.copy()
            try:
                self._conn._conn.modify(self._dn, attrs=data)
            except Exception, e:
                return e
            else:
                self._data = None
                self._new_data = {}
                return True

    @property
    def groups(self):
        groups = self._conn.get_groups(self._dn)
        return [str(g) for g in groups]

    @property
    def groups_nodes(self):
        return self._conn.get_groups(self._dn)

    @property
    def member_nodes(self):
        members = [self._conn.node_class(dn=m) for m in self.member]

    def __getattr__(self, attr):
        try:
            value = self.normalized_data()[attr]
        except KeyError:
            raise AttributeError('%r as no attribute %s' % (self, attr))
        type = self._field_types.get(attr, None)
        if type:
            return utils.to_python(value)
        return value


    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            object.__setattr__(self, attr, value)
        else:
            data = self.normalized_data()
            data[attr] = utils.to_string(value)
            self._new_data[attr] = value

    def __str__(self):
        return self._dn.split(',', 1)[0].split('=')[1]

    def __repr__(self):
        return '<Node at %s>' % self._dn

