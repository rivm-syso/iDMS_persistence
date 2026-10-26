"""REST api for project database
Returns:
    [type]: [description]

The following endpoints will be exposed under /api/1.0:
PROJECTS:
/projects                                                                   GET, POST
/projects/<id>                                                              GET, PUT
/projects/<id>/tags                                                         GET
/projects/<id>/users                                                        GET, POST
/projects/<id>/users/<id>                                                   GET, DELETE
/projects/<id>/managers                                                     GET, POST
/projects/<id>/managers/<id>                                                GET, DELETE
/projects/<id>/processes                                                    GET, POST
/projects/<id>/processes/<id>                                               GET, PUT, DELETE
/projects/<id>/processes/<id>/effective_referencedata/                      GET
/projects/<id>/processes/<id>/referencedata/<id>                            GET, PUT, DELETE
/projects/<id>/processgroups                                                GET, POST
/projects/<id>/processgroups/<id>                                           GET, PUT, DELETE
/projects/<id>/processgroups/<id>/dependencies                              GET
/projects/<id>/processgroups/<id>/processes                                 GET, POST
/projects/<id>/processgroups/<id>/processes/<id>                            GET, PUT, DELETE
/projects/<id>/processgroups/<id>/processes/<id>/dependencies               GET, POST
/projects/<id>/processgroups/<id>/processes/<id>/dependencies/<id>          GET, PUT
/projects/<id>/processgroups/<id>/processes/<id>/referencedata              GET, POST
/projects/<id>/processgroups/<id>/processes/<id>/referencedata/<id>         GET, PUT
/projects/<id>/processgroups/<id>/processes/<id>/effective_referencedataversion GET

PROCESSES
/processes                                                                  GET, POST
/processes/<id>                                                             GET, PUT, DELETE
/processes/<id>/references                                                  GET
/processes/<id>/managers                                                    GET, POST
/processes/<id>/managers/<id>                                               GET, DELETE

REFERENCE DATA
/reference                                                                  GET, POST
/reference/<id>                                                             GET, PUT, DELETE
/reference/<id>                                                             GET, PUT, DELETE
/reference/<id>/tags                                                        GET
/reference/<id>/versions                                                    GET, POST
/reference/<id>/versions/<versionid>                                     GET, PUT, DELETE
/reference/<id>/versionreference/<versionid>
"""

import logging
import re
import uuid
from datetime import datetime

import git
from dateutil import parser as dateparser
from flask import Blueprint, abort, current_app, g, jsonify, request
from flask_marshmallow import Marshmallow
from idms.common.constants.attribute_names import ATTR_GROUP_EXTERNAL
from sqlalchemy import desc

from idms.persistence.auth import auth
from idms.persistence.enum import OBJECTS
from idms.persistence.exceptions import GROUP_NOT_FOUND
from idms.persistence.irods_functions import (
    add_groupmember,
    admin_session,
    get_group,
    get_user,
    provide_group,
    remove_groupmember,
)
from idms.persistence.models.Model import (
    Contact,
    Process,
    Process2,
    ProcessDependency,
    ProcessGroup,
    ProcessRef,
    Project,
    ReferenceData,
    ReferenceDataImport,
    ReferenceDataVersion,
    ReferenceDataVersionForProcess,
    ReferenceDataVersionForProcessRef,
    db,
)
from idms.persistence.notifications import notify
from idms.persistence.schemas.Schema import (
    ContactSchema,
    ContactsSchema,
    Process2Schema,
    ProcessDependencySchema,
    Processes2Schema,
    ProcessesSchema,
    ProcessgroupSchema,
    ProcessRefSchema,
    ProjectSchema,
    ProjectsSchema,
    ReferenceDataImportSchema,
    ReferenceDataSchema,
    ReferenceDataVersionForProcessRefSchema,
    ReferenceDataVersionForProcessSchema,
    ReferenceDataVersionSchema,
)

log = logging.getLogger(__name__)

bp = Blueprint("api_v10", __name__, url_prefix="/api/1.0")
ma = Marshmallow(bp)

contact_schema = ContactSchema()
contacts_schema = ContactsSchema(many=True)

project_schema = ProjectSchema()
projects_schema = ProjectsSchema(many=True)
process_schema = ProcessesSchema()
processes_schema = ProcessesSchema(many=True)

process2_schema = Process2Schema()
processes2_schema = Processes2Schema(many=True)

processgroup_schema = ProcessgroupSchema()
processgroups_schema = ProcessgroupSchema(many=True)

processref_schema = ProcessRefSchema()
processrefs_schema = ProcessRefSchema(many=True)

processdependency_schema = ProcessDependencySchema()
processdependencies_schema = ProcessDependencySchema(many=True)
referencedataversion_for_procesref_schema = ReferenceDataVersionForProcessRefSchema()
referencedataversions_for_procesref_schema = ReferenceDataVersionForProcessRefSchema(
    many=True
)
referencedataversion_for_process_schema = ReferenceDataVersionForProcessSchema()
referencedataversions_for_process_schema = ReferenceDataVersionForProcessSchema(
    many=True
)


referencedata_schema = ReferenceDataSchema()
referencedatas_schema = ReferenceDataSchema(many=True)
referencedataversion_schema = ReferenceDataVersionSchema()
referencedataversions_schema = ReferenceDataVersionSchema(many=True)
referencedataimport_schema = ReferenceDataImportSchema()

EPOCH = "1970-01-01T01:00:00"


def iso2dt(timestr):
    """Convert ISO8601 datetime string to datetime

    Args:
        timestr (str): ISO8601 datetime string
    """
    if timestr is None:
        timestr = EPOCH
    return dateparser.parse(timestr)


def displayname():
    try:
        user_displayname = g.user.metadata.get_one("sys::ad::displayName").value
    except KeyError:
        user_displayname = "-----"
    return user_displayname


def is_valid_uuid(val):
    try:
        # If val is already a UUID object, this will also work
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def string2label(sentence, length):
    """Convert string to short label"""
    parts = re.sub('[ #,+"\\<>]', "_", sentence).split("_")
    partlength = length // len(parts)
    return "".join([p[:partlength].title() for p in parts])


def project_from_id(projectid):
    """Find project in database based on projectid.
    projectid Can be the name or the numeric id

    Args:
        projectid (int or str): Either a projectid or a projectname

    Returns:
        [Project]: Project db record
    """
    if str(projectid).isnumeric():
        project = Project.query.get(projectid)
    else:
        project = Project.query.filter(Project.name == projectid).one_or_none()
    return project


def process_from_id(projectid, processid):
    project = project_from_id(projectid)
    if project is None:
        return None
    project_processes = processes_for_project(project)
    log.error(f"for projectid: '{projectid}' found {len(project_processes)} processes")
    if str(processid).isnumeric():
        processes = [
            project_process
            for project_process in project_processes
            if project_process.id == int(processid)
        ]
    else:
        processes = [
            project_process
            for project_process in project_processes
            if project_process.name == processid
        ]
        log.error(
            f"for projectid: '{projectid}' and process-name {processid} found {len(processes)} matching processes"
        )
    if len(processes) != 1:
        return None
    return processes[0]


def processgroup_from_id(projectid, processgroupid):
    project = project_from_id(projectid)
    if project is None:
        return None
    if str(processgroupid).isnumeric():
        processgroup = ProcessGroup.query.filter(
            ProcessGroup.projectid == project.id, ProcessGroup.id == processgroupid
        ).one_or_none()
    else:
        processgroup = ProcessGroup.query.filter(
            ProcessGroup.projectid == project.id, ProcessGroup.name == processgroupid
        ).one_or_none()
    return processgroup


def process2_from_id(processid):
    if str(processid).isnumeric():
        process = Process2.query.get(processid)
    else:
        process = Process2.query.filter(Process2.name == processid).one_or_none()
    return process


def processref_from_id(projectid, processgroupid, processrefid):
    processgroup = processgroup_from_id(projectid, processgroupid)
    if processgroup is None:
        return None
    if str(processrefid).isnumeric():
        processref = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id, ProcessRef.id == processrefid
        ).one_or_none()
    else:
        processref = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id,
            ProcessRef.name == processrefid,
        ).one_or_none()
    return processref


def processdep_from_id(projectid, processgroupid, processrefid, processdepid):
    processref = processref_from_id(projectid, processgroupid, processrefid)
    if processref is None:
        return None
    if str(processdepid).isnumeric():
        return ProcessDependency.query.filter(
            ProcessDependency.processrefid == processref.id,
            ProcessDependency.id == processdepid,
        ).one_or_none()
    else:
        # TODO : optimize this query (don't know how)
        processdeps = ProcessDependency.query.filter(
            ProcessDependency.processrefid == processref.id
        ).all()
        for pd in processdeps:
            pref = ProcessRef.query.filter(
                ProcessRef.name == processdepid, ProcessRef.id == pd.depends_on
            ).one_or_none()
            if pref:
                return pd
    return None


