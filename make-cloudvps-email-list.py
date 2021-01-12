#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Generate a list of email addresses for all Cloud VPS project admins who have
# not opted out of email contact via their Wikitech preferences.
#
# The LDAP directory is used as the canonical source of email addresses
# because it is possible to have a developer account in the LDAP directory
# that has never been attached to Wikitech at all (via Striker).
#
# Copyright (c) 2021 Bryan Davis and contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)     # any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
import collections
import ldap
import subprocess
import sys

from keystoneauth1 import session as keystone_session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client


ROLES = collections.OrderedDict([
    ('admin', '2cd63d467f754404bf3746fe63ee0698'),
    ('glanceadmin', '1102f4ff63c3435793d0e4340bf4b04e'),
    ('observer', '47a8370618ea42d49f7047774e75d262'),
    ('projectadmin', '4d8cad783d6342efa8414d7d36fbc034'),
    ('user', 'f473273fac7146b3bdbf22e5d4504f95'),
])


def session(project='observer'):
    """Get a session for the novaobserver user scoped to the given project."""
    # NOTE: The novaobserver username and password are not secret in the WMCS
    # environment. This data is provisioned as /etc/novaobserver.yaml on hosts
    # inside the Cloud VPS environment and stored in labs/private.git which is
    # in no way private (also naming is hard and that repo's name is bad).
    auth = v3.Password(
        auth_url='http://cloudcontrol1003.wikimedia.org:5000/v3',
        password='Fs6Dq2RtG8KwmM2Z',
        username='novaobserver',
        project_id=project,
        user_domain_name='Default',
        project_domain_name='Default',
    )
    return keystone_session.Session(auth=auth)


def keystone_client():
    return client.Client(
        session=session(),
        interface='public',
        timeout=2,
    )


def all_projects():
    """Get a list of all project names."""
    keystone = keystone_client()
    # Ignore the magic 'admin' project
    data = [
        p.name
        for p in keystone.projects.list(enabled=True)
        if p.name != 'admin'
    ]
    return data


def project_users_by_role(name):
    """Get a dict of lists of user ids indexed by role name."""
    keystone = keystone_client()
    # Ignore novaadmin & novaobserver in all user lists
    seen = ['novaadmin', 'novaobserver']
    data = {}
    for role_name, role_id in ROLES.items():
        data[role_name] = [
            r.user['id'] for r in keystone.role_assignments.list(
                project=name, role=role_id)
            if r.user['id'] not in seen
        ]
        seen += data[role_name]
    return data


# Get a list of shell names for all Cloud VPS project admins
admins = []
for project in all_projects():
    users = project_users_by_role(project)
    admins.extend(users['projectadmin'])
admins = set(admins)

l = ldap.initialize('ldap://ldap-labs.eqiad.wikimedia.org', bytes_mode=False)
l.protocol_version = ldap.VERSION3

baseDN = 'dc=wikimedia,dc=org'
searchScope = ldap.SCOPE_SUBTREE

# Get the developer account name and email for all admins
ldap_members = {}
for member in admins:
    # print("member: {}".format(member), file=sys.stderr)
    res = l.search_s(
        baseDN, searchScope, 'uid={}'.format(member), ['cn', 'mail'])
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
    )[0].decode("utf-8").strip().split('\n')[1:])

# Remove users who have set their disablemail flag from the set
for user in email_optout:
    ldap_members.pop(user, None)

for email in ldap_members.values():
    print(email)
