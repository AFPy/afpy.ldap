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
    """A ldap node:

    .. sourcecode:: py

        >>> node = Node('uid=gawel,dc=afpy,dc=org')
        >>> print node._dn
        uid=gawel,dc=afpy,dc=org

    """
    _sa_instance_state = True
    _conn = None
    _rdn = None
    _base_dn = None
    _defaults = {}
    _field_types = {}

    dn = schema.Dn('dn')
    rdn = schema.Attribute('rdn')
    base_dn = schema.Attribute('base_dn')
    conn = schema.Attribute('conn')
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
    def search(cls, conn=None, **kwargs):
        options = dict(
            base_dn=cls.base_dn,
            filter='(objectClass=*)',
            )
        options.update(kwargs)
        conn = conn or cls.conn
        return conn.search_nodes(node_class=cls, **options)

    @classmethod
    def unlimited_search(cls, filter='', f='', results=None):
        if not filter.startswith('('):
            filter = '(%s)' % filter
        if results is None:
            results = []
        if not f:
            try:
                return cls.search(cls.conn, filter=filter)
            except ldap.SIZELIMIT_EXCEEDED:
                pass
        for l in string.ascii_lowercase:
            try:
                results.extend(
                   cls.search(cls.conn, filter='(&(%s=%s%s*)%s)' % (cls.rdn, f, l, filter))
                   )
            except ldap.SIZELIMIT_EXCEEDED:
                pass
        return results

    @classmethod
    def from_config(cls, config, section):
        """Generate a class from ConfigObject. This is an easy way to subclass Node and define schema.

        Let' create a config object (you may use a file in real life):

        .. sourcecode:: py

            >>> from ConfigObject import ConfigObject
            >>> config = ConfigObject()
            >>> config.afpy_user = dict(
            ...                        rdn='uid',
            ...                        base_dn='ou=members,dc=afpy,dc=org')
            >>> config.afpy_user.objectclass = ['top', 'person','associationMember',
            ...                       'organizationalPerson', 'inetOrgPerson'],
            >>> config.afpy_user.properties=['name=birthDate, type=date, title= Date de naissance, required=true']
            >>> config.afpy_user.base_class='afpy.ldap.testing:ExtendedNode'

        Generate the new class:

        .. sourcecode:: py

            >>> klass = Node.from_config(config, 'afpy_user')
            >>> klass
            <class 'afpy.ldap.node.AfpyUser'>

        All is ok:

        .. sourcecode:

            >>> klass.birthDate
            <DateProperty 'birthDate'>

        We can import and use it:

        .. sourcecode:: py

            >>> from afpy.ldap.testing import AfpyUser
            >>> isinstance(AfpyUser(), Node)
            True
            >>> AfpyUser().extended()
            True
        """
        options = config[section]
        name = section.split(':')[0].replace('_', ' ').title().replace(' ', '')
        rdn = options.rdn
        base_dn = options.base_dn
        defaults = {}
        attrs = {}
        defaults['objectClass'] = options.objectclass.as_list()
        for prop in options.properties.as_list(sep='\n'):
            args = [p.split('=') for p in prop.split(',')]
            args = dict([(k.strip(), v.strip()) for k, v in args])
            pname = args['name']
            ptype = args.get('type', 'string')
            ptitle = args.get('title', None)
            prequired = args.get('required', False)
            prequired = prequired == 'true' and True or False
            attrs[pname] = getattr(schema, '%sProperty' % ptype.title())(pname, ptitle, prequired)
        attrs.update(_rdn=rdn, _base_dn=base_dn,
                     __doc__='Generated class %s' % section.title())
        klass = None
        if options.base_class:
            mod, klass = options.base_class.split(':')
            module = __import__(mod, globals(), locals(), [''])
            klass = getattr(module, klass)
        klasses = klass and (cls, klass,) or (cls,)
        new_class = type(name, klasses, attrs)
        if klass:
            module.__dict__[new_class.__name__] = new_class
            return getattr(module, new_class.__name__)
        return new_class

    def bind(self, conn):
        """rebind node to conn"""
        self._conn = conn

    @classmethod
    def get_node(cls, conn, uid):
        if '=' in uid:
            dn = uid
        else:
            dn = '%s=%s,%s' % (cls._rdn, uid, cls._base_dn)
        return conn.get_node(dn, node_class=cls)

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
        """return ldap datas as dict"""
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
        return [getattr(g, g.rdn) for g in groups]

    @property
    def groups_nodes(self):
        """return  groups as nodes"""
        return self._conn.get_groups(self._dn)

class GroupOfNames(Node):
    _rdn = 'cn'

    member = schema.SetProperty('member', title='Members')
    member_nodes = schema.SetOfNodesProperty('member', title='Members', node_class=User)

    def __repr__(self):
        return '<%s at %s (%s members)>' % (self.__class__.__name__,
                                    self.dn, len(self._data.get('member', [])))
    def pprint(self):
        out = []
        out.append(self.cn)
        out.append('-'*len(self.cn))
        users = self.member_nodes
        for u in users:
            out.append(getattr(u, u.rdn))
        return '\n'.join(out)

class OrganizationalUnit(Node):
    _rdn = 'ou'
    _defaults = {'objectClass': ['organizationalUnit', 'top']}
    ou = schema.StringProperty('ou', required=True)

