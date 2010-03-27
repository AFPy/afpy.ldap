# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
try:
    from repoze.what.adapters import BaseSourceAdapter, SourceError
except ImportError:
    raise ImportError('repoze.what is required')
from repoze.who.interfaces import IMetadataProvider
from repoze.who.interfaces import IAuthenticator
from afpy.ldap.connection import Connection
from zope.interface import implements
import logging
import os

__doc__ = """This is a set of plugins for repoze.what"""

log = logging.getLogger(__name__)

CONNECTION_KEY = 'afpy.ldap.connection'

def as_bool(value):
    if value in (True, False, 0, 1):
        return bool(value)
    if isinstance(value, basestring):
        if value.lower() in ('true', '1'):
            return True
    return False

class GroupAdapter(BaseSourceAdapter):
    """Group adapter.
    """

    def __init__(self, conn, use_groups=True, **kwargs):
        self.conn = conn
        self.use_groups = as_bool(use_groups)
        log.warn('GroupAdapter(%r, use_groups=%r, **%r)',
                    self.conn, self.use_groups, kwargs)

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        if self.use_groups:
            uid = hint.get('repoze.what.userid')
            if uid and isinstance(uid, basestring):
                user = self.conn.get_user(uid)
                if user:
                    return user.groups
        return []

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class PermissionAdapter(BaseSourceAdapter):
    """Permission adapter.
    """

    def __init__(self, conn, use_permissions=True, **kwargs):
        self.conn = conn
        self.use_permissions = as_bool(use_permissions)
        log.warn('PermissionAdapter(%r, use_permissions=%r, **%r)',
                    self.conn, self.use_permissions, kwargs)

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        if self.use_permissions:
            group = self.conn.get_group(hint, node_class=self.conn.group_class)
            if group:
                rdn = self.conn.group_class.rdn
                return [getattr(v, rdn, None) \
                        for v in self.conn.get_groups(group.dn) \
                        if getattr(v, rdn, None)]
        return []

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class Authenticator(object):
    """Authenticator plugin.
    """
    implements(IAuthenticator)

    def __init__(self, conn):
        self.conn = conn
        log.warn('Authenticator(%r)', self.conn)

    def authenticate(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        login = identity.get('login', '')
        password = identity.get('password', '')
        if login:
            login = str(login)
            user = self.conn.get_user(login)
            rdn = self.conn.user_class._rdn
            if user is not None and password:
                if user.check(password):
                    uid = str(getattr(user, rdn))
                    identity['login'] = login
                    identity['rdn'] = uid
                    identity['user'] = user
                    return uid

class MDPlugin(object):
    """Metadata provider plugin.
    """
    implements(IMetadataProvider)

    def __init__(self, conn):
        self.conn = conn
        log.warn('MDPlugin(%r)', self.conn)

    def add_metadata(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        if 'user' not in identity:
            uid = identity['repoze.who.userid']
            if uid:
                user = self.conn.get_user(uid)
                if user:
                    identity['user'] = user

