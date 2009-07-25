"""
ldaputil.schema: More functionality for ldap.schema

(c) by Michael Stroeder <michael@stroeder.com>

This module is distributed under the terms of the
GPL (GNU GENERAL PUBLIC LICENSE) Version 2
(see http://www.gnu.org/copyleft/gpl.html)

$Id: schema.py,v 1.26 2009/07/01 22:25:58 michael Exp $
"""

import ldap.schema,ldap.schema.subentry
from ldap.schema.models import AttributeType


class SubSchema(ldap.schema.subentry.SubSchema):

  def __init__(self,sub_schema_sub_entry,subentry_dn=None):
    ldap.schema.subentry.SubSchema.__init__(self,sub_schema_sub_entry)
    self.subentry_dn = subentry_dn
    self.no_user_mod_attr_oids = self.determine_no_user_mod_attrs()

  def determine_no_user_mod_attrs(self):
    result = {}.fromkeys([
      a.oid
      for a in self.sed[ldap.schema.AttributeType].values()
      if a.no_user_mod
    ])
    return result # determine_no_user_mod_attrs()

  def get_associated_name_forms(self,structural_object_class_oid):
    """
    Returns a list of instances of ldap.schema.models.NameForm
    representing all name forms associated with the current structural
    object class of this entry.

    The structural object class is determined by attribute
    'structuralObjectClass' if it exists or by calling
    method get_structural_oc() if not.
    """
    if structural_object_class_oid is None:
      return []
    structural_object_class_obj = self.get_obj(ldap.schema.models.ObjectClass,structural_object_class_oid)
    if structural_object_class_obj:
      structural_object_class_names = [
        oc_name.lower()
        for oc_name in structural_object_class_obj.names or ()
      ]
    else:
      structural_object_class_names = ()
    result = []
    for name_form_oid,name_form_obj in self.sed[ldap.schema.models.NameForm].items():
      if not name_form_obj.obsolete and (
           name_form_obj.oc==structural_object_class_oid or \
           name_form_obj.oc.lower() in structural_object_class_names
      ):
        result.append(name_form_obj)
    return result # get_associated_name_forms()

  def get_rdn_variants(self,structural_object_class_oid):
    import msbase
    rdn_variants = []
    for name_form_obj in self.get_associated_name_forms(structural_object_class_oid):
      rdn_variants.append((name_form_obj,name_form_obj.must))
      for i in msbase.combinations(name_form_obj.may):
        rdn_variants.append((name_form_obj,name_form_obj.must+i))
    return rdn_variants # get_rdn_variants()

  def get_rdn_templates(self,structural_object_class_oid):
    """convert the tuple RDN combinations to RDN template strings"""
    rdn_attr_tuples = {}.fromkeys([
      rdn_attr_tuple
      for name_form_obj,rdn_attr_tuple in self.get_rdn_variants(structural_object_class_oid)
    ]).keys()
    return [
      '+'.join([
        '%s=' % (attr_type)
        for attr_type in attr_types
      ])
      for attr_types in rdn_attr_tuples
    ] # get_rdn_templates()

  def get_applicable_name_form_objs(self,dn,structural_object_class_oid):
    """
    Returns a list of instances of ldap.schema.models.NameForm
    representing all name form associated with the current structural
    object class of this entry and matching the current RDN.
    """
    if dn:
      rdn_list=ldap.dn.str2dn(dn)[0]
      current_rdn_attrs = [ attr_type.lower() for attr_type,attr_value,dummy in rdn_list ]
      current_rdn_attrs.sort()
    else:
      current_rdn_attrs = []
    result=[]
    for name_form_obj,rdn_attr_tuple in self.get_rdn_variants(structural_object_class_oid):
      name_form_rdn_attrs = [ attr_type.lower() for attr_type in rdn_attr_tuple ]
      name_form_rdn_attrs.sort()
      if current_rdn_attrs==name_form_rdn_attrs:
        result.append(name_form_obj)
    return result # get_current_name_form_objs()

  def get_possible_dit_structure_rules(self,dn,structural_object_class_oid):
    name_form_identifiers = ldap.cidict.cidict({})
    for name_form_obj in self.get_applicable_name_form_objs(dn,structural_object_class_oid):
      name_form_identifiers[name_form_obj.oid] = None
    dit_struct_ruleids = {}
    for dit_struct_rule_obj in self.sed[ldap.schema.models.DITStructureRule].values():
      name_form_obj = self.get_obj(ldap.schema.models.NameForm,dit_struct_rule_obj.form)
      if (name_form_obj.oid in name_form_identifiers) and \
         (self.getoid(ldap.schema.models.ObjectClass,name_form_obj.oc)==structural_object_class_oid):
        dit_struct_ruleids[dit_struct_rule_obj.ruleid]=dit_struct_rule_obj
    return dit_struct_ruleids.keys() # get_possible_dit_structure_rules()

  def get_subord_structural_oc_names(self,ruleid):
    subord_structural_oc_oids = {}
    subord_structural_ruleids = {}
    for dit_struct_rule_obj in self.sed[ldap.schema.models.DITStructureRule].values():
      for sup in dit_struct_rule_obj.sup:
        if sup==ruleid:
          subord_structural_ruleids[dit_struct_rule_obj.ruleid]=None
          name_form_obj = self.get_obj(ldap.schema.models.NameForm,dit_struct_rule_obj.form)
          if name_form_obj:
            subord_structural_oc_oids[self.getoid(ldap.schema.models.ObjectClass,name_form_obj.oc)]=None
    result = []
    for oc_oid in subord_structural_oc_oids.keys():
      oc_obj = self.get_obj(ldap.schema.models.ObjectClass,oc_oid)
      if oc_obj and oc_obj.names:
        result.append(oc_obj.names[0])
      else:
        result.append(oc_oid)
    return subord_structural_ruleids.keys(),result # get_subord_structural_oc_names()

  def get_superior_structural_oc_names(self,ruleid):
    try:
      dit_struct_rule_obj = self.sed[ldap.schema.models.DITStructureRule][ruleid]
    except KeyError:
      return None
    else:
      result=[];sup_ruleids=[]
      for sup_ruleid in dit_struct_rule_obj.sup:
        try:
          sup_dit_struct_rule_obj = self.sed[ldap.schema.models.DITStructureRule][sup_ruleid]
        except KeyError:
          pass
        else:
          if sup_dit_struct_rule_obj.form:
            sup_name_form_obj = self.get_obj(ldap.schema.models.NameForm,sup_dit_struct_rule_obj.form)
            if sup_name_form_obj:
              sup_ruleids.append(sup_ruleid)
              result.append(sup_name_form_obj.oc)
    return sup_ruleids,result # get_superior_structural_oc_names()


class Entry(ldap.schema.models.Entry):
  """
  Base class with some additional basic methods
  """

  def get_structural_oc(self):
    try:
      structural_object_class_oid = self._s.getoid(
        ldap.schema.models.ObjectClass,
        self['structuralObjectClass'][-1]
      )
    except (KeyError,IndexError):
      structural_object_class_oid = self._s.get_structural_oc(self['objectClass'])
    return structural_object_class_oid

  def get_possible_dit_structure_rules(self,dn):
    try:
      structural_oc = self.get_structural_oc()
    except KeyError:
      return None
    else:
      return self._s.get_possible_dit_structure_rules(dn,structural_oc)

  def get_rdn_templates(self):
    return self._s.get_rdn_templates(self.get_structural_oc())


#------------------------------------------------
# Work arounds for older versions of python-ldap
#------------------------------------------------

# Do not treat the BitString and OctetString syntaxes as not human-readable
try:
  del ldap.schema.NOT_HUMAN_READABLE_LDAP_SYNTAXES['1.3.6.1.4.1.1466.115.121.1.6']
  del ldap.schema.NOT_HUMAN_READABLE_LDAP_SYNTAXES['1.3.6.1.4.1.1466.115.121.1.40']
except KeyError:
  pass

