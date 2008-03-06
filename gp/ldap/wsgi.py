# -*- coding: utf-8 -*-
from paste.deploy.config import ConfigMiddleware
from paste.deploy import CONFIG
from paste.auth.basic import AuthBasicHandler
from paste.fileapp import FileApp
import gp.ldap
import ConfigParser
import string
import os

dirname = os.path.dirname(os.path.abspath(__file__))
STATIC_FILES = ['jquery.js', 'ldap.js']

def index():
    out = ['<html><head>',
           '<script src="js/jquery.js" type="text/javascript"></script>',
           '<script src="js/ldap.js" type="text/javascript"></script>',
           '<style type="text/css">'
           '\n#ldap_contents dd {margin:0;padding:0}',
           '\n#ldap_contents dd label {width:50%;}',
           '\n</style>',
           '</head><body><div id="ldap_links">']
    for l in string.ascii_letters[26:]:
        out.append(' <a href="#%s">%s</a>' % (l, l))
    out.append('</div><div id="ldap_contents"></div>')
    out.append('</body></html>')
    return [''.join(out)]

def application(environ, start_response):
    """an application to render a ldap search
    """
    path_info = environ.get('PATH_INFO')
    parts = [p for p in path_info.split('/') if p]
    filename = parts and parts.pop() or ''

    if not filename:
        start_response('200 OK', [('Content-Type', 'text/html;charset=utf-8')])
        return index()

    if filename in STATIC_FILES:
        app = FileApp(os.path.join(dirname, filename))
        return app(environ, start_response)

    if len(filename) == 1:
        adapter = gp.ldap.get()
        conn = adapter.getConnection()
        results = conn.search(adapter.base_dn,
                              'sub', '(cn=%s*)' % filename)
        out = [gp.ldap.xhtml(r) for r in results]

    start_response('200 OK', [('Content-Type', 'text/html;charset=utf-8')])
    return out

def ldap_auth(self, username, password):
    if not username or not password:
        return False
    adapter = gp.ldap.get()
    return adapter.checkCredentials(username, password)

def factory(global_config, **local_config):
    """aplication factory to expand configs
    """
    conf = global_config.copy()
    conf.update(**local_config)
    app = application
    app = ConfigMiddleware(app, conf)
    app = AuthBasicHandler(app, 'ldap', ldap_auth)
    return app
