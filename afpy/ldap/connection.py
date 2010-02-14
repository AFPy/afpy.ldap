# -*- coding: utf-8 -*-
#Copyright (C) 2009 Gael Pasgrimaud
__doc__ = """This module provide a ldap connection configurable via a .ini file

    >>> import afpy.ldap
    >>> conn = afpy.ldap.Connection(section='afpy')
    >>> conn.search_nodes(filter='(uid=gawel)')
    [<Node at uid=gawel,ou=members,dc=afpy,dc=org>]

"""
from dataflake.ldapconnection.connection import LDAPConnection
from ConfigObject import ConfigObject
from ConfigParser import NoOptionError
from node import Node, User, GroupOfNames
from ldap.ldapobject import ReconnectLDAPObject
import ldap
import _ldap
import os

class SmartLDAPObject(ReconnectLDAPObject):
  """
  Mainly the __init__() method does some smarter things
  like negotiating the LDAP protocol version and calling
  LDAPObject.start_tls_s().
  """

  def __init__(self,uri,
    trace_level=0,trace_file=None,trace_stack_limit=5,
    retry_max=1,retry_delay=60.0,
    who='',cred='',
    start_tls=1,
    tls_cacertfile=None,tls_cacertdir=None,
    tls_clcertfile=None,tls_clkeyfile=None,
  ):
    """
    Return LDAPObject instance by opening LDAP connection to
    LDAP host specified by LDAP URL.

    Unlike ldap.initialize() this function also trys to bind
    explicitly with the bind DN and credential given as parameter,
    probe the supported LDAP version and trys to use
    StartTLS extended operation if this was specified.

    Parameters like ReconnectLDAPObject.__init__() with these
    additional arguments:
    who,cred
        The Bind-DN and credential to use for simple bind
        right after connecting.
    start_tls
        Determines if StartTLS extended operation is tried
        on a LDAPv3 server and if the LDAP URL scheme is ldap:.
        If LDAP URL scheme is not ldap: (e.g. ldaps: or ldapi:)
        this parameter is ignored.
        0       Don't use StartTLS ext op
        1       Try StartTLS ext op but proceed when unavailable
        2       Try StartTLS ext op and re-raise exception if it fails
    tls_cacertfile

    tls_clcertfile

    tls_clkeyfile

    """
    # Initialize LDAP connection
    ReconnectLDAPObject.__init__(
      self,uri,
      trace_level=trace_level,
      trace_file=trace_file,
      trace_stack_limit=trace_stack_limit,
      retry_max=retry_max,
      retry_delay=retry_delay
    )
    # Set protocol version to LDAPv3
    self.protocol_version = ldap.VERSION3
    self.started_tls = 0
    try:
        self.simple_bind_s(who,cred)
    except ldap.PROTOCOL_ERROR:
        # Drop connection completely
        self.unbind_s() ; del self._l
        self._l = ldap.functions._ldap_function_call(_ldap.initialize,self._uri)
        self.protocol_version = ldap.VERSION2
        self.simple_bind_s(who,cred)
    # Try to start TLS if requested
    if start_tls>0 and uri[:5]=='ldaps:':
        if self.protocol_version>=ldap.VERSION3:
            try:
                self.start_tls_s()
            except (ldap.PROTOCOL_ERROR,ldap.CONNECT_ERROR):
                if start_tls>=2:
                    # Application does not accept clear-text connection
                    # => re-raise exception
                    raise
            else:
                self.started_tls = 1
        else:
            if start_tls>=2:
                raise ValueError,"StartTLS extended operation only possible on LDAPv3+ server!"
    if self.protocol_version==ldap.VERSION2 or (who and cred):
        self.simple_bind_s(who,cred)

