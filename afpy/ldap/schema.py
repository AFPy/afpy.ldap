# -*- coding: utf-8 -*-
import utils, datetime

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
        value = utils.to_string(value, instance.klass)
        data = instance.normalized_data()
        data[self.name] = value

class StringProperty(Property):
    klass = str

class DateProperty(Property):
    klass = datetime.date

class DateTimeProperty(Property):
    klass = datetime.datetime

class IntegerProperty(Property):
    klass = datetime.date

