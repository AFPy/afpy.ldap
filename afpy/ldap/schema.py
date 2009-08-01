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

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, klass):
        return getattr(instance, '_%s' % self.name)

    def __set__(self, instance, value):
        setattr(instance, '_%s' % self.name, value)

class Dn(Attribute):

    def __set__(self, instance, value):
        if value and '=' in value:
            self._dn = value
        elif value and instance._conn:
            self._dn = self._conn.uid2dn(uid)
        else:
            self._dn = None
        instance._pk = value and self._dn.split(',', 1)[0].split('=')[1] or None

class Property(property):
    klass = str

    def __init__(self, name, title=None, required=False):
        self.name = name
        self.title = title or name
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

