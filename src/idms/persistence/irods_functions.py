import copy
import re
from flask import g, current_app
from irods.column import Criterion
from irods.exception import GroupDoesNotExist
from irods.meta import iRODSMeta
from irods.models import Group, UserMeta
from irods.session import iRODSSession
from idms.persistence.exceptions import (
    TEMPLATE_NOT_CONFIGURED,
    MULTIPLE_GROUPS_EXCEPTION,
)
from idms.persistence.constant import (
    DEFAULT_CONNECT_PARAMETERS,
    ADMIN_CONNECT_PARAMETERS,
)


def admin_session():
    admin_connect_params = copy.deepcopy(DEFAULT_CONNECT_PARAMETERS)
    connect_parms = current_app.config.get("IRODS_INTERNAL", {})
    for key in ADMIN_CONNECT_PARAMETERS:
        if key in connect_parms:
            admin_connect_params[key] = connect_parms.get(key)
    session = iRODSSession(**admin_connect_params)
    return session


def group_exists(groupname):
    try:
        g.sess.groups.get(groupname)
        return True
    except GroupDoesNotExist:
        return False


def get_user(username):
    return g.sess.users.get(username)


def get_group(groupname):
    return g.sess.groups.get(groupname)


def add_groupmember(group, member):
    if not group.hasmember(member.name):
        group.addmember(member.name)


def remove_groupmember(group, member):
    if group.hasmember(member.name):
        group.removemember(member.name)


def rmmeta(o, attr, value):
    for m in o.metadata.get_all(attr):
        if m.value == value:
            o.metadata.remove(attr, value)


def addmeta(o, attr, value):
    for m in o.metadata.get_all(attr):
        if m.value == value:
            return
    o.metadata.add(iRODSMeta(attr, value))


def setmeta(o, attr, value):
    for m in o.metadata.get_all(attr):
        if m.value == value:
            return
    o.metadata[attr] = iRODSMeta(attr, value)


def provide_group(sess, key, purpose, metadata={}, syncback=False):
    """Create or return irods group based on purpose and metadata

    Args:
        key (string): string used for generating group name (project or process name)
        purpose (string): One of : project-users, project-admins, process-admins
        metadata (dict, optional): Metadata to search for or to set on new group. Defaults to {}.
        syncback (bool, optional): Determines if the syncback attr will be set (To sync to AD). Defaults to False.
    """
    # Check if a group already exists
    purpose_attr = current_app.config.get("ATTR_GROUP_TYPE")
    matching_groups = []
    if metadata:
        q = (
            sess.query(Group)
            .filter(Criterion("=", UserMeta.name, purpose_attr))
            .filter(Criterion("=", UserMeta.value, purpose))
        )
        purpose_groups = [sess.groups.get(g[Group.name]) for g in q]
        for group in purpose_groups:
            matching = True
            for k, v in metadata.items():
                try:
                    existing_value = group.metadata.get_one(k).value
                except KeyError:
                    matching = False
                    break
                if existing_value != v:
                    matching = False
                    break
            if not matching:
                continue
            matching_groups.append(group)
    if len(matching_groups) > 1:
        raise MULTIPLE_GROUPS_EXCEPTION
    if len(matching_groups) == 1:
        group = matching_groups[0]
    if len(matching_groups) == 0:
        groupname_template = current_app.config.get("GROUP_TEMPLATES").get(purpose)
        if groupname_template is None:
            raise TEMPLATE_NOT_CONFIGURED
        groupname = unique_groupname(groupname_template, key)
        group = sess.groups.create(groupname)
    setmeta(group, purpose_attr, purpose)
    for k, v in metadata.items():
        setmeta(group, k, v)
    syncback_attr = current_app.config.get("ATTR_AD_SYNC")
    if syncback:
        setmeta(group, syncback_attr, "true")
    else:
        group.metadata._delete_all_values(syncback_attr)
    return group


def unique_groupname(tpl, hint):
    suffix = re.sub('[ #,+"\\<>]', "_", hint)
    groupbase = tpl.format(suffix)
    groupname = groupbase[:64]
    n = 0
    while group_exists(groupname):
        groupname = f"{groupbase[:62]}{n:02d}"
        n += 1
    return groupname
