# -*- coding: utf-8 -*-
import unittest
import datetime
from afpy.ldap import custom as ldap
import afpy.ldap.utils

conn = ldap.get_conn()

def test_payments():
    user = conn.get_user('gawel')
    payments = user.payments
    assert len(payments) > 2

    payment = payments[0]
    assert isinstance(payment.paymentDate, datetime.date) == True, payment._data

