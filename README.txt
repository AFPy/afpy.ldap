This module is actively used on http://www.afpy.org to manage the french python comunity members.

Get a connection (this custom afpy connection get is configuration from a
`~/.ldap.ini` file.)::

    >>> from afpy.ldap import custom as ldap
    >>> conn = ldap.get_conn()

Get a node via is dn::

    >>> dn = 'uid=gawel,ou=members,dc=afpy,dc=org'
    >>> node = conn.get_node(dn)
    >>> node
    <Node at uid=gawel,ou=members,dc=afpy,dc=org>

    >>> print node.birthDate
    19750410000000Z

You can also define your own node class with a schema::

    >>> from afpy.ldap.node import Node
    >>> from afpy.ldap import schema
    >>> class User(Node):
    ...     uid=schema.StringProperty('uid')
    ...     birthDate = schema.DateProperty('birthDate', title='Date de naissance')
    >>> node = conn.get_node(dn, node_class=User)
    >>> node
    <User at uid=gawel,ou=members,dc=afpy,dc=org>

Then data is converted to a python object::

    >>> node.birthDate
    datetime.date(1975, 4, 10)

This also allow to generate forms with FormAlchemy_::

    >>> from afpy.ldap import forms
    >>> fs = forms.FieldSet(User)
    >>> user = User()
    >>> fs.rebind(user)
    >>> print fs.render().strip() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <div>
      <label class="field_opt" for="User--uid">Uid</label>
      <input id="User--uid" name="User--uid" type="text" />
    </div>
    ...
    <div>
      <label class="field_opt" for="User--birthDate">Date de naissance</label>
    ...

.. _FormAlchemy: http://docs.formalchemy.org

The source code can be find on the `AFPy repository`_

.. _AFPy repository: https://hg.afpy.org/gawel/afpy.ldap/summary

Got a bug, feature request ? Want to send beer because you love it ? Send an
email at afpy-web@lists.afpy.org

