# -*- coding: utf-8 -*-
__doc__ = """You can map your :class:`~afpy.ldap.node.Node` properties::

    >>> from afpy.ldap import node
    >>> class MyUser(node.Node):
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

    def __get__(self, instance, klass):
        return getattr(instance, '_%s' % self.name)

    def __set__(self, instance, value):
        setattr(instance, '_%s' % self.name, value)

class Dn(Attribute):
    """Used to generate dn on new objects. The :class:`~afpy.ldap.node.Node` class already got one::

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
        if not instance._dn:
            if instance._rdn and instance._base_dn:
                value = getattr(instance, instance._rdn, None)
                if value:
                    instance._dn = '%s=%s,%s' % (instance._rdn, value, instance._base_dn)
        if instance._dn and not instance._pk:
            instance._pk = instance._dn and instance._dn.split(',', 1)[0].split('=')[1] or None
        return instance._dn

class Property(property):
    klass = str

    def __init__(self, name, title=None, description='', required=False):
        self.name = name
        self.title = title or name
        self.description = description
        self.required = required

    def __get__(self, instance, klass):
        data = instance.normalized_data()
        value = data.get(self.name)
        return utils.to_python(value, self.klass)

    def __set__(self, instance, value):
        value = utils.to_string(value)
        data = instance.normalized_data()
        data[self.name] = value

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

