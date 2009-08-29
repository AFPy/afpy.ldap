# -*- coding: utf-8 -*-
__doc__ = """This module allow to generate forms from :class:`~afpy.ldap.node.Node` with a :mod:`~afpy.ldap.schema`::

    >>> from afpy.ldap import custom as ldap
    >>> user = ldap.getUser('gawel')
    >>> user.uid
    'gawel'
    >>> fs = FieldSet(ldap.AfpyUser)
    >>> fs.configure(include=[fs.uid])
    >>> fs = fs.bind(user)
    >>> print fs.render().strip() #doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <div>
      <label class="field_req" for="AfpyUser-gawel-uid">Login</label>
      <input id="AfpyUser-gawel-uid" name="AfpyUser-gawel-uid" type="text" value="gawel" />
    </div>
    ...

For more informations on how this works look the FormAlchemy_'s documentation.

.. _FormAlchemy: http://docs.formalchemy.org

"""
from formalchemy.forms import FieldSet as BaseFieldSet
from formalchemy.tables import Grid as BaseGrid
from formalchemy.fields import Field as BaseField
from formalchemy.base import SimpleMultiDict
from formalchemy import fields
from formalchemy import validators
from formalchemy import fatypes
from sqlalchemy.util import OrderedDict
import schema
import node

from datetime import datetime


__all__ = ['Field', 'FieldSet']

class Field(BaseField):
    """"""
    def value(self):
        if not self.is_readonly() and self.parent.data is not None:
            v = self._deserialize()
            if v is not None:
                return v
        return getattr(self.model, self.name, None)
    value = property(value)
    def model_value(self):
        return getattr(self.model, self.name, None)
    model_value = raw_value = property(model_value)

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            setattr(self.model, self.name, self._deserialize())

class FieldSet(BaseFieldSet):
    def __init__(self, model, session=None, data=None, prefix=None):
        self._fields = OrderedDict()
        self._render_fields = OrderedDict()
        self.model = self.session = None
        BaseFieldSet.rebind(self, model, data=data)
        self.prefix = prefix
        self.model = model
        self.readonly = False
        self.focus = True
        self._errors = []
        focus = True
        for k, v in model.__dict__.iteritems():
            if isinstance(v, schema.Property):
                type =  v.__class__.__name__.replace('Property','')
                if type == 'Unicode':
                    type = 'String'
                try:
                    t = getattr(fatypes, type)
                except AttributeError:
                    raise NotImplementedError('%s is not mapped to a type' % v.__class__)
                else:
                    self.append(Field(name=k, type=t))
                    self[k].set(label=v.title)
                    if v.description:
                        self[k].set(instruction=v.description)
                    if v.required:
                        self._fields[k].validators.append(validators.required)

    def bind(self, model, session=None, data=None):
        """Bind to an instance"""
        if not (model or session or data):
            raise Exception('must specify at least one of {model, session, data}')
        if not model:
            if not self.model:
                raise Exception('model must be specified when none is already set')
            model = fields._pk(self.model) is None and type(self.model) or self.model
        # copy.copy causes a stacktrace on python 2.5.2/OSX + pylons.  unable to reproduce w/ simpler sample.
        mr = object.__new__(self.__class__)
        mr.__dict__ = dict(self.__dict__)
        # two steps so bind's error checking can work
        mr.rebind(model, session, data)
        mr._fields = OrderedDict([(key, renderer.bind(mr)) for key, renderer in self._fields.iteritems()])
        if self._render_fields:
            mr._render_fields = OrderedDict([(field.key, field) for field in
                                             [field.bind(mr) for field in self._render_fields.itervalues()]])
        return mr

    def rebind(self, model, session=None, data=None):
        if model:
            if not isinstance(model, node.Node):
                try:
                    model = model()
                except:
                    raise Exception('%s appears to be a class, not an instance, but FormAlchemy cannot instantiate it.  (Make sure all constructor parameters are optional!)' % model)
            self.model = model
            self._bound_pk = model.dn and model._pk or None
        if data is None:
            self.data = None
        elif hasattr(data, 'getall') and hasattr(data, 'getone'):
            self.data = data
        else:
            try:
                self.data = SimpleMultiDict(data)
            except:
                raise Exception('unsupported data object %s.  currently only dicts and Paste multidicts are supported' % self.data)

class Grid(BaseGrid, FieldSet):
    def __init__(self, cls, instances=[], session=None, data=None, prefix=None):
        FieldSet.__init__(self, cls, session, data, prefix)
        self.rows = instances
        self.readonly = False
        self._errors = {}

    def _get_errors(self):
        return self._errors

    def _set_errors(self, value):
        self._errors = value
    errors = property(_get_errors, _set_errors)

    def rebind(self, instances=None, session=None, data=None):
        FieldSet.rebind(data=data)
        if instances is not None:
            self.rows = instances

    def _set_active(self, instance, session=None):
        FieldSet.rebind(self, instance, session or self.session, self.data)

def test_fieldset():
    from afpy.ldap import custom as ldap
    user = ldap.getUser('gawel')

    fs = FieldSet(ldap.AfpyUser)
    fs = fs.bind(user)

    # rendering
    assert fs.uid.is_required() == True, fs.uid.is_required()
    assert fs.uid.value == 'gawel'
    html = fs.render()
    assert 'class="field_req" for="AfpyUser-gawel-uid"' in html, html
    assert 'value="gawel"' in html, html

    # syncing
    fs.configure(include=[fs.uid])
    fs.rebind(user, data={'AfpyUser-gawel-uid':'minou'})
    fs.validate()
    fs.sync()
    assert fs.uid.value == 'minou', fs.render_fields
    assert user.uid == 'minou', user.uid

    # grid
    fs = Grid(ldap.AfpyUser, [user, ldap.AfpyUser()])
    html = fs.render()
    assert '<thead>' in html, html
    assert 'value="minou"' in html, html

