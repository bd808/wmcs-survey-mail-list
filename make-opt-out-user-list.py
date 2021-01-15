#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Generate a list of users who have explictly
# opted out of recieving emails for WMF surveys.
#
# Copyright © 2021 Wikimedia Foundation and contributors
# CC0 1.0 <https://creativecommons.org/publicdomain/zero/1.0/>
import ldap.filter
import urllib

r = urllib.request.urlopen(
    "https://wikitech.wikimedia.org/wiki/Annual_Toolforge_Survey/Opt_out?action=raw"
)
wikitext = r.read().decode("utf-8")

in_list = False
optout_users = []
for line in wikitext.splitlines():
    if line == "<!-- BEGIN OPT-OUT LIST -->":
        in_list = True
        continue
    if not in_list:
        continue
    if line == "<!-- END OPT-OUT LIST -->":
        in_list = False
        break
    optout_users.append(line)

# Output list of users
for user in optout_users:
    cn = ldap.filter.escape_filter_chars(user)
    print(cn)
