# -*- coding: utf-8 -*-
__doc__ = """This module allow to generate forms from :class:`~afpy.ldap.node.Node` with a :mod:`~afpy.ldap.schema`::

    >>> from afpy.ldap import custom as ldap
    >>> user = ldap.getUser('gawel')
    >>> user.uid
    'gawel'
    >>> fs = FieldSet(ldap.User)
    >>> fs.configure(include=[fs.uid])
    >>> fs = fs.bind(user)
    >>> print fs.render().strip() #doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <div>
      <label class="field_req" for="User-gawel-uid">Login</label>
      <input id="User-gawel-uid" name="User-gawel-uid" type="text" value="gawel" />
    </div>
    ...

For more informations on how this works look the FormAlchemy_'s documentation.

.. _FormAlchemy: http://docs.formalchemy.org

"""
try:
    from formalchemy.forms import FieldSet as BaseFieldSet
except ImportError:
    raise ImportError('FormAlchemy is required')
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

def get_node_options(fs, name):
    if fs.model.conn:
        conn = fs.model.conn
        prop = getattr(fs._original_cls, name)
        item_class = prop.item_class
        try:
            item_class = prop.item_class(fs.model)
        except TypeError:
            pass
        try:
            nodes = conn.search_nodes(base_dn=item_class.base_dn,
                                      node_class=item_class, attrs=[item_class.rdn])
        except:
            return []
        else:
            return [(unicode(n), getattr(n, n.rdn)) for n in nodes if getattr(n, n.rdn)]
    return []

class Field(BaseField):
    """Field for ldap FieldSet"""

    def __init__(self, *args, **kwargs):
        if kwargs.get('type') in (fatypes.List, fatypes.Set):
            kwargs['multiple'] = True
            if 'options' not in kwargs:
                kwargs['options'] = lambda fs: get_node_options(fs, self.name)
        self._property = kwargs.pop('prop')
        BaseField.__init__(self, *args, **kwargs)
        if kwargs.get('type') in (fatypes.List, fatypes.Set):
            self.is_relation = True

    @property
    def value(self):
        if not self.is_readonly() and self.parent.data is not None:
            v = self._deserialize()
            if v is not None:
                return v
        return self.raw_value

    @property
    def raw_value(self):
        value = getattr(self.model, self.name, None)
        if isinstance(value, set):
            return list(value)
        return value

    def sync(self):
        """Set the attribute's value in `model` to the value given in `data`"""
        if not self.is_readonly():
            value = self._deserialize()
            if hasattr(self._property, 'item_class'):
                item_class = self._property.item_class
                try:
                    item_class = item_class(self.model)
                except TypeError:
                    pass
                value = [item_class(uid) for uid in value]
            if isinstance(self.type, fatypes.Set):
                value = set(value)
            setattr(self.model, self.name, value)


class FieldSet(BaseFieldSet):
    validator = None
    def __init__(self, model, session=None, data=None, prefix=None):
        self._fields = OrderedDict()
        self._render_fields = OrderedDict()
        if isinstance(model, node.Node):
            self._original_cls = model.__class__
        else:
            self._original_cls = model
        self.model = self.session = None
        BaseFieldSet.rebind(self, model, data=data)
        self.prefix = prefix
        self.model = model
        self.readonly = False
        self.focus = True
        self._errors = []
        focus = True
        for k, v in model.properties():
            type =  v.__class__.__name__.replace('Property','')
            if type == 'Unicode':
                type = 'String'
            elif type == 'SetOfNodes':
                type = 'Set'
            elif type == 'ListOfGroups':
                continue
            elif type == 'ListOfGroupNodes':
                type = 'List'
            try:
                t = getattr(fatypes, type)
            except AttributeError:
                raise NotImplementedError('%s is not mapped to a type' % v.__class__)
            else:
                self.append(Field(name=k, type=t, prop=v))
                field = self[k]
                field.set(label=v.title)
                if v.description:
                    field.set(instructions=v.description)
                if v.required:
                    field.validators.append(validators.required)

    def bind(self, model=None, session=None, data=None):
        """Bind to an instance"""
        if not (model or session or data):
            raise Exception('must specify at least one of {model, session, data}')
        if not model:
            if not self.model:
                raise Exception('model must be specified when none is already set')
            model = fields._pk(self.model) is None and self._original_cls or self.model
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

    def rebind(self, model=None, session=None, data=None):
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
        FieldSet.rebind(self, self._original_cls, data=data)
        if instances is not None:
            self.rows = instances

    def bind(self, instances=None, session=None, data=None):
        mr = FieldSet.bind(self, self._original_cls, session, data)
        mr.rows = instances
        return mr

    def _set_active(self, instance, session=None):
        FieldSet.rebind(self, instance, session or self.session, self.data)

def test_fieldset():
    from afpy.ldap import custom as ldap
    user = ldap.getUser('gawel')

    fs = FieldSet(ldap.User)
    fs = fs.bind(user)

    # rendering
    assert fs.uid.is_required() == True, fs.uid.is_required()
    assert fs.uid.value == 'gawel'
    html = fs.render()
    assert 'class="field_req" for="User-gawel-uid"' in html, html
    assert 'value="gawel"' in html, html

    # syncing
    fs.configure(include=[fs.uid])
    fs.rebind(user, data={'User-gawel-uid':'minou'})
    fs.validate()
    fs.sync()
    assert fs.uid.value == 'minou', fs.render_fields
    assert user.uid == 'minou', user.uid

    # grid
    fs = Grid(ldap.User, [user, ldap.User()])
    html = fs.render()
    assert '<thead>' in html, html
    assert 'value="minou"' in html, html

