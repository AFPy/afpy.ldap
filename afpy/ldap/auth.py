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
import os

__doc__ = """This is a set of plugins for repoze.what"""

CONNECTION_KEY = 'afpy.ldap.connection'


class GroupAdapter(BaseSourceAdapter):
    """Group adapter.
    """

    def __init__(self, conn):
        self.conn = conn
        self.klass = conn.user_class

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()
        #users = self.conn.view('auth/group_users', key=section)
        #return [doc['_id'] for doc in users]

    def _find_sections(self, hint):
        uid = hint.get('repoze.what.userid')
        if uid and isinstance(uid, basestring):
            user = self.conn.get_user(uid)
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

    def __init__(self, conn):
        self.conn = conn

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        group = self.conn.get_group(hint, node_class=self.conn.group_class)
        return [v.cn for v in self.conn.get_groups(group.dn) if v.cn]

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

    def authenticate(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        login = identity.get('login', '')
        password = identity.get('password', '')
        if login:
            login = str(login)
            user = self.conn.get_user(login)
            rdn = self.conn.user_class._rdn
            if user is not None:
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

    def add_metadata(self, environ, identity):
        if CONNECTION_KEY not in environ:
            environ[CONNECTION_KEY] = self.conn
        if 'user' not in identity:
            uid = identity['repoze.who.userid']
            if uid:
                user = conn.get_user(uid)
                if user:
                    identity['user'] = user

