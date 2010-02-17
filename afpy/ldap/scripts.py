# -*- coding: utf-8 -*-
from optparse import OptionParser
from afpy.ldap.connection import Connection
from afpy.ldap import node
from afpy.ldap import utils
from afpy.ldap import schema
from IPython.Shell import IPShellEmbed
import IPython
import string
import base64
import ldap
import sys

class Shell(IPShellEmbed):
    def __init__(self, section=''):
        argv = [
                 '-prompt_in1','\C_Blue\#) \C_Greenldap/%s\$ ' % section,
               ]
        IPShellEmbed.__init__(self,argv,banner='',exit_msg=None,rc_override=None,
                 user_ns=None)

node.Node.__str__ = lambda s: s.pprint()

class User(node.User):
    uid=schema.StringProperty('uid')
    title=schema.StringProperty('title')
    cn=schema.UnicodeProperty('cn')
    givenName=schema.UnicodeProperty('givenName')
    sn=schema.UnicodeProperty('sn')
    mail=schema.StringProperty('mail')
    emailAlias=schema.StringProperty('emailAlias')
    labeledURI=schema.StringProperty('labeledURI')
    birthDate=schema.DateProperty('birthDate')
    telephoneNumber=schema.StringProperty('telephoneNumber')
    l=schema.UnicodeProperty('l')
    street=schema.UnicodeProperty('street')
    st=schema.StringProperty('st')
    postalCode=schema.StringProperty('postalCode')

class Group(node.GroupOfNames):
    pass

class Nodes(dict):

    def update(self, args):
        keys = self.keys()
        for attr in keys:
            del self[attr]
            del self.__dict__[attr]
        for a in args:
            uid = getattr(a, 'uid', a.cn)
            uid = uid.lower()
            for c in ' .-@':
                uid = uid.replace(c, '_')
            self[uid] = a
            self.__dict__[uid] = a

    def values(self):
        return [self[k] for k in sorted(self.keys())]

    def __getattr__(self, attr):
        if attr in self.keys():
            return self[attr]
        raise AttributeError(attr)

    def __getitem__(self, i):
        if isinstance(i, int):
            return self.values()[i]
        else:
            return dict.__getitem__(self, i)

    def __getslice__(self, i, j):
        nodes = Nodes()
        args = self.values()[i:j]
        nodes.update(args)
        return nodes

    def __delattr__(self, attr):
        a = getattr(self, attr)
        try:
            a.conn.delete(a)
        except Execption, e:
            print e
        else:
            del self[attr]
            del self.__dict__[attr]

    def __iter__(self):
        return self.itervalues()

    def __repr__(self):
        return repr(sorted(self.keys()))

    def __str__(self):
        return self.pprint()

    def pprint(self, encoding=utils.DEFAULT_ENCODING):
        out = []
        for a in sorted(self.keys()):
            out.append(self[a].pprint(encoding) + '\n')
        return '\n'.join(out)

def search(klass):
    def wrapper(self, name=''):
        if name in '*-':
            name = '*'
            filter = shell.search_filter % dict(name=name)
        elif '=' in name:
            filter = name
        else:
            name = '*%s*' % name
            filter = shell.search_filter % dict(name=name)
        nodes = klass.unlimited_search(filter=filter)
        shell.update_nodes(klass, nodes)
        u = len(nodes) == 1 and nodes[0] or None
        shell.api.to_user_ns('u')
        return (('u', u), ('%ss' % klass.__name__.lower(), len(shell.nodes[klass.__name__])))
    return wrapper

def save(*args):
    """Save all loaded nodes
    """
    for nodes in shell.nodes.values():
        for node in nodes.values():
            uid = getattr(node, node.rdn)
            try:
                node.save()
            except Exception, e:
                print 'Error while saving %r: %s' % (uid, e)
            else:
                print '%s saved' % uid

class API(property):
    def __get__(self, *args):
        return IPython.ipapi.get() or __IPYTHON__.api

class shell(object):
    search_filter='(|(cn=%(name)s)(uid=%(name)s))'
    section = None
    nodes = {}
    conn = None
    magics = []
    api = API()

    parser = OptionParser()
    parser.add_option('-s', '--section', dest='section', default=None,
                      help='A config section to get ldap info from')

    def __init__(self, section=None, classes=None, callback=None):
        cls = self.__class__
        sys.argv = sys.argv[0:1]
        ipshell = Shell(section)
        cls.parser.usage = """%prog [-s SECTION] """ + cls.help()
        if not section:
            cls.parser.parse_args(['-h'])
        else:
            cls.section = section
            cls.init_magics()
            cls.init(classes)
            if callable(callback):
                callback()
            print cls.help().strip()
            ipshell(header='', global_ns={}, local_ns={})

    @classmethod
    def init(cls, classes):
        if cls.section:
            cls.conn = Connection(section=cls.section)
            conn = cls.conn
            cls.api.to_user_ns('conn')
            if not classes:
                classes = (User, Group)
        elif not classes:
            classes = ()
        for klass in classes:
            klass.conn = cls.conn
            name = klass.__name__
            lname = name.lower()
            rdn = cls.conn.get('%s_rdn' % lname)
            if rdn:
                klass.rdn = rdn
            base_dn = cls.conn.get('%s_dn' % lname)
            if base_dn:
                klass.base_dn = base_dn
            else:
                base_dn = cls.conn.get('base_dn')
                if base_dn:
                    klass.base_dn = base_dn
            cls.nodes[name] = type(name, (Nodes,), {})()
            exec '%ss = cls.nodes[%r]' % (lname, name)
            cls.api.to_user_ns('%ss' % lname)
            exec '%s = klass' % (name,)
            cls.api.to_user_ns(name)
            cls.api.expose_magic('search_%s' % lname, search(klass))

    @classmethod
    def init_magics(cls):
        cls.expose_magic('save', save)

    @classmethod
    def update_nodes(cls, klass, nodes):
        cls.nodes[klass.__name__].update(nodes)

    @classmethod
    def search(cls, klass, name):
        return search(klass)(None, name)

    @classmethod
    def expose_magic(cls, *args):
        if not isinstance(args[0], basestring):
            func = args[0]
            args = (func.func_name, func)
        cls.magics.append(args)
        cls.api.expose_magic(*args)

    @classmethod
    def help(cls):
        out = ''
        if cls.nodes:
            out = """

Available classes
=================
"""
        for name, nodes in cls.nodes.items():
            lname = name.lower()
            sep = '-'*len(name)
            out += """
%(name)s
%(sep)s

    >>> %(lname)ss
    %(nodes)r
    >>> %%search_%(lname)s [string|ldap filter]
""" % locals()

        if cls.magics:
            out += """
Other commands
==============
"""
        for name, func in cls.magics:
            doc = getattr(func, '__doc__', '')
            doc = doc and '# %s' % doc or ''
            doc = doc.strip()
            out += """
    >>> %%%(name)-20.20s %(doc)s
""" % locals()
        return out

def main():
    options, args = shell.parser.parse_args()
    if options.section:
        shell.section = options.section
    if options.section == 'afpy':
        sys.argv = sys.argv[0:1]
        from afpy.ldap import custom
        custom.main()
        return
    elif options.section == 'gawel':
        sys.argv = sys.argv[0:1]
        from afpy.ldap import gawelorg
        gawelorg.main()
        return
    shell(section=options.section)