class Connection(object):
    node_class = Node
    user_class = User
    group_class = GroupOfNames
    def __init__(self, section='ldap', prefix='ldap.', filename=os.path.expanduser('~/.ldap.cfg')):
        self.config = ConfigObject()
        self.config.read([filename])
        self.prefix = prefix
        self.section = self.config[section]
        self._conn = self.connection_factory()
        try:
            self.bind_dn = self.get('bind_dn')
            self.bind_pw = self.get('bind_pwd')
            self.base_dn = self.get('base_dn', self.bind_dn.split(',', 1)[1])
        except Exception, e:
            raise e.__class__('Invalid configuration %s - %s' % (section, self.section))


    def get(self, key, default=None):
        try:
            return self.section[self.prefix+key]
        except (NoOptionError, KeyError):
            return default

    def connection_factory(self, *args, **kwargs):
        config = dict(self.section.items())
        conn = ldapconnection_from_config(config, prefix=self.prefix)
        for url in conn.servers.keys():
            if 'ldaps://' in url:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                ldap.set_option(ldap.OPT_REFERRALS, 0)
        return conn

    def check(self, uid, password):
        dn = self.uid2dn(uid)
        try:
            self.connection_factory().connect(dn, password)
        except ldap.INVALID_CREDENTIALS, e:
            return False
        return True

    def search(self, **kwargs):
        """search"""
        if 'filter' in kwargs:
            kwargs['fltr'] = kwargs['filter']
            del kwargs['filter']
        options = dict(base_dn=self.base_dn,
                       scope=ldap.SCOPE_SUBTREE,
                       bind_dn=self.bind_dn,
                       bind_pwd=self.bind_pw)
        options.update(kwargs)
        return self._conn.search(options.pop('base_dn'), options.pop('scope'), **options)['results']

    def search_nodes(self, node_class=None, **kwargs):
        """like search nut return :class:`~afpy.ldap.node.Node` objects"""
        node_class = node_class or self.node_class
        return [node_class(r['dn'], attrs=r, conn=self) for r in self.search(**kwargs)]

    def get_dn(self, dn):
        """return search result for dn"""
        try:
            return self._conn.search(dn,
                                 ldap.SCOPE_BASE,
                                 bind_dn=self.bind_dn,
                                 bind_pwd=self.bind_pw)
        except:
            raise ValueError(dn)

    def uid2dn(self, uid):
        """apply `config:ldap.user_mask` to uid"""
        user_mask = self.get('user_mask', 'uid={uid},%s' % self.base_dn)
        return '=' in uid and uid or user_mask.replace('{uid}', uid)

    def group2dn(self, uid):
        """apply `config:ldap.group_mask` to uid"""
        group_mask = self.get('group_mask', 'cn={uid},%s' % self.section[self.prefix+'group_dn'])
        return '=' in uid and uid or group_mask.replace('{uid}', uid)

    def get_user(self, uid, node_class=None):
        """return user as :class:`~afpy.ldap.node.User` object"""
        dn = self.uid2dn(uid)
        node_class = node_class or self.user_class
        return node_class(dn=dn, conn=self)

    def get_group(self, uid, node_class=None):
        """return group as :class:`~afpy.ldap.node.GroupOfNames` object"""
        dn = self.group2dn(uid)
        node_class = node_class or self.group_class
        return node_class(dn=dn, conn=self)

    def get_node(self, dn, node_class=None):
        """return :class:`~afpy.ldap.node.Node` for dn"""
        node_class = node_class or self.node_class
        return node_class(dn=dn, conn=self)

    def get_groups(self, dn, base_dn=None, node_class=None):
        """return groups for dn as :class:`~afpy.ldap.node.GroupOfNames`"""
        node_class = node_class or self.group_class
        if base_dn is None:
            base_dn = self.section[self.prefix+'group_dn']
        filter = '(&(objectClass=groupOfNames)(member=%s))' % dn
        return self.search_nodes(node_class=node_class,
                                 base_dn=base_dn,
                                 scope=ldap.SCOPE_SUBTREE,
                                 filter=filter,
                                 bind_dn=self.bind_dn,
                                 bind_pwd=self.bind_pw)


    def save(self, node):
        if node._data and node.dn:
            node._conn = self
            attrs = node._data.copy()
            if 'dn' in attrs:
                dn = attrs.pop('dn')
                if dn.lower() != node.dn.lower():
                    raise ValueError('Inconsistent dn for %r: %s %s' % (self, node.dn, dn))
            try:
                self._conn.modify(node.dn, attrs=attrs)
            except Exception, e:
                raise e.__class__('Error while saving %r: %s' % (node, e))
            else:
                node._data = None
                return True

    def add(self, node):
        node._conn = self
        attrs = node._defaults.copy()
        attrs.update(node._data)
        if 'dn' in attrs:
            dn = attrs.pop('dn')
            if dn.lower() != node.dn.lower():
                raise ValueError('Inconsistent dn for %r: %s %s' % (self, node.dn, dn))
        rdn, base = node.dn.split(',', 1)
        try:
            self._conn.insert(base, rdn, attrs=attrs)
        except Exception, e:
            raise e.__class__('%s %s %s' % (e, node.dn, attrs))
        else:
            node._data = None

    def delete(self, node):
        node._data = None
        self._conn.delete(node.dn)

def ldapconnection_from_config(config, prefix='ldap.', **kwargs):
    """This is useful to get an LDAPConnection from a ConfigParser section
    items.
    """
    options = dict(
            host='localhost',
            port = 389,
            protocol = 'ldap',
            c_factory=SmartLDAPObject,
            rdn_attr='',
            bind_dn='',
            bind_pwd='',
            read_only=0,
            conn_timeout=-1,
            op_timeout=-1)

    options.update(kwargs)
    for key, value in config.items():
        if prefix in key:
            k = key.replace(prefix, '')
            if k in options:
                if isinstance(options[k], int):
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        raise TypeError(
                           '%s must be an integer. Got %s' % (key, value))
                options[k] = value

    if not callable(options['c_factory']):
        raise TypeError(
           'c_factory must be callable. Got %(c_factory)s' % options)

    return LDAPConnection(**options)

