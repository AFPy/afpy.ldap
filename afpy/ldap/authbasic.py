# -*- coding: utf-8 -*-
try:
    from repoze.what.middleware import setup_auth
except ImportError:
    raise ImportError('repoze.what is required')
from repoze.who.plugins.basicauth import BasicAuthPlugin
from afpy.ldap.connection import Connection
from afpy.ldap import auth
import os

__doc__ = """
This module contain a paste entry point example with basic auth.

You can use it in you app. Once you have read :doc:`../install` you can use this
in your paste config file:

.. sourcecode:: ini

    [pipeline:main]
    pipeline = auth myapp

    [filter:auth]
    use = egg:afpy.ldap
    section = afpy

    # uncomment this to disable groups/permissions
    #use_groups = false
    #use_permissions = false

    # and if you dont want to use ~/.ldap.cfg
    #config = %%(here)s/ldap.cfg

    [app:myapp]
    ...

You can now retrieve the :class:`~afpy.ldap.node.User` in the ``repoze.what``
environ vars and the :class:`~afpy.ldap.connection.Connection` in
``environ['%s']``

You can also adapt this code and use your own identifiers/challengers:

.. literalinclude:: ../../afpy/ldap/authbasic.py
   :language: py

""" % auth.CONNECTION_KEY

def make_auth_basic(app, global_config, conn=None, **local_conf):
    """Paste entry point for auth basic middleware using repoze.what"""

    if not conn:
        section = local_conf.get('section', 'ldap')
        config_file = local_conf.get('config', os.path.expanduser('~/.ldap.cfg'))
        conn = Connection(section, filename=config_file)

    basicauth = BasicAuthPlugin('Private web site')
    identifiers=[("basicauth", basicauth)]
    challengers=[("basicauth", basicauth)]

    authenticators=[("accounts", auth.Authenticator(conn, **local_conf))]
    groups = {'all_groups': auth.GroupAdapter(conn, **local_conf)}
    permissions = {'all_perms': auth.PermissionAdapter(conn, **local_conf)}
    mdproviders=[("accounts", auth.MDPlugin(conn, **local_conf))]

    return setup_auth(app,
                      groups,
                      permissions,
                      identifiers=identifiers,
                      authenticators=authenticators,
                      challengers=challengers,
                      mdproviders=mdproviders)


