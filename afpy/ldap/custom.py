# -*- coding: utf-8 -*-
import datetime
from connection import LDAP as BaseLDAP
from node import Node as BaseNode

class Node(BaseNode):
    _field_types = dict(
        birthDate=datetime.date,
        membershipExpirationDate=datetime.date,
        paymentDate=datetime.date,
        paymentAmount=int,
        )

    @property
    def payments(self):
        return self._conn.search_nodes(base_dn=self._dn, filter='(objectClass=payment)')

class LDAP(BaseLDAP):
    node_class = Node

def get_conn():
    return LDAP(section='afpy')

