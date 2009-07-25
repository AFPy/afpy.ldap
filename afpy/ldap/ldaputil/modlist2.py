"""
ldaputil.modlist2 - create modify modlist's with schema knowledge
(c) by Michael Stroeder <michael@stroeder.com>

$Id: modlist2.py,v 1.16 2009/04/03 06:30:32 michael Exp $
"""

__version__ = '$Revision: 1.16 $'.split(' ')[1]


import ldap
from afpy.ldap.ldaputil import schema


def modifyModlist(
  sub_schema,
  old_entry,
  new_entry,
  ignore_attr_types=None,
  ignore_oldexistent=0
):
  """
  Build differential modify list for calling LDAPObject.modify()/modify_s()

  sub_schema
      Instance of schema.SubSchema
  old_entry
      Dictionary holding the old entry
  new_entry
      Dictionary holding what the new entry should be
  ignore_attr_types
      List of attribute type names to be ignored completely
  ignore_oldexistent
      If non-zero attribute type names which are in old_entry
      but are not found in new_entry at all are not deleted.
      This is handy for situations where your application
      sets attribute value to '' for deleting an attribute.
      In most cases leave zero.
  """
  # Type checking
  assert isinstance(sub_schema,schema.SubSchema)
  assert isinstance(old_entry,schema.Entry)
  assert isinstance(new_entry,schema.Entry)

  # Performance optimization
  AttributeType = ldap.schema.AttributeType
  MatchingRule = ldap.schema.MatchingRule

  # Build a dictionary with key of all attribute types to be ignored
  ignore_attr_types = {}.fromkeys([
    sub_schema.getoid(AttributeType,attr_type)
    for attr_type in (ignore_attr_types or [])
  ])

  # Start building the modlist result
  modlist = []

  # Sanitize new_entry
  for a in new_entry.keys():
    # Filter away list items which are empty strings or None
    new_entry[a] = filter(None,new_entry[a])
    # Check for attributes with empty value lists
    if not new_entry[a]:
      # Remove the empty attribute
      del new_entry[a]

  for attrtype in new_entry.keys():

    if ignore_attr_types.has_key(sub_schema.getoid(AttributeType,attrtype)):
      # This attribute type is ignored
      continue

    # Filter away list items which are empty strings or None
    new_value = new_entry[attrtype]
    old_value = filter(None,old_entry.get(attrtype,[]))

    # We have to check if attribute value lists differs
    old_value_dict={}.fromkeys(old_value)
    new_value_dict={}.fromkeys(new_value)
    delete_values = 0
    for v in old_value:
      if not new_value_dict.has_key(v):
        delete_values = 1
        break
    if delete_values:
      try:
        at_eq_mr =  sub_schema.get_inheritedattr(AttributeType,attrtype,'equality')
      except KeyError:
        at_eq_mr = None
      if at_eq_mr and attrtype.lower()!='objectclass':
        mr_obj =  sub_schema.get_obj(MatchingRule,at_eq_mr)
        if mr_obj:
          modlist.append((ldap.MOD_DELETE,attrtype,old_value_dict.keys()))
        else:
          modlist.append((ldap.MOD_DELETE,attrtype,None))
      else:
        modlist.append((ldap.MOD_DELETE,attrtype,None))
      modlist.append((ldap.MOD_ADD,attrtype,new_value))
    else:
      add_values = []
      for v in new_value:
        if not old_value_dict.has_key(v):
          add_values.append(v)
      if add_values:
        modlist.append((ldap.MOD_ADD,attrtype,add_values))

  # Remove all attributes of old_entry which are not present
  # in new_entry at all
  if not ignore_oldexistent:
    for attrtype in old_entry.keys():
      try:
        old_value = old_entry[attrtype]
      except KeyError:
        continue
      else:
        if old_value and \
           not new_entry.has_key(attrtype) and \
           not ignore_attr_types.has_key(sub_schema.getoid(AttributeType,attrtype)):
          try:
            at_eq_mr =  sub_schema.get_inheritedattr(AttributeType,attrtype,'equality')
          except KeyError:
            at_eq_mr = None
          if at_eq_mr:
            mr_obj =  sub_schema.get_obj(MatchingRule,at_eq_mr)
            if mr_obj:
              modlist.append((ldap.MOD_DELETE,attrtype,old_value))
            else:
              modlist.append((ldap.MOD_DELETE,attrtype,None))
          else:
            modlist.append((ldap.MOD_DELETE,attrtype,None))


  return modlist # modifyModlist()
