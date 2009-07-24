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

class LDAP(BaseLDAP):
    node_class = Node

