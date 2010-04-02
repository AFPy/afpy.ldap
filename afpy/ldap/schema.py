# -*- coding: utf-8 -*-
__doc__ = """You can map your :class:`~afpy.ldap.node.Node` properties::

    >>> from afpy.ldap import node
    >>> class MyUser(node.Node):
    ...     _rdn = 'uid'
    ...     _base_dn = 'ou=members,dc=afpy,dc=org'
    ...     uid = StringProperty('uid', title='login', required=True)
    ...     birthDate = DateProperty('birthDate', title='login', required=True)
    >>> from afpy.ldap import custom as ldap
    >>> conn = ldap.get_conn()

Get a node with this class::

    >>> user = conn.get_user('gawel', node_class=MyUser)
    >>> user
    <MyUser at uid=gawel,ou=members,dc=afpy,dc=org>

The `birthDate` is stored as string but converted to date when you access it
via the property::

    >>> user.get('birthDate')
    '19750410000000Z'
    >>> user.birthDate
    datetime.date(1975, 4, 10)

No validation is done at schema level. The title and required parameters are
used for :mod:`afpy.ldap.forms` generation.
"""


import utils, datetime

class Attribute(property):
    """An attribute not showed in forms"""

    def __init__(self, name):
        self.name = name
        self.__doc__ = ':class:`~afpy.ldap.schema.%s` for ``_%s``' % (self.__class__.__name__, name)

    def __get__(self, instance, klass):
        if instance is None:
            return getattr(klass, '_%s' % self.name, self)
        else:
            return getattr(instance, '_%s' % self.name, self)

    def __set__(self, instance, value):
        setattr(instance.__class__, '_%s' % self.name, value)

class ReadonlyAttribute(property):

    def __init__(self, name):
        self.name = name
        self.__doc__ = ':class:`~afpy.ldap.schema.%s` for ``_%s``' % (self.__class__.__name__, name)

    def __get__(self, instance, klass):
        if instance is None:
            return getattr(klass, '_%s' % self.name, self)
        else:
            return getattr(instance, '_%s' % self.name, self)

class Dn(Attribute):
    """Used to generate dn on new objects. The :class:`~afpy.ldap.node.Node` class already got one:

    .. sourcecode:: py

        >>> from afpy.ldap import node
        >>> class MyUser(node.Node):
        ...     _rdn = 'uid'
        ...     _base_dn = 'ou=members,dc=afpy,dc=org'
        >>> user = MyUser()
        >>> user.uid = 'gawel'
        >>> user.dn
        'uid=gawel,ou=members,dc=afpy,dc=org'

    """

    def __get__(self, instance, klass):
        if instance is None:
            return self
        if not instance._dn:
            if instance._rdn and instance._base_dn:
                try:
                    value = getattr(instance, instance._rdn, None)
                except ValueError:
                    return None
                if value:
                    instance._dn = '%s=%s,%s' % (instance._rdn, value, instance._base_dn)
        if instance._dn and not instance._pk:
            instance._pk = instance._dn and instance._dn.split(',', 1)[0].split('=')[1] or None
        return instance._dn

    def __set__(self, instance, value):
        setattr(instance, '_%s' % self.name, value)

class Property(property):
    klass = str
    count = 0

    def __init__(self, name, title=None, description='', required=False):
        self.name = name
        self.title = title or name.title()
        self.description = description
        self.required = required
        Property.count += 1
        self.order = Property.count
        self.__doc__ = ':class:`~afpy.ldap.schema.%s` for ldap field ``%s``' % (self.__class__.__name__, name)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        try:
            data = instance.normalized_data()
        except ValueError:
            # new node
            return ''
        value = data.get(self.name)
        return utils.to_python(value, self.klass)

    def __set__(self, instance, value):
        data = instance.normalized_data()
        if value is None:
            data[self.name] = []
        else:
            data[self.name] = utils.to_string(value)

    def __delete__(self, instance):
        data = instance.normalized_data()
        data[self.name] = []

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)

class UnicodeProperty(Property):
    klass = unicode

class StringProperty(Property):
    klass = str

class DateProperty(Property):
    klass = datetime.date

class DateTimeProperty(Property):
    klass = datetime.datetime

class IntegerProperty(Property):
    klass = int

