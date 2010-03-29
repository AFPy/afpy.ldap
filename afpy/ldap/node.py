# -*- coding: utf-8 -*-
#Copyright (C) 2009 Gael Pasgrimaud
__doc__ = """This module provide a Node class that you can extend
"""
from ldaputil.passwd import UserPassword
import datetime
import schema
import ldap
import string
import utils
import sys


class Node(object):
    """A LDAP node. Base class for all LDAP objects:

    .. sourcecode:: py

        >>> node = Node('uid=gawel,dc=afpy,dc=org')
        >>> print node.dn
        uid=gawel,dc=afpy,dc=org

    """
    _sa_instance_state = True
    _conn = None
    _rdn = None
    _base_dn = None
    _defaults = {}
    _field_types = {}

    dn = schema.Dn('dn')
    rdn = schema.ReadonlyAttribute('rdn')
    base_dn = schema.ReadonlyAttribute('base_dn')
    conn = schema.ReadonlyAttribute('conn')
    data = schema.ReadonlyAttribute('data')

    def __init__(self, uid=None, dn=None, conn=None, attrs=None):
        object.__init__(self)
        if conn and not self._conn:
            self._conn = conn
        self._dn = None
        self._update_dn(uid=uid, dn=dn)
        if attrs:
            self._data = self._defaults.copy()
            for k, v in attrs.items():
                if isinstance(v, (list, tuple)) and len(v) == 1:
                    v = v[0]
                self._data[k] = utils.to_string(v)
        elif attrs is not None:
            self._data = attrs
        else:
            self._data = None

    def _update_dn(self, uid, dn=None):
        if dn:
            self._dn = dn
        elif uid and '=' in uid:
            self._dn = uid
        elif uid and self.base_dn and self.rdn:
            self._dn = '%s=%s,%s' % (self.rdn, uid, self.base_dn)
        pk = self._dn and self._dn.split(',', 1)[0].split('=')[1] or None
        self._pk = pk and pk.lower() or None

    @classmethod
    def properties(cls_):
        props = []
        props_names = []
        for cls in cls_.mro():
            for k, v in cls.__dict__.items():
                if k not in props_names and isinstance(v, schema.Property):
                    props.append((k, v))
                    props_names.append(k)
        def cmp_prop(a, b):
            return cmp(a[1].order, b[1].order)
        props.sort(cmp=cmp_prop)
        return props

    @classmethod
    def search(cls, conn=None, filter='(objectClass=*)', **kwargs):
        """search class nodes"""
        options = dict(
            base_dn=cls.base_dn,
            filter=filter,
            )
        options.update(kwargs)
        conn = conn or cls.conn
        return conn.search_nodes(node_class=cls, **options)

    @classmethod
    def unlimited_search(cls, filter='', conn=None, **kwargs):
        """same as search but handle SIZELIMIT_EXCEEDED errors"""
        conn = conn or cls.conn
        if not filter.startswith('('):
            filter = '(%s)' % filter
        try:
            return cls.search(cls.conn, filter=filter)
        except ldap.SIZELIMIT_EXCEEDED:
            pass
        results = []
        for l in string.ascii_lowercase:
            try:
                results.extend(
                   cls.search(filter='(&(%s=%s%s*)%s)' % (cls.rdn, f, l, filter), conn=conn)
                   )
            except ldap.SIZELIMIT_EXCEEDED:
                pass
        return results

    def bind(self, conn):
        """rebind instance to conn"""
        self._conn = conn

    def save(self):
        """save node"""
        conn = self._conn or self.conn
        if conn and self._dn:
            try:
                conn.save(self)
            except ldap.NO_SUCH_OBJECT:
                conn.add(self)
        else:
            raise RuntimeError('%r is not bind to a connection' % self)

    def append(self, node, save=True):
        """append a subnode"""
        if self.dn:
            if node.rdn:
                value = utils.to_string(getattr(node, node.rdn))
                node._dn = '%s=%s,%s' % (node.rdn, value, self.dn)
                node.bind(self._conn)
                if save:
                    try:
                        self._conn.get_dn(node.dn)
                    except ValueError:
                        self._conn.add(node)
                    else:
                        self._conn.save(node)
            else:
                raise ValueError('%r need a _rdn attr' % node)
        else:
            raise AttributeError('%r is not bound to a connection' % self)

    def normalized_data(self):
        if self._data:
            return self._data
        if not self._conn:
            # new instance. node to store data tought
            self._data = {}
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
        if attr.startswith('_') or \
           isinstance(getattr(self.__class__, attr, None), property):
            object.__setattr__(self, attr, value)
        else:
            data = self.normalized_data()
            if value is None:
                value = []
            else:
                value = utils.to_string(value)
            data[attr] = value

    def __delattr__(self, attr):
        """del a node attribute"""
        if attr.startswith('_'):
            object.__delattr__(self, attr)
        else:
            data = self.normalized_data()
            if attr in data:
                data[attr] = []

    def __eq__(self, node):
        return node._dn == self._dn

    def __ne__(self, node):
        return node._dn != self._dn

    def __str__(self):
        return getattr(self, self.rdn)

    def __unicode__(self):
        return unicode(getattr(self, self.rdn))

    def __repr__(self):
        return '<%s at %s>' % (self.__class__.__name__, self.dn)

    def pprint(self, encoding=utils.DEFAULT_ENCODING, show_dn=True):
        """pretty print"""
        out = []
        out.append(self.cn)
        out.append('-'*len(self.cn))
        if show_dn:
            out.append('%-15.15s : %s' % ('dn', self.dn))
        def enc(v):
            if isinstance(v, unicode):
                return v.encode(encoding, 'replace')
            return v
        for k, v in self.properties():
            value = getattr(self, k, None)
            if value:
                title = v.title
                out.append('%-15.15s : %s' % (enc(title), enc(value)))
        return '\n'.join(out)


