# -*- coding: utf-8 -*-
from webtest import TestApp
from webob import Request, Response, exc
from afpy.ldap import custom as ldap
from afpy.ldap.authbasic import make_auth_basic
from afpy.ldap.authafpy import make_auth
from repoze.what.predicates import Any, is_user, has_permission, in_group
import logging
import unittest
import base64

log = logging.getLogger('nose')

def application(environ, start_response):
    req = Request(environ)
    resp = Response()
    resp.content_type = 'text/plain'
    resp.body = 'anonymous'
    if req.path_info == '/auth' and not environ.get('repoze.what.credentials'):
        return exc.HTTPUnauthorized()(environ, start_response)
    if req.path_info == '/secure':

        ident = environ.get('repoze.who.identity', {})
        body = 'repoze.who.identity = {\n'
        for k, v in ident.items():
            if k.lower() != 'password':
                body += '    %r: %r,\n' % (k, v)
        body += '}\n\n'

        cred = environ.get('repoze.what.credentials', {})
        body += 'repoze.what.credentials = {\n'
        for k, v in cred.items():
            body += '    %r: %r,\n' % (k, v)
        body += '}\n\n'

        for group in ('svn', 'bureau', 'other'):
            body += 'in_group(%r) == %s\n' % (group, in_group(group).is_met(environ))

        for perm in ('read', 'write'):
            body += 'has_permision(%r) == %s\n' % (perm, has_permission(perm).is_met(environ))

        resp.body = body
    return resp(environ, start_response)

def make_test_app(*args, **kwargs):
    return application

conn = ldap.get_conn()

class TestAuth(unittest.TestCase):

    def setUp(self):
        user = ldap.User('afpy_test_user', attrs=dict(cn='Test User', sn='Test'), conn=conn)
        try:
            conn.add(user)
        except:
            log.warn('afpy_test_user already exist')
            user = ldap.getUser('afpy_test_user')
        user.change_password('toto')
        self.user = user
        self.setUpApp()

    def setUpApp(self):
        app = make_auth_basic(application, {}, section='afpy')
        self.app = TestApp(app)

    def test_request(self):
        resp = self.app.get('/')
        resp.mustcontain('anonymous')

    def test_gawel(self):
        if conn.config.tests.passwd:
            encoded = base64.encodestring('%(uid)s:%(passwd)s' % conn.config.tests)
            headers = {'Authorization': 'Basic %s' % encoded}
            resp = self.app.get('/secure', headers=headers)
            resp.mustcontain(
                "'repoze.what.userid': %r" % conn.config.tests.uid,
                "in_group('svn') == True",
                "in_group('bureau') == True",
                "in_group('other') == False",
                "has_permision('read') == False",
                "has_permision('write') == False",
                )

    def tearDown(self):
        try:
            conn.delete(self.user)
        except:
            log.warn('cant delete afpy_test_user')
            pass

class TestAuthAfpy(TestAuth):

    def setUpApp(self):
        app = make_auth(application, {}, section='afpy')
        self.app = TestApp(app)

