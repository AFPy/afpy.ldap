========
Doctests
========

This folder contains doctests for gp.ldap package.

  >>> import gp.ldap
  >>> adapter = gp.ldap.get()

  >>> conn = adapter.getConnection()
  >>> conn
  <ldapadapter.utility.LDAPConnection object at ...>


