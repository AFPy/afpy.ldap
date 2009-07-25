# -*- coding: utf-8 -*-
__doc__ = """This module provide specific customisation for afpy website

Initialize connection::

    >>> from afpy.ldap import custom as ldap
    >>> conn = ldap.get_conn()

Get myself::

    >>> user = conn.get_user('gawel')
    >>> user
    <AfpyUser at uid=gawel,ou=members,dc=afpy,dc=org>

"""
import datetime
from connection import Connection as BaseConnection
from node import Node
from node import User as BaseUser
from utils import to_string, to_python

class Payment(Node):
    """
    Initialize connection and user::

        >>> from afpy.ldap import custom as ldap
        >>> conn = ldap.get_conn()
        >>> user = conn.get_user('gawel')

    Members have payements::

        >>> payment = user.payments[0]
        >>> payment
        <Payment at paymentDate=20050101000000Z,uid=gawel,ou=members,dc=afpy,dc=org>
        >>> payment.paymentDate
        datetime.date(2005, 1, 1)

    We can add some::

        >>> date = datetime.date(2002, 1, 1)
        >>> payment = user.new_payment(paymentDate=date)
        >>> conn.add(payment)

    It works::

        >>> payment = user.payments[0]
        >>> payment.paymentDate
        datetime.date(2002, 1, 1)

    Delete it. I was not a member in 2002::

        >>> if payment.paymentDate == date:
        ...     conn.delete(payment)

    Assume deletion::

        >>> payment = user.payments[0]
        >>> payment.paymentDate
        datetime.date(2005, 1, 1)

    """
    _defaults = dict(objectClass=['top', 'payment'])
    _field_types = dict(
        paymentDate=datetime.date,
        paymentAmount=int,
        )

class AfpyUser(BaseUser):
    """
    Specific node for afpy member

    Initialize connection::

        >>> from afpy.ldap import custom as ldap
        >>> conn = ldap.get_conn()
        >>> user = conn.get_user('gawel')
        >>> user.birthDate
        datetime.date(1975, 4, 10)

    Try to add one. We need the conn to retrieve the correct dn from uid:

        >>> user = ldap.AfpyUser('afpy_test_user', attrs=dict(cn='Test AfpyUser', sn='Test'), conn=conn)
        >>> user
        <AfpyUser at uid=afpy_test_user,ou=members,dc=afpy,dc=org>
        >>> conn.add(user)

        >>> user.change_password('toto')
        >>> user.check('toto')
        True

        >>> user = conn.get_user('afpy_test_user')
        >>> user
        <AfpyUser at uid=afpy_test_user,ou=members,dc=afpy,dc=org>
        >>> conn.delete(user)

    """

    _field_types = dict(
        birthDate=datetime.date,
        membershipExpirationDate=datetime.date,
        )
    _defaults = dict(
        objectClass = ['top', 'person','associationMember',
                       'organizationalPerson', 'inetOrgPerson'],
        st='FR',
       )

    @property
    def payments(self):
        """return payments for the member"""
        payments = self._conn.search_nodes(node_class=Payment, base_dn=self._dn, filter='(objectClass=payment)')
        return sorted(payments, key=lambda i: i.paymentDate)

    def last_payments(self):
        """
        """

    def new_payment(self, paymentDate, paymentObject='personnal membership', paymentAmount=0, invoiceReference=''):
        """add a payment"""
        if not isinstance(paymentDate, datetime.date):
            paymentDate = to_python(to_string(paymentDate), datetime.date)
        dn = 'paymentDate=%s,%s' % (to_string(paymentDate), self._dn)
        attrs = Payment._defaults.copy()
        attrs.update(paymentDate=paymentDate, paymentObject=paymentObject,
                     paymentAmount=paymentAmount, invoiceReference=invoiceReference)
        payment = Payment(dn=dn, attrs=attrs)
        return payment

class Connection(BaseConnection):
    """Specific connection"""
    user_class = AfpyUser

def get_conn():
    """return a ldap connection"""
    return Connection(section='afpy')

def getUser(uid):
    """
    >>> getUser('gawel')
    <AfpyUser at uid=gawel,ou=members,dc=afpy,dc=org>
    >>> getUser('lskdslmdgkmdglsldjggsdgjsk')
    """
    user = get_conn().get_user(uid)
    try:
        user.dn
    except:
        return None
    else:
        return user
    return get_conn().get_user(uid)

