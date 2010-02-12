# -*- coding: utf-8 -*-
#Copyright (C) 2009 Gael Pasgrimaud
__doc__ = """This module provide a Node class that you can extend
"""
from ldaputil.passwd import UserPassword
import datetime
import utils
import schema

class Node(object):
    """A ldap node::

        >>> node = Node('uid=gawel,dc=afpy,dc=org')
        >>> print node._dn
        uid=gawel,dc=afpy,dc=org

    """
    _sa_instance_state = True
    _rdn = None
    _base_dn = None
    _defaults = {}
    _field_types = {}

    dn = schema.Dn('dn')
    rdn = schema.Attribute('rdn')
    base_dn = schema.Attribute('base_dn')
    conn = schema.Attribute('conn')

    def __init__(self, uid=None, dn=None, conn=None, attrs=None):
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
        elif uid and self._base_dn and self._rdn:
            self._dn = '%s=%s,%s' % (self._rdn, uid, self._base_dn)
        pk = self._dn and self._dn.split(',', 1)[0].split('=')[1] or None
        self._pk = pk and pk.lower() or None

    @classmethod
    def search(cls, conn, **kwargs):
        options = dict(
            base_dn=cls._base_dn,
            filter='(objectClass=*)',
            )
        options.update(kwargs)
        return conn.search_nodes(**kwargs)

    @classmethod
    def from_config(cls, config, section):
        """Generate a class from ConfigObject. This is an easy way to subclass Node and define schema.

        Let' create a config object (you may use a file in real life)::

            >>> from ConfigObject import ConfigObject
            >>> config = ConfigObject()
            >>> config.afpy_user = dict(
            ...                        rdn='uid',
            ...                        base_dn='ou=members,dc=afpy,dc=org')
            >>> config.afpy_user.objectclass = ['top', 'person','associationMember',
            ...                       'organizationalPerson', 'inetOrgPerson'],
            >>> config.afpy_user.properties=['name=birthDate, type=date, title= Date de naissance, required=true']
            >>> config.afpy_user.base_class='afpy.ldap.testing:ExtendedNode'

        Generate the new class::

            >>> klass = Node.from_config(config, 'afpy_user')
            >>> klass
            <class 'afpy.ldap.node.AfpyUser'>

        All is ok::

            >>> klass.__dict__['birthDate'] #doctest: +ELLIPSIS
            <afpy.ldap.schema.DateProperty object at ...>

        We can import and use it::

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
        if self._conn and self._dn:
            self._conn.save(self)
        else:
            raise RuntimeError('%r is not bind to a connection' % self)

    def append(self, node, save=True):
        if self.dn:
            if node._rdn:
                value = utils.to_string(getattr(node, node._rdn))
                node._dn = '%s=%s,%s' % (node._rdn, value, self.dn)
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
        if attr.startswith('_'):
            object.__setattr__(self, attr, value)
        else:
            data = self.normalized_data()
            data[attr] = utils.to_string(value)

    def __delattr__(self, attr):
        """del a node attribute"""
        if attr.startswith('_'):
            object.__delattr__(self, attr)
        else:
            data = self.normalized_data()
            if attr in data:
                del data[attr]

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