def reference_from_id(referenceid):
    """Find reference dataset in database based on referenceid.
    referenceid Can be the name or the numeric id

    Args:
        referenceid (int or str): Either a referenceid or a referencename

    Returns:
        [ReferenceData]: ReferenceData db record
    """
    if str(referenceid).isnumeric():
        reference = ReferenceData.query.get(referenceid)
    else:
        reference = ReferenceData.query.filter(
            ReferenceData.name == referenceid
        ).one_or_none()
    return reference


def refdataversion_from_id(prrdvid):
    if str(prrdvid).isnumeric():
        return ReferenceDataVersion.query.get(prrdvid)
    return None


def refdataversion_for_processref_from_id(prrdvid):
    if str(prrdvid).isnumeric():
        return ReferenceDataVersionForProcessRef.query.get(prrdvid)
    return None


def refdataversion_for_process_from_id(prrdvid):
    if str(prrdvid).isnumeric():
        return ReferenceDataVersionForProcess.query.get(prrdvid)
    return None


def import_state_for_referenceid(referenceid):
    """Find importer_state dataset in database based on referenceid.
    referenceid, since this is an 1-to-1 table.

    Args:
        referenceid (int or str): Either a referenceid or a referencename

    Returns:
        [ReferenceData]: ReferenceData db record
    """
    importer_state = None
    reference = reference_from_id(referenceid)
    if reference:
        importer_state = ReferenceDataImport.query.filter(
            ReferenceDataImport.referenceid == reference.id
        ).one_or_none()
    return importer_state


def is_manager(obj):
    """Check if current_user is a manager for supplied project or process

    Args:
        object (Project or Process): Project or process instance

    Returns:
        boolean: True if current_user is manager
    """
    if hasattr(obj, "owner"):
        user_is_owner = obj.owner == g.username
    else:
        user_is_owner = False

    user_is_manager = False
    if hasattr(obj, "manager_group"):
        mg = get_group(obj.manager_group)
        user_is_manager = mg.hasmember(g.username)

    log.debug(
        f"Permissions on {obj} - {obj.name} for user {g.username}: is_owner: {user_is_owner}, is_manager: {user_is_manager}"
    )
    return user_is_owner or user_is_manager


def userdict(u):
    result = {"username": u.name}
    try:
        user_displayname = u.metadata.get_one("sys::ad::displayName").value
    except KeyError:
        user_displayname = u.name
    result["displayName"] = user_displayname
    return result


