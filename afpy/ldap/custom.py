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
import schema

SUBSCRIBER_FILTER = '(&(objectClass=payment)(!(paymentObject=donation)))'

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

    paymentDate = schema.DateAttribute('paymentDate')
    paymentObject = schema.StringAttribute('paymentObject')
    paymentAmount = schema.IntegerAttribute('paymentAmount')
    invoiceReference = schema.StringAttribute('invoiceReference')

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

    _defaults = dict(
        objectClass = ['top', 'person','associationMember',
                       'organizationalPerson', 'inetOrgPerson'],
        st='FR',
       )

    uid=schema.StringAttribute('uid', required=True)
    mail=schema.StringAttribute('mail', title='E-mail', required=True)
    birthDate=schema.DateAttribute('birthDate', title="Date de naissance", required=True)
    st=schema.StringAttribute('st', title='Pays', required=True)
    membershipExpirationDate=schema.DateAttribute('membershipExpirationDate', title="Expiration de cotisation")

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

def getAdherents(min=365, max=None):
    """ return users with a payment > now - min and < now - max
    """
    min = to_string(datetime.datetime.now()-datetime.timedelta(min))
    f = '(&%s(paymentAmount=*))' % SUBSCRIBER_FILTER
    if max:
        max = to_string(datetime.datetime.now()-datetime.timedelta(max))
        f = '(&%s(&(paymentDate>=%s)(paymentDate<=%s)))' % (f, min,max)
    else:
        f = '(&%s(paymentDate>=%s))' % (f, min)
    conn = get_conn()
    members = conn.search(filter=f, attrs=['dn'])
    members = [m['dn'].split(',')[1].split('=')[1] for m in members]
    return set(members)

def getAllTimeAdherents():
    """return users with at least one payment
    """
    conn = get_conn()
    return set([p['dn'].split(',')[1].split('=')[1] for p in conn.search(
                        filter='objectClass=payment')])

def getExpiredUsers():
    """return unregulirised users
    """
    members = getAllTimeAdherents() - getAdherents()
    return members


