#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Generate a list of email addresses associated with users who have explictly
# opted out of recieving emails for WMF surveys.
#
# Copyright © 2018 Wikimedia Foundation and contributors
# CC0 1.0 <https://creativecommons.org/publicdomain/zero/1.0/>
from __future__ import print_function

import ldap
import ldap.filter
import urllib2

r = urllib2.urlopen('https://wikitech.wikimedia.org/wiki/Annual_Toolforge_Survey/Opt_out?action=raw')
wikitext = r.read()

in_list = False
optout_users = []
for line in wikitext.splitlines():
    if line == '<!-- BEGIN OPT-OUT LIST -->':
        in_list = True
        continue
    if not in_list:
        continue
    if line == '<!-- END OPT-OUT LIST -->':
        in_list = False
        break
    optout_users.append(line)

l = ldap.open('ldap-labs.eqiad.wikimedia.org')
l.protocol_version = ldap.VERSION3

baseDN = u'dc=wikimedia,dc=org'
searchScope = ldap.SCOPE_SUBTREE

# Get the email addresses for the accounts via LDAP
emails = []
for user in optout_users:
    user = user.decode('utf-8')
    cn = u'cn={}'.format(ldap.filter.escape_filter_chars(user)).encode('utf-8')
    res = l.search_s(baseDN, searchScope, cn, ['mail'])
    # Note: there are a small number of very old accounts that are missing
    # their mail attribute
    if res and 'mail' in res[0][1]:
        emails.append(res[0][1]['mail'][0])

for email in sorted(set(emails)):
    print(email)
