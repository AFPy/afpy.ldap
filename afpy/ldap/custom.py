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

DONATION = 'donation'
PERSONNAL_MEMBERSHIP = 'personnal membership'
STUDENT_MEMBERSHIP = 'student membership'
CORPORATE_MEMBERSHIP = 'corporate membership'

PAYMENTS_LABELS = (DONATION, PERSONNAL_MEMBERSHIP, STUDENT_MEMBERSHIP, CORPORATE_MEMBERSHIP)

PAYMENTS_OPTIONS = {
        DONATION:'Donation',
        PERSONNAL_MEMBERSHIP:'Cotisation',
        STUDENT_MEMBERSHIP:'Cotisation etudiante',
#        CORPORATE_MEMBERSHIP:'Cotisation entreprise'
}

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
        >>> payment = user.new_payment(paymentDate=date, paymentAmount=20)
        >>> conn.add(payment)

    It works::

        >>> payment = user.payments[0]
        >>> payment.paymentDate
        datetime.date(2002, 1, 1)
        >>> payment.paymentAmount
        20

    Delete it. I was not a member in 2002::

        >>> if payment.paymentDate == date:
        ...     conn.delete(payment)

    Assume deletion::

        >>> payment = user.payments[0]
        >>> payment.paymentDate
        datetime.date(2005, 1, 1)

    """
    _rdn = 'paymentDate'
    _defaults = dict(objectClass=['top', 'payment'])

    paymentDate = schema.DateProperty('paymentDate', title='Date', required=True)
    paymentObject = schema.StringProperty('paymentObject', title='Type', required=True)
    paymentAmount = schema.IntegerProperty('paymentAmount', title='Montant', required=True)
    invoiceReference = schema.StringProperty('invoiceReference', title='Reference')

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

    _rdn = 'uid'
    _base_dn = 'ou=members,dc=afpy,dc=org'
    _defaults = dict(
        objectClass = ['top', 'person','associationMember',
                       'organizationalPerson', 'inetOrgPerson'],
        st='FR',
       )

    uid=schema.StringProperty('uid', title='Login', required=True)
    title=schema.StringProperty('title', title='Role', required=True)
    sn=schema.StringProperty('sn', title='Nom', required=True)
    mail=schema.StringProperty('mail', title='E-mail', required=True)
    emailAlias=schema.StringProperty('emailAlias', title='Alias E-mail')
    labeledURI=schema.StringProperty('labeledURI', title='Open Id')
    birthDate=schema.DateProperty('birthDate', title="Date de naissance", required=True)
    telephoneNumber=schema.StringProperty('telephoneNumber', title='Tel.', required=True)
    l=schema.StringProperty('l', title='Ville', required=True)
    street=schema.StringProperty('street', title='Adresse', required=True)
    st=schema.StringProperty('st', title='Pays', required=True)
    postalCode=schema.StringProperty('postalCode', title='Code Postal', required=True)
    membershipExpirationDate=schema.DateProperty('membershipExpirationDate', title="Expiration de cotisation")

    @property
    def payments(self):
        """return payments for the member"""
        payments = self._conn.search_nodes(node_class=Payment, base_dn=self._dn, filter='(objectClass=payment)')
        return sorted(payments, key=lambda i: i.paymentDate)

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

    @property
    def email(self):
        """return emailAlias if any or mail"""
        alias = self.emailAlias
        if alias and '@afpy.org' in alias:
            return alias
        return self.mail

    @property
    def expired(self):
        """return True if membership is expired
        """
        date = self.membershipExpirationDate
        if isinstance(date, datetime.date):
            date = to_python(to_string(date), datetime.datetime)
            if date > datetime.datetime.now():
                return False
        return True

    def append(node, save=True):
        super(AfpyUser, self).append(node, save=save)
        updateExpirationDate(self)


def get_conn():
    """return a ldap connection"""
    class Connection(BaseConnection):
        """Specific connection"""
        user_class = AfpyUser
    return Connection(section='afpy')

def getUser(uid):
    """
    >>> getUser('gawel')
    <AfpyUser at uid=gawel,ou=members,dc=afpy,dc=org>
    >>> getUser('lskdslmdgkmdglsldjggsdgjsk')
    """
    user = get_conn().get_user(uid)
    try:
        user.normalized_data()
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

def getMembersOf(uid):
    """return user uids of group"""
    conn = get_conn()
    group = conn.get_group(uid)
    return [p.split(',', 1)[0].split('=')[1] for p in group.member]

def updateExpirationDate(user):
    payments = [p for p in user.payments if p.paymentAmount]
    if payments:
        last = payments[-1]
        expire = to_python(to_string(last.paymentDate), datetime.datetime)+datetime.timedelta(400)
        user.membershipExpirationDate = expire
        user.save()
    return last

def applyToMembers(callback, filter=None):
    import string
    conn = get_conn()
    if filter:
        filter='&((uid=%%s*)%s)' % filter
    else:
        filter='(uid=%s*)' % filter
    for l in string.lowercase:
        users = conn.search_nodes(node_class=AfpyUser, filter = filter % l)
        for u in users:
            callback(u)


