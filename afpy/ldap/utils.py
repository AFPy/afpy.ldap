# -*- coding: utf-8 -*-
import datetime
import sys

DEFAULT_ENCODING = getattr(sys.stdout, 'encoding', 'utf-8')

_serializers = []

def resolve_class(entry_point):
    """Resolve a dotted name:

    .. sourcecode:: py

        >>> resolve_class('afpy.ldap.custom:User')
        <class 'afpy.ldap.custom.User'>

    """
    mode_name, class_name = entry_point.split(':')
    mod = __import__(mode_name, globals(), locals(), [class_name], -1)
    return getattr(mod, class_name)

def register_serializer(klass):
    """add a new serializer to the list
    """
    for attr in ('to_python', 'to_string', 'klass'):
        if not hasattr(klass, attr):
            raise AttributeError('%s as not attribute %s' % (klass, attr))
    _serializers.insert(0, klass)

class BaseSerializer(object):
    klass = str
    @classmethod
    def to_python(cls, value):
        """convert string to python object"""
        return value

    @classmethod
    def to_string(cls, value):
        """convert string to python object"""
        return value
register_serializer(BaseSerializer)

class UnicodeSerializer(object):
    klass = unicode
    encodings = ['utf-8', 'iso-8859-1']
    @classmethod
    def to_python(cls, value):
        """convert string to python object"""
        for encoding in cls.encodings + [DEFAULT_ENCODING]:
            try:
                return value.decode(encoding)
            except Exception, e:
                pass
        raise

    @classmethod
    def to_string(cls, value):
        """convert string to python object"""
        for encoding in cls.encodings + [DEFAULT_ENCODING]:
            try:
                return value.encode(encoding)
            except Exception, e:
                pass
        raise
register_serializer(UnicodeSerializer)

class DateSerializer(BaseSerializer):
    klass = datetime.date
    _range_index = 7

    @classmethod
    def to_python(cls, value):
        if value:
            try:
                if len(value) >= 8:
                    args = [int(value[0:4])]
                    for i in range(4, cls._range_index, 2):
                        args.append(int(value[i:i+2]))
                    date = cls.klass(*args)
                    return date
            except Exception, e:
                raise e.__class__('%s (%s)' % (str(e), value))

    @classmethod
    def to_string(cls, value):
        if isinstance(value, cls.klass):
            return value.strftime('%Y%m%d%H%M00Z')
register_serializer(DateSerializer)

class DateTimeSerializer(DateSerializer):
    klass = datetime.datetime
    _range_index = 11
register_serializer(DateTimeSerializer)

class IntSerializer(BaseSerializer):
    klass = int

    @classmethod
    def to_python(cls, value):
        if isinstance(value, basestring) and value.isdigit():
            try:
                return int(value)
            except Exception, e:
                raise e.__class__('%s (%s)' % (str(e), value))

    @classmethod
    def to_string(cls, value):
        return str(value)
register_serializer(IntSerializer)

class ListSerializer(BaseSerializer):
    klass=list
    @classmethod
    def to_python(cls, value):
        return value
    @classmethod
    def to_string(cls, value):
        return [to_string(v) for v in value]
register_serializer(ListSerializer)

def to_string(value):
    """serialize a python object to string"""
    if value is None:
        return None
    if not isinstance(value, basestring):
        for serializer in _serializers:
            if isinstance(value, serializer.klass):
                return serializer.to_string(value)
    if not isinstance(value, basestring):
        raise TypeError('%r is not serializable' % value)
    return value

def to_python(value, klass):
    """convert a string to python"""
    if value:
        for serializer in _serializers:
            if klass is serializer.klass:
                return serializer.to_python(value)
    return value
