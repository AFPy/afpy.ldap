# -*- coding: utf-8 -*-
from zope.interface import implements
from repoze.who.interfaces import IIdentifier
from repoze.who.plugins.basicauth import BasicAuthPlugin
from repoze.who.plugins.friendlyform import FriendlyFormPlugin
from repoze.what.middleware import setup_auth
from paste.request import get_cookies
from afpy.ldap import custom as ldap
from afpy.ldap import auth
from afpy.ldap import tktauth
import binascii
import logging
import time
import os

log = logging.getLogger(__name__)


class AuthTktCookiePlugin(object):

    implements(IIdentifier)

    def __init__(self, cookie_name):
        from ConfigObject import ConfigObject

        cfg = ConfigObject(filename=os.path.expanduser('~/.afpy.cfg'))

        self.secret = '%s' % cfg.authtkt.secret
        self.timeout = int(cfg.authtkt.timeout)
        self.cookie_name = cookie_name

    # IIdentifier
    def identify(self, environ):
        cookies = get_cookies(environ)
        cookie = cookies.get(self.cookie_name)

        if cookie is None or not cookie.value:
            return None

        try:
            token = binascii.a2b_base64(cookie.value)
        except binascii.Error:
            data = None
        else:
            data = tktauth.validateTicket(self.secret, token,
                                          timeout=self.timeout,
                                          now=time.time(),
                                          mod_auth_tkt=True)
        if not data:
            return None

        (digest, userid, tokens, user_data, timestamp) = data
        environ['AUTH_TYPE'] = 'cookie'

        identity = {}
        identity['timestamp'] = timestamp
        identity['repoze.who.userid'] = userid
        identity['tokens'] = tokens
        identity['userdata'] = user_data
        return identity

    def _get_cookies(self, environ, value, max_age=None):
        max_age = ''

        cur_domain = environ.get('HTTP_HOST', environ.get('SERVER_NAME'))
        wild_domain = '.' + cur_domain
        cookies = [
            ('Set-Cookie', '%s="%s"; Path=/%s' % (
             self.cookie_name, value, max_age)),
            ('Set-Cookie', '%s="%s"; Path=/; Domain=%s%s' % (
             self.cookie_name, value, cur_domain, max_age)),
            ('Set-Cookie', '%s="%s"; Path=/; Domain=%s%s' % (
             self.cookie_name, value, wild_domain, max_age))
        ]
        return cookies

    # IIdentifier
    def forget(self, environ, identity):
        # return a set of expires Set-Cookie headers
        return self._get_cookies(environ, '""')

    # IIdentifier
    def remember(self, environ, identity):
        cookies = get_cookies(environ)
        existing = cookies.get(self.cookie_name)
        old_cookie_value = getattr(existing, 'value', None)

        timestamp, userid, tokens, userdata = None, '', '', ''

        if old_cookie_value:
            try:
                old_cookie_value = binascii.a2b_base64(old_cookie_value)
            except binascii.Error:
                pass
            else:
                data = tktauth.validateTicket(self.secret, old_cookie_value,
                                              timeout=self.timeout,
                                              now=time.time(),
                                              mod_auth_tkt=True)
                if data:
                    (digest, userid, tokens, user_data, timestamp) = data

        who_userid = identity['repoze.who.userid']
        who_tokens = identity.get('tokens', '')
        who_userdata = identity.get('userdata', '')

        if not isinstance(tokens, basestring):
            tokens = ','.join(tokens)
        if not isinstance(who_tokens, basestring):
            who_tokens = ','.join(who_tokens)
        old_data = (userid, tokens, userdata)
        new_data = (who_userid, who_tokens, who_userdata)
        if old_data != new_data:
            ticket = tktauth.createTicket(self.secret, who_userid,
                                          timestamp=timestamp,
                                          mod_auth_tkt=True)
            if old_cookie_value != ticket:
                # return a set of Set-Cookie headers
                cookie = binascii.b2a_base64(ticket).rstrip()
                return self._get_cookies(environ, cookie)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            id(self))  # pragma NO COVERAGE


class Authenticator(auth.Authenticator):
    def authenticate(self, environ, identity):
        auth.Authenticator.authenticate(self, environ, identity)
        if 'user' in identity:
            cn = identity['user'].cn
            identity['login'] = cn
            return cn


def make_auth(app, global_config, **local_config):

    conn = ldap.get_conn()

    cookie = AuthTktCookiePlugin('__ac')

    loginform = FriendlyFormPlugin(login_form_url="/login",
                                   login_handler_path="/do_login",
                                   post_login_url="/login",
                                   logout_handler_path="/logout",
                                   post_logout_url="/login",
                                   rememberer_name="_ac")

    basicauth = BasicAuthPlugin('Private web site')
    if 'auth_basic' in local_config:
        log.warn('using auth basic')
        identifiers = [("basicauth", basicauth)]
        challengers = [("basicauth", basicauth)]
    else:
        log.warn('using cookie auth')
        identifiers = [
            ("loginform", loginform),
            ("_ac", cookie),
            ("basicauth", basicauth)]
        challengers = [("loginform", loginform)]

    authenticators = [("accounts", Authenticator(conn))]
    groups = {'all_groups': auth.GroupAdapter(conn)}
    permissions = {'all_perms': auth.PermissionAdapter(conn,
                                                       use_permissions=False)}
    mdproviders = [("accounts", auth.MDPlugin(conn))]

    return setup_auth(app,
                      groups,
                      permissions,
                      identifiers=identifiers,
                      authenticators=authenticators,
                      challengers=challengers,
                      mdproviders=mdproviders)