class ListProperty(Property):
    klass = list
    item_class = basestring

    def _to_python(self, value, instance=None):
        return self.klass(value)

    def _to_ldap(self, value, instance=None):
        return list(value)

    def __get__(self, instance, klass):
        if instance is None:
            return self
        data = instance.normalized_data()
        value = data.get(self.name)
        if not value:
            value = []
        elif isinstance(value, basestring):
            value = [value]
        return self._to_python(value, instance)

    def __set__(self, instance, value):
        data = instance.normalized_data()
        if value is None:
            value = self.klass()
        elif not isinstance(value, self.klass):
            raise TypeError('Value for %s must by %s not %s. Got %s' % (self.name, self.klass, type(value), value))
        for i in value:
            if not isinstance(i, self.item_class):
                raise TypeError('All items of %s must by %s not %s' % (self.name, self.item_class, type(i)))
        data[self.name] = self._to_ldap(value, instance)

class SetProperty(ListProperty):
    klass = set

class SetOfNodesProperty(SetProperty):
    item_class = None

    def __init__(self, name, title, required=False, node_class=None):
        SetProperty.__init__(self, name, title, required)
        if node_class is None:
            raise TypeError('node_class is required for %s property' % self.__class__.__name__)
        self.item_class = node_class
        self.__doc__ = ':class:`~afpy.ldap.schema.%s` for ldap field ``%s``. Contains ``%s`` objects' % (self.__class__.__name__, name, node_class.__name__)

    def _to_python(self, value, instance=None):
        if instance.conn:
            value = self.klass(value or [])
            return self.klass([self.item_class(dn=v, conn=instance.conn) for v in value])
        else:
            return self.klass()

    def _to_ldap(self, value, instance=None):
        return list([v.dn for v in value])

class ListOfGroupNodesProperty(ListProperty):
    _item_class = 'group'

    def __init__(self, name, title, required=False):
        ListProperty.__init__(self, name, title, required)
        self.__doc__ = ':class:`~afpy.ldap.schema.%s` for ldap field ``%s``. Contains ``%s`` objects' % (
                                self.__class__.__name__, name, self._item_class.title())

    def item_class(self, instance):
        return getattr(instance.conn, '%s_class' % self._item_class)

    def get_instances(self, instance):
        value = []
        item_class = self.item_class(instance)
        if instance.conn and item_class.base_dn:
            value = instance.conn.get_groups(instance._dn,
                                             base_dn=item_class.base_dn,
                                             node_class=item_class)
        return value

    def __get__(self, instance, klass):
        if instance is None:
            return self
        if not instance.conn:
            return self.klass()
        return self._to_python(self.get_instances(instance))

    def __set__(self, instance, value):
        if value is None:
            value = self.klass()
        elif not isinstance(value, self.klass):
            raise TypeError('Value for %s must by %s not %s' % (self.name, self.klass, type(value)))
        item_class = self.item_class(instance)
        for i in value:
            if not isinstance(i, item_class):
                raise TypeError('All items of %s must by %s not %s' % (self.name, item_class, type(i)))
        self._to_ldap(value, instance)

    def _to_python(self, value, instance=None):
        return self.klass(value)

    def _to_ldap(self, value, instance=None):
        dn = instance.dn
        groups = self.get_instances(instance)
        groups = dict([(getattr(g, g.rdn), g) for g in groups])
        new_groups = dict([(getattr(g, g.rdn), g) for g in value])
        all_groups = set(new_groups.keys()+groups.keys())
        for v in all_groups:
            if v in new_groups and v not in groups:
                g = new_groups[v]
                member = g.member
                member.add(dn)
                g.member = member
                g.save()
            elif v not in new_groups and v in groups:
                g = groups[v]
                member = g.member
                member.remove(dn)
                g.member = member
                g.save()

class ListOfGroupsProperty(ListOfGroupNodesProperty):

    def __set__(self, instance, value):
        new_value = self.klass()
        if value:
            item_class = self.item_class(instance)
            new_value = []
            for v in set(value):
                dn = item_class.build_dn(v)
                new_value.append(item_class(dn=dn, conn=instance.conn))
            new_value = self.klass(new_value)
        ListOfGroupNodesProperty.__set__(self, instance, new_value)

    def _to_python(self, value, instance=None):
        return self.klass([getattr(v, v.rdn) for v in value])


class ListOfPermNodesProperty(ListOfGroupNodesProperty):
    _item_class = 'perm'

class ListOfPermsProperty(ListOfGroupsProperty):
    _item_class = 'perm'

