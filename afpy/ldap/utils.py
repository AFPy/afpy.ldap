# -*- coding: utf-8 -*-
import datetime

class DateSerializer(object):
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

class DateTimeSerializer(DateSerializer):
    klass = datetime.datetime
    _range_index = 11

class IntSerializer(object):
    klass = int

    @classmethod
    def to_python(cls, value):
        if value:
            try:
                return int(value)
            except Exception, e:
                raise e.__class__('%s (%s)' % (str(e), value))

    @classmethod
    def to_string(cls, value):
        return str(value)

_serializers = (DateTimeSerializer, DateSerializer, IntSerializer)

def to_string(value):
    if value:
        for serializer in _serializers:
            if isinstance(value, serializer.klass):
                return serializer.to_string(value)
    if not isinstance(value, basestring):
        raise TypeError('%r is not serializable' % value)
    return value

def to_python(value, klass):
    if value:
        for serializer in _serializers:
            if klass is serializer.klass:
                return serializer.to_python(value)
    return value