def handle_external_groups(obj, groupattr, objectname):
    if request.method == "GET":
        groupname = getattr(obj, groupattr)
        group = get_group(groupname)
        avus = group.metadata.get_all(ATTR_GROUP_EXTERNAL)
        return jsonify([avu.value for avu in avus])
    elif request.method == "POST":
        if not is_manager(obj):
            return (
                jsonify({"message": f"Access denied for {objectname} {obj.id}"}),
                401,
            )
        externalgroup = request.json.get("groupname")
        if externalgroup is None:
            return jsonify({"message": "Invalid request data"}), 400
        groupname = getattr(obj, groupattr)
        log.debug(f"Add external group {groupname} to group {groupname}")
        sess = admin_session()
        group = sess.groups.get(groupname)
        externalgroups = [
            avu.value for avu in group.metadata.get_all(ATTR_GROUP_EXTERNAL)
        ]
        if not externalgroup in externalgroups:
            group.metadata.add(ATTR_GROUP_EXTERNAL, externalgroup)
            if obj.__class__.__name__ == "Project":
                notify(
                    obj.id,
                    OBJECTS.project,
                    displayname(),
                    getattr(OBJECTS, groupattr),
                    groupname,
                    f"Group {groupname} gets members from remote group {externalgroup}",
                )
        return jsonify({"message": "SUCCESS"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def handle_external_group(obj, groupattr, objectname, externalgroup):
    groupname = getattr(obj, groupattr)
    group = get_group(groupname)
    avus = group.metadata.get_all(ATTR_GROUP_EXTERNAL)
    externalgroups = [avu.value for avu in avus]
    if externalgroup not in externalgroups:
        return (
            jsonify(
                {
                    "message": f"Group {externalgroup} is not an external source for group {groupname}"
                }
            ),
            400,
        )
    if request.method == "GET":
        return jsonify({"externalgroup": externalgroup}), 200
    elif request.method == "DELETE":
        if not is_manager(obj):
            return (
                jsonify({"message": f"Access denied for {objectname} {obj.id}"}),
                401,
            )
        log.debug(f"Remove external group {externalgroup} from group {groupname}")
        sess = admin_session()
        group = sess.groups.get(groupname)
        group.metadata.remove(ATTR_GROUP_EXTERNAL, externalgroup)
        notify(
            obj.id,
            OBJECTS.project,
            displayname(),
            getattr(OBJECTS, groupattr),
            groupname,
            f"External group {externalgroup} was removed from group {groupname}",
        )
        return jsonify({"message": "SUCCESS"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def handle_groupmembers(obj, groupattr, objectname):
    """_Process get/post requests for getting/adding group members

    Args:
        object (Process or Project): Process or Project object that this change applies to
        groupattr (str): name of object attribute that holds the AD group name
        objectname (str): descriptive name for object type (eg 'process')

    Returns:
        tuple jsondata, http_return_code
    """
    if request.method == "GET":
        groupname = getattr(obj, groupattr)
        group = get_group(groupname)
        formatted_members = [userdict(member) for member in group.members]
        return jsonify(formatted_members), 200
    elif request.method == "POST":
        if not is_manager(obj):
            return (
                jsonify({"message": f"Access denied for {objectname} {obj.id}"}),
                401,
            )
        username = request.json.get("username")
        if username is None:
            return jsonify({"message": "Invalid request data"}), 400
        groupname = getattr(obj, groupattr)
        log.debug(f"Add {username} to group {groupname}")
        sess = admin_session()
        group = sess.groups.get(groupname)
        if not group.hasmember(username):
            group.addmember(username)
            if obj.__class__.__name__ == "Project":
                notify(
                    obj.id,
                    OBJECTS.project,
                    displayname(),
                    getattr(OBJECTS, groupattr),
                    groupname,
                    f"User {username} was added",
                )
        return jsonify({"message": "SUCCESS"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def handle_groupmember(obj, groupattr, objectname, username):
    groupname = getattr(obj, groupattr)
    group = get_group(groupname)
    if not group.hasmember(username):
        return jsonify({"message": f"User {username} is not in group {groupname}"}), 400
    user = get_user(username)
    if request.method == "GET":
        return userdict(user), 200
    elif request.method == "DELETE":
        if not is_manager(obj):
            return (
                jsonify({"message": f"Access denied for {objectname} {obj.id}"}),
                401,
            )
        log.debug(f"Remove {username} from group {groupname}")
        sess = admin_session()
        group = sess.groups.get(groupname)
        user = sess.users.get(username)
        remove_groupmember(group, user)
        notify(
            obj.id,
            OBJECTS.project,
            displayname(),
            getattr(OBJECTS, groupattr),
            groupname,
            f"User {username} was removed",
        )
        return jsonify({"message": "SUCCESS"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def handle_create_contact(entity_id, entity_type, entity_name, data):
    name = data.get("name")
    email = data.get("email")
    primary = data.get("primary", 0)
    if not (name and email):  # both name and email have to be set
        return jsonify({"message": "missing values in create contact request"}), 400
    log.debug(
        f"New contact {name} for {entity_type} {entity_name} created by {g.username}"
    )
    number_of_contacts = Contact.query.filter(
        Contact.entity_id == entity_id, Contact.entity_type == entity_type
    ).count()
    # the first contact is automatically the primary contact!
    if number_of_contacts == 0:
        primary = 1
    new_contact = Contact(
        entity_id,
        entity_type,
        name,
        email,
        primary,
        notify_data=request.json.get("notify_data", 0),
        notify_pipeline=request.json.get("notify_pipeline", 0),
        notify_errors=request.json.get("notify_errors", 0),
        notify_config_changes=request.json.get("notify_config_changes", 0),
    )
    db.session.add(new_contact)
    db.session.commit()
    notify(
        entity_id,
        entity_type,
        displayname(),
        OBJECTS.contact,
        name,
        f"A contact was added to {entity_type} {entity_name}",
    )
    return contact_schema.jsonify(new_contact), 201


def handle_change_contact(contact, entity_name, data):
    log.debug(f"Contact {contact} for reference {entity_name} modified by {g.username}")
    for attr in [
        "name",
        "email",
        "notify_data",
        "notify_pipeline",
        "notify_errors",
        "notify_config_changes",
    ]:
        if attr in data:
            setattr(contact, attr, data.get(attr))
    if "primary" in data:
        new_primary_value = data.get("primary")
        # check first if this contact is the last primary contact
        if (contact.primary == 1) and (new_primary_value == 0):
            count_primary_contacts = Contact.query.filter(
                Contact.entity_id == contact.entity_id,
                Contact.entity_type == contact.entity_type,
                Contact.primary == 1,
            ).count()
            if count_primary_contacts == 1:
                return (
                    jsonify(
                        {
                            "message": "There has to be at least one primary contact!",
                            "contact": contact_schema.dump(contact),
                        }
                    ),
                    405,
                )
        contact.primary = data.get("primary")
    db.session.commit()
    return contact_schema.dump(contact), 200


#################
# TEST endpoints
#################


@bp.route("/hello", methods=["GET"])
def hello_test():
    return jsonify({"message": "Hello World!"})


@bp.route("/secure_hello", methods=["GET"])
@auth.login_required
def secure_hello_test():
    return jsonify({"message": f"Hello {g.username}!"})


###################
# /contacts
###################


@bp.route("/contacts", methods=["GET"])
def handle_contacts():
    all_contacts = Contact.query.all()
    dump = contacts_schema.dump(all_contacts)
    return jsonify(dump)


###########
# /projects
###########


@bp.route("/projects", methods=["POST"])
@auth.login_required
def auth_handle_projects():
    return handle_projects()


@bp.route("/projects", methods=["GET"])
def handle_projects():
    if request.method == "GET":
        """Retrieve a list of all known projects"""
        all_projects = Project.query.all()
        dump = projects_schema.dump(all_projects)
        return jsonify(dump)
    elif request.method == "POST":
        """Create a new project with name 'name'"""
        # Check for membership of project creators group
        project_admins_groupname = current_app.config.get("PROJECT_CREATORS_GROUP")

        try:
            admin_group = get_group(project_admins_groupname)
            is_project_admin = admin_group.hasmember(g.username)
        except GROUP_NOT_FOUND:
            return jsonify({"message": "Cannot resolve project admins group"}), 401
        if not is_project_admin:
            return (
                jsonify({"message": "Access denied while trying to create a project"}),
                401,
            )

        log.debug("Create new project")
        # Test if name is supplied
        projectname = request.json.get("name")
        if not projectname:
            log.error("Projectname not supplied")
            return (
                jsonify({"message": "Invalid request data: no project name supplied"}),
                400,
            )
        log.debug("Projectname is {}".format(projectname))
        if len(projectname) > 24:
            log.error("Projectname {} is too long".format(projectname))
            return jsonify({"message": "Max projectname length(24) exceeded"}), 400
        # Test if project does not exist already
        project = Project.query.filter_by(name=projectname).count()
        if project:
            log.error("Projectname {} already exists".format(projectname))
            return jsonify({"message": "Project already exists"}), 409
        # Create the new project
        project = Project(projectname, g.username)
        # TODO: test user authorization
        db.session.add(project)
        db.session.commit()
        return project_schema.jsonify(project), 202


##########################
# /sys/projects/projectid>
##########################


@bp.route("/sys/projects/<projectid>", methods=["PUT"])
@auth.login_required
def handle_sys_project(projectid):
    """Handles updates to the projects settings by the system user

    Used to update project settings after the projectcreator has run
    Will not update last_updated field

    Args:
        project ([type]): [description]
    """
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    log.debug(f"Update project {project.name} by system")
    dt_properties = ["last_verified"]
    # TODO : fix this user
    if g.username == current_app.config.get("SYSTEM_USER"):
        for key, value in request.json.items():
            if key in Project.sys_change_allowed:
                if key == "service_account" and value:
                    try:
                        user = get_user(value)
                    except:
                        return (
                            jsonify({"message": f"Service account {value} not found"}),
                            501,
                        )
                    try:
                        project_users_group = get_group(project.user_group)
                    except:
                        return (
                            jsonify(
                                {"message": f"Project users for {project} not found"}
                            ),
                            501,
                        )
                    try:
                        add_groupmember(project_users_group, user)
                    except:
                        return (
                            jsonify(
                                {
                                    "message": f"Error adding {value} to {project_users_group}"
                                }
                            ),
                            501,
                        )
                log.debug(f"Set {key} for {project.name} to {value}")
                setattr(project, key, value)
                notify(
                    project.id,
                    OBJECTS.project,
                    "system",
                    OBJECTS.prop,
                    key,
                    f"The system changed {key} to {value}",
                )
            elif key in dt_properties:
                log.debug(f"Set {key} for {project.name} to {value}")
                setattr(project, key, iso2dt(value))
        db.session.commit()
        return project_schema.jsonify(project), 200
    else:
        log.debug(f"Unauthorized system PUT request by {g.username}")
        return (
            jsonify({"message": "Access denied for project {}".format(projectid)}),
            401,
        )


#######################
# /projects/<projectid>
#######################


@bp.route("/projects/<projectid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_project_update(projectid):
    return handle_project_update(projectid)


@bp.route("/projects/<projectid>", methods=["GET"])
def handle_project_update(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    if request.method == "GET":
        return jsonify(project_schema.dump(project)), 200
    elif request.method == "PUT":
        log.debug(f"Update to project {project.name} by {g.username}")
        # user should be project manager
        if not is_manager(project):
            return (
                jsonify({"message": "Access denied for project {}".format(projectid)}),
                401,
            )
        for key in request.json:
            if key in Project.change_allowed:
                log.debug(
                    f"Attr {key} for project {project.name} set to {request.json[key]}"
                )
                setattr(project, key, request.json[key])
                project.last_updated = datetime.now()
        db.session.commit()
#EVW REMOVE        check_project(project.id)
        return project_schema.jsonify(project), 202
    elif request.method == "DELETE":
        if not current_app.config.get("ENABLE_DELETE_PROJECT", False):
            return (
                jsonify(
                    {
                        "message": "Delete project {}: project deletion is globally disabled".format(
                            projectid
                        )
                    }
                ),
                501,
            )  # Not implemented.
        log.debug(f"Project {project.name} deleted by {g.username}")
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


################################
# /projects/<projectid>/contacts
################################
@bp.route("/projects/<projectid>/contacts", methods=["POST"])
@auth.login_required
def auth_handle_project_contacts_authorized(projectid):
    return handle_project_contacts_authorized(projectid)


@bp.route("/projects/<projectid>/contacts", methods=["GET"])
def handle_project_contacts_authorized(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404

    if request.method == "GET":
        contacts = Contact.query.filter(
            Contact.entity_id == project.id, Contact.entity_type == OBJECTS.project
        ).all()
        return jsonify(contacts_schema.dump(contacts))

    elif request.method == "POST":
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {project.name}"}), 401
        json, code = handle_create_contact(
            project.id, OBJECTS.project, project.name, request.json
        )
        return json, code
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


##############################
# /projects/<projectid>/external/users/groups
##############################


@bp.route("/projects/<projectid>/external/<usertype>/groups", methods=["GET", "POST"])
@auth.login_required
def project_externals(projectid, usertype):
    MAP = {"users": "user_group", "managers": "manager_group"}
    project = project_from_id(projectid)
    return handle_external_groups(project, MAP.get(usertype), "project")


##############################
# /projects/<projectid>/external/users/groups/<group>
##############################


@bp.route(
    "/projects/<projectid>/external/<usertype>/groups/<externalgroup>",
    methods=["GET", "DELETE"],
)
@auth.login_required
def project_external(projectid, usertype, externalgroup):
    MAP = {"users": "user_group", "managers": "manager_group"}
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    return handle_external_group(project, MAP.get(usertype), "project", externalgroup)


##############################
# /projects/<projectid>/users
##############################


@bp.route("/projects/<projectid>/users", methods=["GET", "POST"])
@auth.login_required
def project_users(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    return handle_groupmembers(project, "user_group", "project")


########################################
# /projects/<projectid>/users/<username>
########################################


@bp.route("/projects/<projectid>/users/<username>", methods=["GET", "DELETE"])
@auth.login_required
def project_user(projectid, username):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    return handle_groupmember(project, "user_group", "project", username)


########################################
# /projects/<projectid>/managers
########################################


@bp.route("/projects/<projectid>/managers", methods=["GET", "POST"])
@auth.login_required
def project_managers(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    return handle_groupmembers(project, "manager_group", "project")


########################################
# /projects/<projectid>/managers/<username>
########################################


@bp.route("/projects/<projectid>/managers/<username>", methods=["GET", "DELETE"])
@auth.login_required
def project_manager(projectid, username):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    return handle_groupmember(project, "manager_group", "project", username)


########################################
# /projects/<projectid>/contacts/<contactid>
########################################


@bp.route("/projects/<projectid>/contacts/<contactid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_contact(projectid, contactid):
    return handle_contact(projectid, contactid)


@bp.route("/projects/<projectid>/contacts/<contactid>", methods=["GET"])
def handle_contact(projectid, contactid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    contact = Contact.query.filter(
        Contact.entity_id == project.id,
        Contact.entity_type == OBJECTS.project,
        Contact.id == contactid,
    ).one_or_none()

    if contact is None:
        return (
            jsonify(
                {"message": f"Contact {contactid} in project {projectid} not found"}
            ),
            404,
        )

    if request.method == "GET":
        return jsonify(contact_schema.dump(contact))

    elif request.method == "PUT":
        if not is_manager(project):
            return (
                jsonify({"message": f"Access denied for project: {project.name}"}),
                401,
            )
        res, code = handle_change_contact(contact, project.name, request.json)
        return res, code

    elif request.method == "DELETE":
        log.debug(f"Delete contact {contactid} from project {project.name}")
        # user should be project manager
        if not is_manager(project):
            abort(401)
        if contact.primary == 1:
            return jsonify({"message": "Primary contact must not be deleted!"}), 405
        db.session.delete(contact)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.contact,
            contact.name,
            "A contact was removed from the project",
        )
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


# Project-specific processes (legacy)


def processes_for_project(project):
    """Return a list of all processes that are configured in processgroups
    belonging to a project
    Input:
        project: project record from Projects database
    """
    processlist = []
    processset = []
    # We have to collect all processgroups and make a list of all processes in there
    processgroups = ProcessGroup.query.filter(
        ProcessGroup.projectid == project.id
    ).all()
    for processgroup in processgroups:
        all_processrefs = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id
        ).all()
        for processref in all_processrefs:
            # We want all processes that have a distinct id/tag combination
            uniqueid = processref.processid, processref.tag
            if uniqueid in processset:
                continue
            processset.append(uniqueid)
            process2 = Process2.query.filter(Process2.id == processref.processid).one()
            process = Process(
                project.id,
                f"{process2.name} - {processref.tag}",
                processid=process2.name,
            )
            process.id = processref.id
            # Copy instance properties
            for attr in ["tag", "lsf_queue"]:
                setattr(process, attr, getattr(processref, attr))
            process.tag = processref.tag
            # Copy global properties
            process.repo = process2.repo
            for attr in [
                "description",
                "modify_in_place",
                "omit_staging",
                "omit_bringonline",
                "repo",
                "distribution",
                "concurrency_limit",
                "max_runtime",
                "compatible_clusters",
                "required_memory",
            ]:
                setattr(process, attr, getattr(process2, attr))
            process.next_processid = 0
            process.next_projectid = 0
            processlist.append(process)
    return processlist


########################################
# /projects/<projectid>/processes
########################################


@bp.route("/projects/<projectid>/processes", methods=["GET"])
def handle_processes(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    if request.method == "GET":
        processlist = processes_for_project(project)
        return jsonify(processes_schema.dump(processlist))
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


########################################
# /projects/<projectid>/processes/<processid>
########################################


@bp.route("/projects/<projectid>/processes/<processid>", methods=["GET"])
def handle_process(projectid, processid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    process = process_from_id(projectid, processid)
    if process is None:
        return (
            jsonify(
                {"message": f"Process {processid} in project {projectid} not found"}
            ),
            404,
        )
    if request.method == "GET":
        return jsonify(process_schema.dump(process))
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


########################################
# /processes
########################################


@bp.route("/processes", methods=["POST"])
@auth.login_required
def auth_handle_processes2():
    return handle_processes2()


@bp.route("/processes", methods=["GET"])
def handle_processes2():
    if request.method == "GET":
        all_processes = Process2.query.all()
        dump = processes2_schema.dump(all_processes)
        return jsonify(dump)
    elif request.method == "POST":
        processname = request.json.get("name")
        if not processname:
            log.error("Processname not supplied")
            return jsonify({"message": "Invalid request data"}), 400
        # Test if process does not exist already
        process = Process2.query.filter_by(name=processname).count()
        if process:
            log.error(f"Processname {processname} already exists")
            return jsonify({"message": f"Process {processname} already exists"}), 40
        new_process = Process2(processname)
        log.debug(f"New process {processname} created by {g.username}")
        admin_sess = admin_session()
        processid_attr = current_app.config.get("ATTR_PROCESSID")
        manager_group = provide_group(
            admin_sess,
            string2label(processname, 15),
            "process-admins",
            metadata={processid_attr: processname},
        )
        add_groupmember(manager_group, g.user)
        new_process.manager_group = manager_group.name
        db.session.add(new_process)
        db.session.commit()
        return process2_schema.jsonify(new_process), 201
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


######################
# /processes/processid
######################


def process_inuse(processid):
    """Test if a process is being used by pipelines

    Args:
        processid (int or str): name or id of process

    Returns:
        boolean: True if process is being used
    """
    ref, result = get_processreferences(processid)
    if result != 200:
        return False
    return bool(ref.json)


@bp.route("/processes/<processid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_process2(processid):
    return handle_process2(processid)


@bp.route("/processes/<processid>", methods=["GET"])
def handle_process2(processid):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    if request.method == "GET":
        record = process2_schema.dump(process)
        in_use = process_inuse(processid)
        record["in_use"] = int(in_use)
        return jsonify(record)
    elif request.method == "PUT":
        if not is_manager(process):
            return jsonify({"message": f"Access denied for process {processid}"}), 401
        log.debug(f"Process {process.name} modified by {g.username}")
        valid_properties = [
            "name",
            "description",
            "output_prefix",
            "distribution",
            "modify_in_place",
            "restartable",
            "repo",
            "omit_staging",
            "omit_bringonline",
            "concurrency_limit",
            "max_runtime",
            "compatible_clusters",
            "required_memory",
        ]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid process property {key}"}), 404
            log.debug(f"Set {key} for {process.name} to {request.json[key]}")
            setattr(process, key, request.json[key])
        # Make sure omit_bringonline is only set if omit_staging is also set
        process.omit_bringonline = int(
            bool(process.omit_bringonline) and bool(process.omit_staging)
        )
        db.session.commit()
        return process2_schema.jsonify(process), 200
    elif request.method == "DELETE":
        if not is_manager(process):
            return jsonify({"message": f"Access denied for process {processid}"}), 401
        if process_inuse(processid):
            return (
                jsonify(
                    {
                        "message": f"Process '{process.name}' is in use and cannot be deleted"
                    }
                ),
                405,
            )
        log.debug(f"Delete process {processid}")
        db.session.delete(process)
        db.session.commit()
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


########################################
# /processes/<processid>/tags
########################################


def get_tags_on_repo(repo):
    gitcmd = git.cmd.Git()
    output = ""
    with gitcmd.custom_environment(GIT_SSL_NO_VERIFY="1"):
        output = gitcmd.ls_remote("--tags", "--heads", "--refs", repo)
    refs = []
    for line in output.split("\n"):
        s1 = line.split("\t")
        if len(s1) == 2:
            s2 = s1[1].split("/")
            if len(s2) == 3:
                refs.append(s2[2])
    return jsonify(refs)


@bp.route("/processes/<processid>/tags", methods=["GET"])
def get_processtags(processid):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404

    return get_tags_on_repo(process.repo)


########################################
# /processes/<processid>/references
########################################


@bp.route("/processes/<processid>/references", methods=["GET"])
def get_processreferences(processid):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    result = []
    refs = (
        db.session.query(ProcessRef)
        .join(ProcessGroup)
        .join(Project)
        .filter(ProcessRef.processid == process.id)
        .all()
    )
    for row in refs:
        processref = processref_schema.dump(row)
        processref["url"] = (
            f"{bp.url_prefix}/projects/{row.processgroup.project.id}/processgroups/{row.processgroup.id}/processes/{row.id}"
        )
        processref["project"] = row.processgroup.project.name
        processref["processgroup"] = row.processgroup.name
        result.append(processref)
    return jsonify(result), 200


#################################
# /processes/<processid>/managers
#################################


@bp.route("/processes/<processid>/managers", methods=["GET", "POST"])
@auth.login_required
def process_managers(processid):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    return handle_groupmembers(process, "manager_group", "process")


############################################
# /processes/<processid>/managers/<username>
############################################


@bp.route("/processes/<processid>/managers/<username>", methods=["GET", "DELETE"])
@auth.login_required
def process_manager(processid, username):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    return handle_groupmember(process, "manager_group", "process", username)


############################################
# /processes/<processid>/referencedataversion
############################################

### referencedata for a process


@bp.route("/processes/<processid>/referencedataversion", methods=["POST"])
@auth.login_required
def auth_handle_referencedatas_of_process(processid):
    return handle_referencedatas_of_process(processid)


@bp.route("/processes/<processid>/referencedataversion", methods=["GET"])
def handle_referencedatas_of_process(processid):
    process = process2_from_id(processid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    if request.method == "GET":
        all_process_referencedataversions = ReferenceDataVersionForProcess.query.filter(
            ReferenceDataVersionForProcess.processid == process.id
        ).all()
        dump = referencedataversions_for_process_schema.dump(
            all_process_referencedataversions
        )
        return jsonify(dump)
    elif request.method == "POST":
        # user should be project manager
        if not is_manager(process):
            return jsonify({"message": f"Access denied for process {processid}"}), 401
        log.debug(
            f"New referencedata_version as input for process {processid} by {g.username}"
        )
        # if version_id is set to None, we store Null in the database to indicate we always want
        # the latest version of reference data
        referencedataid = request.json.get("referencedataid")
        referencedataversionid = request.json.get("referencedataversionid")
        label = request.json.get("label")
        if referencedataversionid and int(referencedataversionid) < 0:
            referencedataversionid = None
        new_process_data_input = ReferenceDataVersionForProcess(
            referencedataid, referencedataversionid, process.id, label
        )
        db.session.add(new_process_data_input)
        db.session.commit()
        return (
            referencedataversion_for_process_schema.jsonify(new_process_data_input),
            201,
        )
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/processes/<processid>/referencedataversion/<refdataid>", methods=["PUT", "DELETE"]
)
@auth.login_required
def auth_referencedata_of_process(processid, refdataid):
    return referencedata_of_process(processid, refdataid)


@bp.route("/processes/<processid>/referencedataversion/<refdataid>", methods=["GET"])
def referencedata_of_process(processid, refdataid):
    process = process2_from_id(processid)
    process_refdata = refdataversion_for_process_from_id(refdataid)
    if process is None:
        return jsonify({"message": f"Process {processid} not found"}), 404
    if process_refdata is None:
        return jsonify({"message": f"Process {process_refdata} not found"}), 404
    if request.method == "GET":
        referencedataversion = ReferenceDataVersionForProcess.query.filter(
            ReferenceDataVersion.id == refdataid
        )
        dump = referencedataversions_for_process_schema.dump(referencedataversion)
        return jsonify(dump)
    elif request.method == "PUT":
        # user should be project manager
        if not is_manager(process):
            return jsonify({"message": f"Access denied for process {processid}"}), 401
        log.debug(
            f"Reference_data_conn {process_refdata.id} for process {process.name} modified by {g.username}"
        )
        valid_properties = ["referencedataversionid", "label"]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid process property {key}"}), 404
            log.debug(
                f"Set {key} for {process.name} to {request.json[key]} by {g.username}"
            )
            value = request.json[key]
            if key == "referencedataversionid" and int(value) < 0:
                value = None
            setattr(process_refdata, key, value)
        db.session.commit()
        return process2_schema.jsonify(process_refdata), 200
    elif request.method == "DELETE":
        # user should be project manager
        if not is_manager(process):
            return jsonify({"message": f"Access denied for process {processid}"}), 401
        log.debug(
            f"Reference data {refdataid} for process {process.name} deleted by {g.username}"
        )
        db.session.delete(process_refdata)
        db.session.commit()
        return jsonify({"message": "reference data was deleted"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


### processgroup endpoints


@bp.route("/projects/<projectid>/processgroups", methods=["POST"])
@auth.login_required
def auth_handle_processgroups(projectid):
    return handle_processgroups(projectid)


@bp.route("/projects/<projectid>/processgroups", methods=["GET"])
def handle_processgroups(projectid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    if request.method == "GET":
        all_processgroups = ProcessGroup.query.filter(
            ProcessGroup.projectid == project.id
        ).all()
        dump = processgroups_schema.dump(all_processgroups)
        return jsonify(dump)
    elif request.method == "POST":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        processgroupname = request.json.get("name")
        if not processgroupname:
            log.error("Processgroupname not supplied")
            return jsonify({"message": "Invalid request data"}), 400
        # Test if process does not exist already
        processgroup = ProcessGroup.query.filter(
            ProcessGroup.name == processgroupname, ProcessGroup.projectid == project.id
        ).count()
        if processgroup:
            log.error(f"Processname {processgroupname} already exists")
            return (
                jsonify({"message": f"Process {processgroupname} already exists"}),
                409,
            )
        log.debug(
            f"Processgroup {processgroupname} for project {project.name} created by {g.username}"
        )
        new_processgroup = ProcessGroup(project.id, processgroupname)
        db.session.add(new_processgroup)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.processgroup,
            processgroupname,
            "A new processgroup was created",
        )
        return processgroup_schema.jsonify(new_processgroup), 201
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/projects/<projectid>/processgroups/<processgroupid>", methods=["PUT", "DELETE"]
)
@auth.login_required
def auth_handle_processgroup(projectid, processgroupid):
    return handle_processgroup(projectid, processgroupid)


@bp.route("/projects/<projectid>/processgroups/<processgroupid>", methods=["GET"])
def handle_processgroup(projectid, processgroupid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, processgroupid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {processgroupid} not found"}), 404

    if request.method == "GET":
        return jsonify(process2_schema.dump(processgroup))
    elif request.method == "PUT":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(
            f"Processgroup {processgroup.name} for project {project.name} modified by {g.username}"
        )
        valid_properties = ["name", "description"]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid processgroup property {key}"}), 404
            log.debug(
                f"Set {key} for {processgroup.name} to {request.json[key]} by {g.username}"
            )
            setattr(processgroup, key, request.json[key])
        db.session.commit()
        return process2_schema.jsonify(processgroup), 200
    elif request.method == "DELETE":
        # First delete all group process references
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        processrefs = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id
        ).all()
        for processref in processrefs:
            delete_processref(processref)
        log.debug(
            f"Processgroup {processgroup.name} for project {project.name} deleted by {g.username}"
        )
        db.session.delete(processgroup)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.processgroup,
            processgroup.name,
            "A processgroup was removed",
        )
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/projects/<projectid>/processgroups/<pgid>/dependencies", methods=["GET"])
def handle_all_dependencies(projectid, pgid):
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return (
            jsonify(
                {"message": f"Project {projectid} or processgroup {pgid} not found"}
            ),
            404,
        )
    all_processrefs = ProcessRef.query.filter(
        ProcessRef.processgroupid == processgroup.id
    ).all()
    all_deps = []
    for processref in all_processrefs:
        deps = ProcessDependency.query.filter(
            ProcessDependency.processrefid == processref.id
        ).all()
        all_deps += deps
    return processdependencies_schema.jsonify(all_deps)


# processref endpoints


@bp.route("/projects/<projectid>/processgroups/<pgid>/processes", methods=["POST"])
@auth.login_required
def auth_handle_processrefs(projectid, pgid):
    return handle_processrefs(projectid, pgid)


@bp.route("/projects/<projectid>/processgroups/<pgid>/processes", methods=["GET"])
def handle_processrefs(projectid, pgid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    if request.method == "GET":
        all_processrefs = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id
        ).all()
        dump = processrefs_schema.dump(all_processrefs)
        return jsonify(dump)
    elif request.method == "POST":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        processrefname = request.json.get("name")
        processid = request.json.get("processid")
        if not processrefname:
            log.error("Group process name not supplied")
            return jsonify({"message": "Invalid request data"}), 400
        # Test if process does not exist already
        processref = ProcessRef.query.filter(
            ProcessRef.processgroupid == processgroup.id,
            ProcessRef.name == processrefname,
        ).count()
        if processref:
            return (
                jsonify(
                    {"message": f"Group process name {processrefname} already exists"}
                ),
                40,
            )
        new_processref = ProcessRef(processgroup.id, processrefname, processid)
        log.debug(
            f"New process reference for project {project.name}: {new_processref.name}"
        )
        db.session.add(new_processref)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.processgroup,
            processgroup.name,
            f"The process {processrefname} was added to the processgroup",
        )
        return processgroup_schema.jsonify(new_processref), 201
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>",
    methods=["PUT", "DELETE"],
)
@auth.login_required
def auth_handle_processref(projectid, pgid, processrefid):
    return handle_processref(projectid, pgid, processrefid)


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>",
    methods=["GET"],
)
def handle_processref(projectid, pgid, processrefid):

    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    processref = processref_from_id(project.id, processgroup.id, processrefid)
    if processref is None:
        return (
            jsonify({"message": f"Process group process {processrefid} not found"}),
            404,
        )
    if request.method == "GET":
        return jsonify(processref_schema.dump(processref))
    elif request.method == "PUT":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(f"Process reference {processref.name} modified by {g.username}")
        valid_properties = ["name", "input", "lsf_queue", "tag"]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid process property {key}"}), 404
            log.debug(f"Set attr {key} for {processref.name} to {request.json[key]}")
            setattr(processref, key, request.json[key])
            if key == "tag":
                notify(
                    project.id,
                    OBJECTS.project,
                    displayname(),
                    OBJECTS.processgroup,
                    processgroup.name,
                    f"Git tag for {processref.name} was changed to {request.json[key]}",
                )
        db.session.commit()
        return process2_schema.jsonify(processref), 200
    elif request.method == "DELETE":
        log.debug(f"Delete processref {processref.name} by {g.username}")
        delete_processref(processref)
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.processgroup,
            processgroup.name,
            f"The process {processref.name} was removed from the processgroup",
        )
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def delete_processref(processref):
    # First delete all dependencies:
    deps = ProcessDependency.query.filter(
        ProcessDependency.processrefid == processref.id
    ).all()
    for dep in deps:
        db.session.delete(dep)
    # Delete dependencies of other processes that refer to this process
    deps = ProcessDependency.query.filter(
        ProcessDependency.depends_on == processref.id
    ).all()
    for dep in deps:
        db.session.delete(dep)
    db.session.delete(processref)
    db.session.commit()


# pgpdepend endpoints


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/dependencies",
    methods=["POST"],
)
@auth.login_required
def auth_handle_pgpdepends(projectid, pgid, processrefid):
    return handle_pgpdepends(projectid, pgid, processrefid)


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/dependencies",
    methods=["GET"],
)
def handle_pgpdepends(projectid, pgid, processrefid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    processref = processref_from_id(project.id, processgroup.id, processrefid)
    if processref is None:
        return (
            jsonify({"message": f"Process group process {processrefid} not found"}),
            404,
        )
    if request.method == "GET":
        all_pgdepend = ProcessDependency.query.filter(
            ProcessDependency.processrefid == processref.id
        ).all()
        dump = processdependencies_schema.dump(all_pgdepend)
        return jsonify(dump)
    elif request.method == "POST":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(f"New dependency in project {project.name} by {g.username}")
        depends_on = request.json.get("depends_on")
        # Test if process dependency does not exist already
        new_pgpdepend = ProcessDependency(processref.id, depends_on)
        db.session.add(new_pgpdepend)
        db.session.commit()
        return processdependency_schema.jsonify(new_pgpdepend), 201
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/dependencies/<did>",
    methods=["PUT", "DELETE"],
)
@auth.login_required
def auth_handle_pgpdepend(projectid, pgid, processrefid, did):
    return handle_pgpdepend(projectid, pgid, processrefid, did)


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/dependencies/<did>",
    methods=["GET"],
)
def handle_pgpdepend(projectid, pgid, processrefid, did):

    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    processref = processref_from_id(project.id, processgroup.id, processrefid)
    if processref is None:
        return (
            jsonify({"message": f"Process group process {processrefid} not found"}),
            404,
        )
    processrefdepend = processdep_from_id(
        project.id, processgroup.id, processref.id, did
    )
    if processrefdepend is None:
        return jsonify({"message": f"Process dependency {did} not found"}), 404
    if request.method == "GET":
        return jsonify(processdependency_schema.dump(processrefdepend))
    elif request.method == "PUT":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(f"Modify dependency in project {project.name} by {g.username}")
        valid_properties = ["depends_on"]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid dependency property {key}"}), 404
            setattr(processrefdepend, key, request.json[key])
        db.session.commit()
        return processdependency_schema.jsonify(processrefdepend), 200
    elif request.method == "DELETE":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(
            f"Delete dependency {processrefdepend} in project {project.name} by {g.username}"
        )
        db.session.delete(processrefdepend)
        db.session.commit()
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/referencedataversion",
    methods=["POST"],
)
@auth.login_required
def auth_handle_pgprdv_(projectid, pgid, processrefid):
    return handle_pgprdv_(projectid, pgid, processrefid)


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/referencedataversion",
    methods=["GET"],
)
def handle_pgprdv_(projectid, pgid, processrefid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    processref = processref_from_id(project.id, processgroup.id, processrefid)
    if processref is None:
        return (
            jsonify({"message": f"Process group process {processrefid} not found"}),
            404,
        )
    if request.method == "GET":
        all_processref_referencedataversions = (
            ReferenceDataVersionForProcessRef.query.filter(
                ReferenceDataVersionForProcessRef.processrefid == processref.id
            ).all()
        )
        dump = referencedataversions_for_procesref_schema.dump(
            all_processref_referencedataversions
        )
        return jsonify(dump), 200
    elif request.method == "POST":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(
            f"New referencedata_version as input for process {processrefid} in project {project.name} by {g.username}"
        )
        # if version_id is set to None, we store Null in the database to indicate we always waant the latest version of reference data
        supersedingersionid = request.json.get("supersedingversionid")
        processdefaultid = request.json.get("processdefaultid")
        new_process_refdata_input = ReferenceDataVersionForProcessRef(
            processref.id, supersedingersionid, processdefaultid
        )
        db.session.add(new_process_refdata_input)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.reference_data,
            processgroup.name,
            "A required reference dataset was added to processgroup",
        )
        return (
            referencedataversion_for_procesref_schema.jsonify(
                new_process_refdata_input
            ),
            201,
        )
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/referencedataversion/<prrdvid>",
    methods=["PUT", "DELETE"],
)
@auth.login_required
def auth_handle_pgprdv(projectid, pgid, processrefid, prrdvid):
    return handle_pgprdv(projectid, pgid, processrefid, prrdvid)


@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/referencedataversion/<prrdvid>",
    methods=["GET"],
)
def handle_pgprdv(projectid, pgid, processrefid, prrdvid):

    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"Project {projectid} not found"}), 404
    processgroup = processgroup_from_id(projectid, pgid)
    if processgroup is None:
        return jsonify({"message": f"Processgroup {pgid} not found"}), 404
    processref = processref_from_id(project.id, processgroup.id, processrefid)
    if processref is None:
        return (
            jsonify({"message": f"Process group process {processrefid} not found"}),
            404,
        )
    # this should just be the primary key, no need for all thr humbugh
    processref_refdataversion = refdataversion_for_processref_from_id(prrdvid)
    if processref_refdataversion is None:
        return (
            jsonify(
                {
                    "message": f"ReferenceDataVersion input {prrdvid} for process {processrefid} not found"
                }
            ),
            404,
        )
    if request.method == "GET":
        return jsonify(
            referencedataversion_for_procesref_schema.dump(processref_refdataversion)
        )
    elif request.method == "PUT":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(
            f"Modify input reference_dataversion in project {project.name} by {g.username}"
        )
        valid_properties = ["supersedingversionid"]
        for key in request.json:
            if key not in valid_properties:
                return jsonify({"message": f"Invalid dependency property {key}"}), 404
            setattr(processref_refdataversion, key, request.json[key])
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.reference_data,
            processgroup.name,
            "A required reference dataset was changed in processgroup",
        )
        return (
            jsonify(
                referencedataversion_for_procesref_schema.dump(
                    processref_refdataversion
                )
            ),
            200,
        )
    elif request.method == "DELETE":
        # user should be project manager
        if not is_manager(project):
            return jsonify({"message": f"Access denied for project {projectid}"}), 401
        log.debug(
            f"Delete input reference_dataversion {processref_refdataversion} in project {project.name} by {g.username}"
        )
        db.session.delete(processref_refdataversion)
        db.session.commit()
        notify(
            project.id,
            OBJECTS.project,
            displayname(),
            OBJECTS.reference_data,
            processgroup.name,
            "A required reference dataset was removed from processgroup",
        )
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


def latest_valid_version_of_reference_dataset(referenceDatasetId):
    latest_version = (
        ReferenceDataVersion.query.filter(
            ReferenceDataVersion.referenceid == referenceDatasetId,
            bool(ReferenceDataVersion.is_valid) == True,
        )
        .order_by(desc(ReferenceDataVersion.version))
        .limit(1)
        .one_or_none()
    )

    importer_state = ReferenceDataImport.query.filter(
        ReferenceDataImport.referenceid == referenceDatasetId
    ).one_or_none()
    if importer_state:
        current_version_import_state = (
            importer_state.current_version
        )  # this is just the version number! Not the Id!
        latest_version_import_state = ReferenceDataVersion.query.filter(
            ReferenceDataVersion.referenceid == referenceDatasetId,
            ReferenceDataVersion.version == current_version_import_state,
        ).one_or_none()
        if latest_version != latest_version_import_state:
            log.error(
                f"The latest ReferenceDataVersion for referenceDatasetId '{referenceDatasetId}' is {latest_version.version} while the latest version in importerstate is {latest_version_import_state}!"
            )

    return latest_version


# return the refdata version that should be used (either default, latest, possibly overwritten...)
@bp.route(
    "/projects/<projectid>/processgroups/<pgid>/processes/<processrefid>/effective_referencedataversion",
    methods=["GET"],
)
# @auth.login_required
def handle_effective_referencedataversion(projectid, pgid, processrefid):
    if request.method != "GET":
        return jsonify({"message": f"Method {request.method} not allowed"}), 405
    else:
        # allow only GET
        project = project_from_id(projectid)
        if project is None:
            return jsonify({"message": f'Project "{projectid}" not found'}), 404
        processgroup = processgroup_from_id(projectid, pgid)
        if processgroup is None:
            return jsonify({"message": f'Processgroup "{pgid}" not found'}), 404
        processref = processref_from_id(project.id, processgroup.id, processrefid)
        if processref is None:
            return (
                jsonify(
                    {"message": f'Process group process "{processrefid}" not found'}
                ),
                404,
            )

        all_versions_for_process = ReferenceDataVersionForProcess.query.filter(
            ReferenceDataVersionForProcess.processid == processref.processid
        ).all()
        all_versions_for_processref = ReferenceDataVersionForProcessRef.query.filter(
            ReferenceDataVersionForProcessRef.processrefid == processref.id
        ).all()

        effective_versions = {}
        # first collect all versions connected to the process itself
        for rdv_for_process in all_versions_for_process:
            key = f"{rdv_for_process.id}"  # f"{rdv_for_process.referencedataid}_{rdv_for_process.referencedataversionid}"
            if (rdv_for_process.referencedataversionid) and (
                rdv_for_process.referencedataversionid >= 0
            ):
                version = ReferenceDataVersion.query.get(
                    rdv_for_process.referencedataversionid
                )
                versionJSON = referencedataversion_schema.dump(version)
                effective_versions[key] = {
                    "effective_version": versionJSON,
                    "specified_by": "Process",
                    "specified_as": rdv_for_process.referencedataversionid,
                    "reference_dataset_id": rdv_for_process.referencedataid,
                    "label": rdv_for_process.label,
                }
            elif rdv_for_process.referencedataversionid == None:  # None = latest
                version = latest_valid_version_of_reference_dataset(
                    rdv_for_process.referencedataid
                )
                versionJSON = referencedataversion_schema.dump(version)
                effective_versions[key] = {
                    "effective_version": versionJSON,
                    "specified_by": "Process",
                    "specified_as": "LATEST",
                    "reference_dataset_id": rdv_for_process.referencedataid,
                    "label": rdv_for_process.label,
                }
            else:
                return (
                    jsonify(
                        {
                            "message": f"Referencedataversion_for_Process {rdv_for_process.id} refers a version with unexpected value: {rdv_for_process.referencedataversionid}"
                        }
                    ),
                    500,
                )

        # second overwrite all versions for which we find a more specific entry in the processref
        for rdv_for_processref in all_versions_for_processref:
            processdefaultid = rdv_for_processref.processdefaultid
            if processdefaultid == None:
                # this seems wrong, we arent overwriting any process specific default?
                pass
            else:
                process_default = ReferenceDataVersionForProcess.query.get(
                    processdefaultid
                )
                key = f"{rdv_for_processref.processdefaultid}"
                # overwrite the entry in effective_versions with the soeciefied (or possibly latest) version entry
                if (rdv_for_processref.supersedingversionid) and (
                    rdv_for_processref.supersedingversionid == -2
                ):
                    # this seems to be in error, -2 is used in NGSweb to signal that this entry should have been removed! (e.g. dont overwrite the process default)
                    # for now we just act as if the entry weren here
                    pass
                elif (rdv_for_processref.supersedingversionid) and (
                    rdv_for_processref.supersedingversionid >= 0
                ):
                    version = ReferenceDataVersion.query.get(
                        rdv_for_processref.supersedingversionid
                    )
                    versionJSON = referencedataversion_schema.dump(version)
                    effective_versions[key] = {
                        "effective_version": versionJSON,
                        "specified_by": "ProcessRef",
                        "specified_as": rdv_for_processref.supersedingversionid,
                        "reference_dataset_id": process_default.referencedataid,
                        "label": process_default.label,
                    }
                elif rdv_for_processref.supersedingversionid == None:  # None = Latest
                    version = latest_valid_version_of_reference_dataset(
                        process_default.referencedataid
                    )
                    versionJSON = referencedataversion_schema.dump(version)
                    effective_versions[key] = {
                        "effective_version": versionJSON,
                        "specified_by": "ProcessRef",
                        "specified_as": "LATEST",
                        "reference_dataset_id": process_default.referencedataid,
                        "label": process_default.label,
                    }
        return jsonify(list(effective_versions.values())), 200


@bp.route(
    "/projects/<projectid>/processes/<processid>/effective_referencedataversion",
    methods=["GET"],
)
def handle_process__effective_referencedataversion(projectid, processid):
    project = project_from_id(projectid)
    if project is None:
        return jsonify({"message": f"unknown project: {projectid}"}), 404
    process = process2_from_id(processid)
    if process is None:
        return (
            jsonify(
                {"message": f'Process "{processid}" in project "{projectid}" not found'}
            ),
            404,
        )
    if not request.method == "GET":
        return jsonify({"message": f"Method {request.method} not allowed"}), 405

    all_versions_for_process = ReferenceDataVersionForProcess.query.filter(
        ReferenceDataVersionForProcess.processid == process.id
    ).all()
    log.error(
        f"found {len(all_versions_for_process)} Versions connected to process: '{processid}' aka, '{process.id}'"
    )
    effective_versions = {}
    for rdv_for_process in all_versions_for_process:
        key = f"{rdv_for_process.id}"
        if (rdv_for_process.referencedataversionid) and (
            rdv_for_process.referencedataversionid >= 0
        ):
            version = ReferenceDataVersion.query.get(
                rdv_for_process.referencedataversionid
            )
            versionJSON = referencedataversion_schema.dump(version)
            effective_versions[key] = {
                "effective_version": versionJSON,
                "specified_by": "Process",
                "specified_as": rdv_for_process.referencedataversionid,
                "reference_dataset_id": rdv_for_process.referencedataid,
                "label": rdv_for_process.label,
            }
        elif rdv_for_process.referencedataversionid == None:  # None = latest
            version = latest_valid_version_of_reference_dataset(
                rdv_for_process.referencedataid
            )
            versionJSON = referencedataversion_schema.dump(version)
            effective_versions[key] = {
                "effective_version": versionJSON,
                "specified_by": "Process",
                "specified_as": "LATEST",
                "reference_dataset_id": rdv_for_process.referencedataid,
                "label": rdv_for_process.label,
            }
        else:
            return (
                jsonify(
                    {
                        "message": f"Referencdataversion_for_Process {rdv_for_process.id} refers a version with unexpected value: {rdv_for_process.referencedataversionid}"
                    }
                ),
                500,
            )

    return jsonify(list(effective_versions.values())), 200


@bp.route("/reference", methods=["POST"])
@auth.login_required
def auth_handle_referencedatas():
    return handle_referencedatas()


@bp.route("/reference", methods=["GET"])
def handle_referencedatas():
    if request.method == "GET":

        rds = referencedatas_schema.dump(ReferenceData.query.all())
        for rd in rds:
            rd["importer_state"] = referencedataimport_schema.dump(
                ReferenceDataImport.query.filter(
                    ReferenceDataImport.referenceid == rd["id"]
                ).one_or_none()
            )
            rd["number_of_versions"] = ReferenceDataVersion.query.filter(
                ReferenceDataVersion.referenceid == rd["id"]
            ).count()
            rd["number_of_valid_versions"] = ReferenceDataVersion.query.filter(
                ReferenceDataVersion.referenceid == rd["id"],
                ReferenceDataVersion.is_valid == "1",
            ).count()

        return jsonify(rds)
    elif request.method == "POST":
        name = request.json.get("name")
        owner_name = ""
        try:
            owner_name = g.username
        except Exception:
            pass
        new_referencedata = ReferenceData(name, owner_name)
        for key, value in request.json.items():
            setattr(new_referencedata, key, value)
        db.session.add(new_referencedata)
        db.session.commit()
        new_importstate = ReferenceDataImport(new_referencedata.id)
        db.session.add(new_importstate)
        db.session.commit()
        return jsonify(referencedata_schema.dump(new_referencedata)), 201
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/reference/<referenceid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_referencedata(referenceid):
    return handle_referencedata(referenceid)


@bp.route("/reference/<referenceid>", methods=["GET"])
def handle_referencedata(referenceid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    if request.method == "GET":
        # return jsonify(referencedata_schema.dump(reference))
        result = referencedata_schema.dump(reference)
        result["importer_state"] = referencedataimport_schema.dump(
            ReferenceDataImport.query.filter(
                ReferenceDataImport.referenceid == reference.id
            ).one_or_none()
        )
        return jsonify(result)
    elif request.method == "PUT":
        for key, value in request.json.items():
            if key in ReferenceData.change_allowed:
                setattr(reference, key, value)
            else:
                return jsonify({"message": f"Not allowed to change {key}"}), 403
        db.session.commit()
        notify(
            reference.id,
            OBJECTS.reference_data,  # this is the object-type the contacts are stored on!
            displayname(),
            OBJECTS.reference_data,  # this is the object-type the change occured on!
            reference.name,
            "A new reference data definition was added",
        )
        return jsonify(referencedata_schema.dump(reference)), 200
    elif request.method == "DELETE":
        existingVersions = ReferenceDataVersion.query.filter(
            ReferenceDataVersion.referenceid == reference.id
        ).count()
        if existingVersions == 0:
            db.session.delete(reference)
            db.session.commit()
            notify(
                reference.id,
                OBJECTS.reference_data,  # this is the object-type the contacts are stored on!
                displayname(),
                OBJECTS.reference_data,  # this is the object-type the change occured on!
                reference.name,
                "A reference data definition was deleted",
            )
            return jsonify({"message": "OK"}), 200
        else:
            return (
                jsonify(
                    {
                        "message": f"Method {request.method} is forbidden while {existingVersions} versions exist."
                    }
                ),
                403,
            )

    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


################################
# /reference/<referenceid>/tags
################################


@bp.route("/reference/<referenceid>/tags", methods=["GET"])
def get_referencetags(referenceid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    if not reference.repository:
        return (
            jsonify({"message": f"ReferenceData {referenceid} has no repository"}),
            404,
        )

    return get_tags_on_repo(reference.repository)


################################
# /reference/<referenceid>/contacts
################################
@bp.route("/reference/<referenceid>/contacts", methods=["POST"])
@auth.login_required
def auth_handle_reference_contacts_authorized(referenceid):
    return handle_reference_contacts_authorized(referenceid)


@bp.route("/reference/<referenceid>/contacts", methods=["GET"])
def handle_reference_contacts_authorized(referenceid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404

    if request.method == "GET":
        contacts = Contact.query.filter(
            Contact.entity_id == reference.id,
            Contact.entity_type == OBJECTS.reference_data,
        ).all()
        return jsonify(contacts_schema.dump(contacts))

    elif request.method == "POST":
        # if not is_manager(reference):
        #    return jsonify({"message": f"Access denied for ReferenceData: reference.name"}), 401
        json, code = handle_create_contact(
            reference.id, OBJECTS.reference_data, reference.name, request.json
        )
        return json, code
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


########################################
# /reference/<referenceid>/contacts/<contactid>
########################################


@bp.route("/reference/<referenceid>/contacts/<contactid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_reference_contact(referenceid, contactid):
    return handle_reference_contact(referenceid, contactid)


@bp.route("/reference/<referenceid>/contacts/<contactid>", methods=["GET"])
def handle_reference_contact(referenceid, contactid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404

    contact = Contact.query.filter(
        Contact.entity_id == reference.id,
        Contact.entity_type == OBJECTS.reference_data,
        Contact.id == contactid,
    ).one_or_none()
    if contact is None:
        return (
            jsonify(
                {"message": f"Contact {contactid} in reference {referenceid} not found"}
            ),
            404,
        )

    if request.method == "GET":
        return jsonify(contact_schema.dump(contact))

    elif request.method == "PUT":
        # if not is_manager(reference):
        #    return jsonify({"message": f"Access denied for reference data: {reference.name}"}), 401
        res, code = handle_change_contact(contact, reference.name, request.json)
        return res, code

    elif request.method == "DELETE":
        log.debug(f"Delete contact {contactid} from reference {reference.name}")
        # user should be  manager
        # if not is_manager(reference):
        #    abort(401)
        if contact.primary == 1:
            return jsonify({"message": "Primary contact must not be deleted!"}), 405
        db.session.delete(contact)
        db.session.commit()
        notify(
            reference.id,
            OBJECTS.reference_data,
            displayname(),
            OBJECTS.contact,
            contact.name,
            "A contact was removed from the reference data",
        )
        return jsonify({"message": "OK"}), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/reference/<referenceid>/importer_state", methods=["PUT", "PATCH"])
@auth.login_required
def auth_handle_referencedataimport(referenceid):
    return handle_referencedataimport(referenceid)


@bp.route("/reference/<referenceid>/importer_state", methods=["GET"])
def handle_referencedataimport(referenceid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    if request.method == "GET":
        return jsonify(
            referencedataimport_schema.dump(
                ReferenceDataImport.query.filter(
                    ReferenceDataImport.referenceid == reference.id
                ).one_or_none()
            )
        )
    elif request.method == "PUT":
        importer_state = import_state_for_referenceid(referenceid)
        if not importer_state:
            log.debug(
                f"no import state in database for {referenceid}, creating a new one"
            )
            importer_state = ReferenceDataImport(referenceid)
            db.session.add(importer_state)
            db.session.commit()
        else:
            importer_state.refereceid = referenceid
        importer_state.last_task_pid = request.json.get("last_task_pid")
        setattr(
            importer_state, "current_version", int(request.json.get("current_version"))
        )
        for k in ReferenceDataImport.change_allowed:
            value = request.json.get(k, None)
            if value:
                setattr(importer_state, k, value)
        db.session.commit()
        return jsonify(referencedataimport_schema.dump(importer_state)), 200
    elif request.method == "PATCH":
        importer_state = import_state_for_referenceid(referenceid)
        if not importer_state:
            return jsonify({"message": "No importer_state found"}), 404
        for k, v in request.json.items():
            if k in ReferenceDataImport.change_allowed:
                setattr(importer_state, k, v)
        db.session.commit()
        return jsonify(referencedataimport_schema.dump(importer_state)), 200

    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/reference/<referenceid>/versions", methods=["POST"])
@auth.login_required
def auth_handle_referencedataversions(referenceid):
    return handle_referencedataversions(referenceid)


@bp.route("/reference/<referenceid>/versions", methods=["GET"])
def handle_referencedataversions(referenceid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    if request.method == "GET":
        return jsonify(
            referencedataversions_schema.dump(
                ReferenceDataVersion.query.filter(
                    ReferenceDataVersion.referenceid == reference.id
                ).all()
            )
        )
    elif request.method == "POST":
        version = request.json.get("version")
        dataset_id = request.json.get("dataset_id")
        version_name = request.json.get("version_name", "")
        new_referencedataversion = ReferenceDataVersion(
            reference.id, version, version_name, dataset_id
        )
        db.session.add(new_referencedataversion)
        db.session.commit()
        notify(
            reference.id,
            OBJECTS.reference_data,  # this is the object-type the contacts are stored on!
            displayname(),
            OBJECTS.reference_data_version,  # this is the object-type the change occured on!
            reference.id,
            "A new version of a reference dataset was imported",
        )
        return jsonify(referencedataversion_schema.dump(new_referencedataversion)), 200
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/reference/<referenceid>/versions/<versionid>", methods=["PUT", "DELETE"])
@auth.login_required
def auth_handle_referencedataversion(referenceid, versionid):
    return handle_referencedataversion(referenceid, versionid)


@bp.route("/reference/<referenceid>/versions/<versionid>", methods=["GET"])
def handle_referencedataversion(referenceid, versionid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    reference_version = ReferenceDataVersion.query.filter(
        ReferenceDataVersion.id == versionid
    ).one_or_none()
    if not reference_version:
        return (
            jsonify({"message": f"ReferenceDataVersion {reference_version} not found"}),
            404,
        )
    if request.method == "GET":
        return jsonify(
            referencedataversion_schema.dump(
                ReferenceDataVersion.query.filter(
                    ReferenceDataVersion.id == versionid
                ).one_or_none()
            )
        )
    elif request.method == "PUT":
        for key, value in request.json.items():
            if key in ReferenceDataVersion.change_allowed:
                setattr(reference_version, key, value)
            else:
                return jsonify({"message": f"Not allowed to change {key}"}), 404
        db.session.commit()
        return jsonify(referencedataversion_schema.dump(reference_version)), 200
    elif request.method == "DELETE":
        version = ReferenceDataVersion.query.filter(
            ReferenceDataVersion.id == versionid
        ).one_or_none()
        if version:
            db.session.delete(version)
            db.session.commit()
            return jsonify({"message": "OK"}), 200
        else:
            return (
                jsonify(
                    {
                        "message": f"ReferenceDataVersion {reference_version} for referenceid {referenceid} not found"
                    }
                ),
                404,
            )
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405


@bp.route("/reference/<referenceid>/versionreference/<versionid>", methods=["GET"])
def handle_referencedataversionreference(referenceid, versionid):
    reference = reference_from_id(referenceid)
    if not reference:
        return jsonify({"message": f"ReferenceData {referenceid} not found"}), 404
    # versionid can be:
    #  * latest
    #  * number referring to version field
    #  * uuid referring to dataset_id
    #  * name referring to version_name
    if versionid == "latest":
        reference_version = (
            ReferenceDataVersion.query.filter(
                ReferenceDataVersion.referenceid == reference.id
            )
            .order_by(desc(ReferenceDataVersion.version))
            .limit(1)
            .one_or_none()
        )
    elif versionid.isnumeric():
        reference_version = (
            ReferenceDataVersion.query.filter(
                ReferenceDataVersion.referenceid == reference.id
            )
            .filter(ReferenceDataVersion.version == versionid)
            .one_or_none()
        )
    elif is_valid_uuid(versionid):
        reference_version = ReferenceDataVersion.query.filter(
            ReferenceDataVersion.dataset_id == versionid
        ).one_or_none()
    else:
        reference_version = (
            ReferenceDataVersion.query.filter(
                ReferenceDataVersion.referenceid == reference.id
            )
            .filter(ReferenceDataVersion.version_name == versionid)
            .one_or_none()
        )

    if not reference_version:
        return (
            jsonify({"message": f"ReferenceDataVersion {versionid} not found"}),
            404,
        )
    if request.method == "GET":
        return jsonify(
            referencedataversion_schema.dump(
                ReferenceDataVersion.query.filter(
                    ReferenceDataVersion.id == reference_version.id
                ).one_or_none()
            )
        )
    else:
        return jsonify({"message": f"Method {request.method} not allowed"}), 405