class User(Node):
    """base class for user nodes"""

    def check(self, password):
        """check credential by binding a new connection"""
        if password:
            return self._conn.check(self.dn, password)

    def change_password(self, passwd, scheme='ssha', charset='utf-8', multiple=0):
        """allow to change password"""
        if passwd:
            password = UserPassword(self._conn._conn.connect(),
                                    self._dn, charset=charset,
                                    multiple=multiple)
            password.changePassword(None, passwd, scheme)

    @property
    def groups(self):
        """return groups as string"""
        groups = self._conn.get_groups(self._dn)
        return [getattr(g, g.rdn) for g in groups]

    @property
    def groups_nodes(self):
        """return  groups as nodes"""
        return self._conn.get_groups(self._dn)


class GroupOfNames(Node):
    """base class for group nodes"""
    _rdn = 'cn'
    _memberAttr = 'member'
    _defaults = {'objectClass': ['groupOfNames', 'top']}

    member = schema.SetProperty('member', title='Members')
    member_nodes = schema.SetOfNodesProperty('member', title='Members', node_class=User)

    def __repr__(self):
        return '<%s at %s (%s members)>' % (self.__class__.__name__,
                                    self.dn, len(self.member))
    def pprint(self):
        out = []
        out.append(self.cn)
        out.append('-'*len(self.cn))
        users = self.member_nodes
        for u in users:
            out.append(getattr(u, u.rdn))
        return '\n'.join(out)


class GroupOfUniqueNames(GroupOfNames):
    """groupOfUniqueNames implementation"""
    _rdn = 'cn'
    _memberAttr = 'uniqueMember'
    _defaults = {'objectClass': ['groupOfUniqueNames', 'top']}

    member = schema.SetProperty('uniqueMember', title='Members')
    member_nodes = schema.SetOfNodesProperty('uniqueMember', title='Members', node_class=User)


class OrganizationalUnit(Node):
    """base class for Organizational Unit nodes"""
    _rdn = 'ou'
    _defaults = {'objectClass': ['organizationalUnit', 'top']}
    ou = schema.StringProperty('ou', required=True)

