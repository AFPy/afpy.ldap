# -*- coding: utf-8 -*-
from webob import Request, Response, exc
from paste.deploy import CONFIG
from paste.fileapp import FileApp
import afpy.ldap
import string
import os

dirname = os.path.dirname(os.path.abspath(__file__))
STATIC_FILES = ['jquery.js', 'ldap.js']

def index():
    out = ['<html><head>',
           '<meta http-equiv="content-type" content="text/html; charset=utf-8"/>',
           '<title>Ldap</title>',
           '<script src="./js/jquery.js" type="text/javascript"></script>',
           '<script src="./js/ldap.js" type="text/javascript"></script>',
           '<style type="text/css">'
           '\n#ldap_links {text-align:center;}',
           '\n#ldap_contents {margin:1em 10%; padding:0}',
           '\n#ldap_contents label {width:50%;}',
           '\n.ldiff {margin:1em 0; padding:0}',
           '\n</style>',
           '</head><body><div id="ldap_links">']
    for l in string.ascii_letters[26:]:
        out.append(' <a href="#%s">%s</a>' % (l, l))
    out.append('</div><div id="ldap_contents"></div>')
    out.append('</body></html>')
    return ''.join(out)

def application(environ, start_response):
    """an application to render a ldap search
    """
    if environ.get('REMOTE_USER', None) != 'gawel':
        return exc.HTTPForbidden()(environ, start_response)

    req = Request(environ)
    resp = Response()

    path_info = req.path_info
    parts = [p for p in path_info.split('/') if p]
    filename = parts and parts.pop() or ''

    if not filename:
        resp.body = index()
        return resp(environ, start_response)

    if filename in STATIC_FILES:
        app = FileApp(os.path.join(dirname, filename))
        return app(environ, start_response)

    if len(filename) == 1:
        conn = afpy.ldap.get_conn('ldap')
        results = conn.search(filter='(cn=%s*)' % filename)
        out = [afpy.ldap.xhtml(r) for r in results]
        resp.charset='utf-8'
        body = ''.join(out)
        body = body.decode('iso-8859-1')
        resp.body = body.encode('utf-8')
    return resp(environ, start_response)

def factory(global_config, **local_config):
    return application
