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

class BaseAdapter(object):

    use_search = False

    def get_user(self, uid):
        if uid:
            if self.use_search:
                rdn = self.conn.user_class._rdn
                users = self.conn.search_nodes(
                            filter='%s=%s' % (rdn, uid),
                            base_dn=self.conn.base_dn,
                            node_class=self.conn.user_class)
                if users and len(users) == 1:
                    return users[0]
            else:
                user = self.conn.get_user(uid)
                if user is not None:
                    try:
                        user.normalized_data()
                    except:
                        return None
                    else:
                        return user

class GroupAdapter(BaseSourceAdapter, BaseAdapter):
    """Group adapter.
    """

    def __init__(self, conn, use_groups=True, **kwargs):
        self.conn = conn
        self.use_groups = as_bool(use_groups)
        log.warn('GroupAdapter(%r, use_groups=%r, **%r)',
                    self.conn, self.use_groups, kwargs)

    def _find_sections(self, hint):
        if self.use_groups:
            user = None
            if 'user' in hint:
                user = hint['user']
            else:
                uid = hint.get('repoze.what.userid', None)
                if uid and isinstance(uid, basestring):
                    user = self.get_user(uid)
            if user:
                return user.groups
        return []


class PermissionAdapter(BaseSourceAdapter):
    """Permission adapter.
    """

    def __init__(self, conn, use_permissions=True, **kwargs):
        self.conn = conn
        self.use_permissions = as_bool(use_permissions)
        log.warn('PermissionAdapter(%r, use_permissions=%r, **%r)',
                    self.conn, self.use_permissions, kwargs)

    def _find_sections(self, hint):
        if self.use_permissions:
            klass = self.conn.perm_class or self.conn.group_class
            group = self.conn.get_group(hint, node_class=self.conn.group_class)
            if group:
                rdn = klass.rdn
                groups = self.conn.get_groups(group.dn, node_class=klass)
                return [getattr(v, rdn) for v in  groups if getattr(v, rdn, '')]
        return []


class Authenticator(BaseAdapter):
    """Authenticator plugin.
    """
    implements(IAuthenticator)

    def __init__(self, conn, use_search=False, **kwargs):
        self.conn = conn
        self.use_search = use_search
        log.warn('Authenticator(%r)', self.conn)

    def authenticate(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        login = identity.get('login', '')
        password = identity.get('password', '')
        user = self.get_user(login)
        if user is not None and password:
            if user.check(password):
                rdn = self.conn.user_class._rdn
                uid = str(getattr(user, rdn))
                identity['login'] = login
                identity['rdn'] = uid
                identity['user'] = user
                return uid

class MDPlugin(BaseAdapter):
    """Metadata provider plugin.
    """
    implements(IMetadataProvider)

    def __init__(self, conn, use_search=False, **kwargs):
        self.conn = conn
        self.use_search = use_search
        log.warn('MDPlugin(%r)', self.conn)

    def add_metadata(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        if 'user' not in identity:
            uid = identity['repoze.who.userid']
            if uid:
                user = self.get_user(uid)
                if user is not None:
                    identity['user'] = user

