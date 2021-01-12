#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Generate a list of email addresses for all Toolforge users who have
# not opted out of email contact via their Wikitech preferences.
#
# The LDAP directory is used as the canonical source of email addresses
# because it is possible to have a developer account in the LDAP directory
# that has never been attached to Wikitech at all (via Striker).
#
# Copyright © 2021 Wikimedia Foundation and contributors
# CC0 1.0 <https://creativecommons.org/publicdomain/zero/1.0/>
import ldap
import subprocess


l = ldap.initialize('ldap://ldap-labs.eqiad.wikimedia.org', bytes_mode=False)
l.protocol_version = ldap.VERSION3

baseDN = 'dc=wikimedia,dc=org'
searchScope = ldap.SCOPE_SUBTREE

# Get a list of all Toolforge project members
res = l.search_s(baseDN, searchScope, 'cn=project-tools', ['member'])
members = [m.decode("utf-8") for m in res[0][1]['member']]

# Get the developer account name and email for all Toolforge project members
ldap_members = {}
for member in members:
    res = l.search_s(baseDN, searchScope, member.split(',')[0], ['cn', 'mail'])
    # Note: there are a small number of very old accounts that are missing
    # their mail attribute
    if res and 'cn' in res[0][1] and 'mail' in res[0][1]:
        ldap_members[res[0][1]['cn'][0].decode("utf-8")] = res[0][1]['mail'][0].decode("utf-8")

# Get the username for all Wikitech accounts that have opt-ed out of email
# contact by other users.
query = """\
SELECT user_name
FROM user
WHERE user_id IN (
      SELECT up_user
      FROM user_properties
      WHERE up_property='disablemail'
        AND up_value=1
);"""
sql = subprocess.Popen(
    ['/usr/local/bin/sql', 'labswiki'],
    stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
email_optout = set(
    sql.communicate(
        input=query.encode("utf-8")
    )[0].decode("utf-8").strip().split('\n')[1:]
)

# Remove users who have set their disablemail flag from the set
for user in email_optout:
    ldap_members.pop(user, None)

for email in ldap_members.values():
    print(email)
