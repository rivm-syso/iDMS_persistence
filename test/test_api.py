import json
import re
import pytest

from idms.persistence import create_app
from idms.persistence.models.Model import db
from irods.models import Group
from irods.meta import iRODSMeta
from irods.exception import GroupDoesNotExist

TEST_CONFIG = {
    "ATTR_PROJECTID": "projectID",
    "ATTR_PROCESSID": "processID",
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "postgresql://postgres:password@:9876/projectdb?host=/tmp",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "MAX_GROUP_UNROLL_LEVELS": 1,
    "PROJECT_CREATORS_GROUP": "admins_group",
    "LDAP_SERVER": "dummy",
    "AD_USER_RW": "rw_user",
    "AD_USER_RW_PWD": "top_secret",
    "IRODS_INTERNAL": {"user": "rods"},
    "GROUP_TEMPLATES": {
        "project-users": "G-FUN-Irot1_{}",
        "project-admins": "L-AUT-Irot1_{}",
        "process-admins": "L-AUT-Irot1pr_{}",
    },
    "PROJECT_COLLECTION_TEMPLATE": "/{}/projects/{}",
    "SYSTEM_USER": "system_user"
}

TEST_PROCESS = "/api/1.0/processes/pr1"
TEST_PROJECT = "/api/1.0/projects/test1"
TEST_SYS_PROJECT = "/api/1.0/sys/projects/test1"
TEST_PG = "/api/1.0/projects/ngslab/processgroups/pg1"
TEST_PROCREF = "/api/1.0/projects/ngslab/processgroups/pg1/processes/pr1"
TEST_REFERENCE = "/api/1.0/reference/refdb1"
TEST_REFVERSION = "/api/1.0/reference/refdb1/versions/1"
TEST_ZONE = "testZone"

TEST_PARAMETERS = [
    (TEST_PROCESS, "repo", "https://some.git.server/location"),
    (TEST_PROCESS, "description", "New process description"),
    (TEST_PROCESS, "distribution", 1),
    (TEST_PROCESS, "modify_in_place", 1),
    (TEST_PROCESS, "concurrency_limit", 4),
    (TEST_PROCESS, "max_runtime", 86400),
    (TEST_PROCESS, "restartable", 1),
    (TEST_PG, "description", "NGSLAB new description"),
    (TEST_PROCREF, "tag", "some_git_tag"),
    (TEST_PROCREF, "input", 17),
    (TEST_PROCREF, "lsf_queue", "prio-jobs"),
    (TEST_REFERENCE, "synchronize_command", "wget http://location/version"),
#    (TEST_REFVERSION, "version_name", "3.5"),
]

TEST_ILLEGAL_PARAMETERS = [
    (TEST_PROCESS, "tag", "new_git_tag"),
    (TEST_PG, "projectid", 2),
    (TEST_PROCREF, "unknown_property", "some_value"),
    (TEST_REFVERSION, "dataset_id", "d33719a6-7197-4f12-ad57-094184e0b47d"),
]

TEST_SYS_PARAMETERS = [
    (TEST_SYS_PROJECT, TEST_PROJECT, "last_maintenance", "2013-08-02T10:38:22")
]

TEST_COLLECTIONS = [f"/{TEST_ZONE}/projects/testproject1"]
TEST_COLL_META = {"attr1": "no_value"}
TEST_USERS = {
    "admin_user": {"sys::ad::displayName": "Admin User"},
    "dummy": {"sys::ad::displayName": "Dummy User"},
}
TEST_GROUPS = {
    "admins_group": {"members": ["admin_user"], "meta": {}},
    "public": {"members": [], "meta": {}}
}
TEST_GROUP_META = {}


class Mock_irodsUser:
    def __init__(self, user="dummy"):
        self.name = user
        self.metadata = Mock_metadata(TEST_USERS.get(user, {}))

    def addmember(self, user):
        pass


class Mock_irodsQuery:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.filters = []

    def filter(self, *args):
        self.filters.append(args)
        return self

    def __iter__(self):
        for gr in TEST_GROUP_META:
            yield {Group.name: gr}


class Mock_metadata:
    def __init__(self, data):
        self.data = data

    def get_one(self, k):
        return iRODSMeta(k, self.data[k])

    def get_all(self, k):
        if k in self.data:
            return [iRODSMeta(k, self.data[k])]
        else:
            return []

    def __setitem__(self, k, v):
        self.data[k] = v.value

    def _delete_all_values(self, key):
        del self.data[key]


class Mock_irodsGroup:
    def __init__(self, name):
        self.name = name
        self.metadata = Mock_metadata(TEST_GROUP_META.get(self.name, {}))

    def addmember(self, user):
        pass

    def hasmember(self, user):
        return user in TEST_GROUPS.get(self.name, {})["members"]


class Mock_groupmanager:
    def __init__(self):
        pass

    def get(self, name):
        if not name in TEST_GROUPS:
            raise GroupDoesNotExist
        return Mock_irodsGroup(name)

    def create(self, name):
        TEST_GROUPS[name] = {"members": [], "meta": {}}
        return Mock_irodsGroup(name)


class Mock_irodsCollection:
    def __init__(self, path):
        self.path = path
        self.metadata = Mock_metadata(TEST_COLL_META)


class Mock_irodsCollManager:
    def __init__(self):
        pass

    def exists(self, path):
        return path in TEST_COLLECTIONS

    def get(self, path):
        return Mock_irodsCollection(path)

    def create(self, path):
        TEST_COLLECTIONS.append(path)
        return Mock_irodsCollection(path)


class Mock_irodsSession:
    def __init__(self, user="dummy", **kwargs):
        self.collections = Mock_irodsCollManager()
        self.groups = Mock_groupmanager()
        self.query = Mock_irodsQuery
        self.user = user
        self.zone = TEST_ZONE

    def cleanup(self):
        pass


class Mock_g:
    def __init__(self, user="dummy"):
        self.username = user
        self.sess = Mock_irodsSession(user=user)
        self.user = Mock_irodsUser(user=user)


@pytest.fixture(autouse=True)
def set_g(monkeypatch):
    monkeypatch.setattr("idms.persistence.auth.get_irods_pw_cached", lambda x, y: "dummy_password")
    monkeypatch.setattr("idms.persistence.auth.irods_login", lambda x, y: True)
    monkeypatch.setattr("idms.persistence.api.g", Mock_g("dummy"))
    monkeypatch.setattr("idms.persistence.irods_functions.g", Mock_g("dummy"))
    monkeypatch.setattr("idms.persistence.irods_functions.iRODSSession", Mock_irodsSession)


@pytest.fixture  #(scope="module")
def client():
    app = create_app(TEST_CONFIG)
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            sqlfile = open("test/testdata.sql")
            sql = sqlfile.read()
            for line in sql.split(";"):
                db.engine.execute(line)
        yield client


def test_hello(client):
    """Get a response to the most basic request."""

    rv = client.get("/hello")
    assert json.loads(rv.data)["message"] == "Hello World!"


@pytest.mark.parametrize(
    "data, message",
    [
        ({}, "Invalid request data: no project name supplied"),
        ({"name": "a_bit_too_long_for_project_id"}, "Max projectname length(24) exceeded"),
    ],
)
def test_invalid_proj_request(client, data, message, monkeypatch):
    my_g = Mock_g(user="admin_user")
    monkeypatch.setattr("idms.persistence.irods_functions.g", my_g)
    monkeypatch.setattr("idms.persistence.api.g", my_g)
    rv = client.post("/api/1.0/projects", json=data)
    assert rv.status_code == 400
    assert json.loads(rv.data)["message"] == message


@pytest.mark.parametrize("projectname", ["dummy_1", "slurpork", "go-ahead"])
def test_new_project(client, monkeypatch, projectname):
    my_g = Mock_g(user="admin_user")
    monkeypatch.setattr("idms.persistence.irods_functions.g", my_g)
    monkeypatch.setattr("idms.persistence.api.g", my_g)

    rv = client.post(
        "/api/1.0/projects",
        json={
            "name": projectname,
        },
    )

    # assert f"/{TEST_ZONE}/projects/{projectname}" in TEST_COLLECTIONS
    # assert TEST_COLL_META.get("projectID") == projectname
    assert rv.status_code == 202


def test_new_project_unauthorized(client, monkeypatch):
    monkeypatch.setattr("idms.persistence.api.g", Mock_g(user="project_admin"))
    rv = client.post(
        "/api/1.0/projects",
        json={
            "name": "dummy_id",
        },
    )

    assert rv.status_code == 401


def test_project_list(client):
    """Test if projects are returned."""

    rv = client.get("/api/1.0/projects")
    print(rv.data)
    assert b'"name":"ngslab"' in rv.data
    assert b'"name":"test1"' in rv.data


def test_create_refdb(client, monkeypatch):
    data = {"name": "refdb_test"}
    rv = client.post("/api/1.0/reference", json=data)
    assert rv.status_code == 201
    rv = client.get("/api/1.0/reference/refdb_test")
    assert rv.status_code == 200


def xtest_referencedataversion_for_process(client, monkeypatch):
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)
    # Get reference data for process
    rv = client.get(f"{TEST_PROCESS}/referencedataversion")
    assert rv.json == [] and rv.status_code == 200
    # Get id for refdb1
    rv = client.get(TEST_REFERENCE)
    assert rv.status_code == 200
    refdb1_id = rv.json["id"]
    # Get id vor version 2 of refdb1
    rv = client.get(f"{TEST_REFERENCE}/versions/2")
    assert rv.status_code == 200
    version_id = rv.json["id"]
    # Check there are no version references
    rv = client.get(f"{TEST_PROCREF}/referencedataversion")
    assert rv.json == [] and rv.status_code == 200
    # Add a specific version reference
    data = {"supersedingversionid": version_id, "chicken": refdb1_id}
    rv = client.post(f"{TEST_PROCREF}/referencedataversion", json=data)
    assert rv.status_code == 201
    # verify the version reference
    rv = client.get(f"{TEST_PROCREF}/referencedataversion")
    assert rv.json[0]["supersedingversion"]["version_name"] == "Version 2"

    # Get my specific version from refdataversion
    rv = client.get(f"/api/1.0/reference/refdb_test")
    data = {}
    rv = client.post(f"{TEST_PROCREF}/referencedataversion", json=data)


@pytest.mark.parametrize(
    "processname, groupname",
    [
        ("doit", "L-AUT-Irot1pr_Doit"),
        ("make a new version of this dataset", "L-AUT-Irot1pr_MaANeVeOfThDa"),
        ("A very Important$ PROCESS application", "L-AUT-Irot1pr_AVerImpProApp"),
    ],
)
def test_create_process(client, processname, groupname, monkeypatch):
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)
    data = {"name": processname}
    rv = client.post("/api/1.0/processes", json=data)
    assert rv.status_code == 201
    assert groupname in TEST_GROUPS
    rv = client.get(f"/api/1.0/processes/{processname}")
    assert rv.status_code == 200


def test_modify_process_non_admin(client, monkeypatch):
    #assume user is not a process manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: False)
    data = {"name": "testprocess1"}
    rv = client.post("/api/1.0/processes", json=data)
    assert rv.status_code == 201
    data = {"description": "new description"}
    rv = client.put("/api/1.0/processes/testprocess1", json=data)
    assert rv.status_code == 401


def test_create_processgroup(client, monkeypatch):

    # assume user is a project manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)

    # Test processgroup creation
    data = {"name": "pgtest"}
    rv = client.post("/api/1.0/projects/ngslab/processgroups", json=data)
    assert rv.status_code == 201
    # Test it can not be created again
    rv = client.post("/api/1.0/projects/ngslab/processgroups", json=data)
    assert rv.status_code == 409
    # Test is is in the list of processgroups
    rv = client.get("/api/1.0/projects/ngslab/processgroups")
    assert rv.status_code == 200
    assert "pgtest" in [pg["name"] for pg in json.loads(rv.data)]
    # Test it can be retrieved directly
    rv = client.get("/api/1.0/projects/ngslab/processgroups/pgtest")
    assert rv.status_code == 200
    # Test it can be deleted
    rv = client.delete("/api/1.0/projects/ngslab/processgroups/pgtest")
    assert rv.status_code == 200


def test_create_processgroup_non_admin(client, monkeypatch):
    # assume user is not a project admin
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: False)
    # Test processgroup creation
    data = {"name": "pgtest"}
    rv = client.post("/api/1.0/projects/ngslab/processgroups", json=data)
    assert rv.status_code == 401


def test_nonexisting_processgroup(client):
    rv = client.get("/api/1.0/projects/ngslab/processgroups/non_existing_group")
    assert rv.status_code == 404  # Not Found


@pytest.mark.parametrize("endpoint, property, value", TEST_PARAMETERS)
def test_update_properties(client, endpoint, property, value, monkeypatch):
    # assume user is a project manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)

    data = {property: value}
    rv = client.put(endpoint, json=data)
    assert rv.status_code == 200
    rv = client.get(endpoint)
    assert json.loads(rv.data)[property] == value


def test_update_properties_non_admin(client, monkeypatch):
    # assume user is not a project manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: False)

    data = {"description": "New project description"}
    r1 = client.put("/api/1.0/projects/ngslab", json=data)
    assert r1.status_code == 401


@pytest.mark.parametrize("endpoint, property, value", TEST_ILLEGAL_PARAMETERS)
def test_illegal_properties(client, endpoint, property, value, monkeypatch):
    # assume user is a project manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)

    data = {property: value}
    r1 = client.get(endpoint)
    rv = client.put(endpoint, json=data)
    assert (
        rv.status_code == 404
    )  # should be 400 Illegal Request (Parameter), 404 would be url/ressource not found?
    rv = client.get(endpoint)
    if property in json.loads(rv.data):
        assert json.loads(rv.data)[property] == json.loads(r1.data)[property]

@pytest.mark.parametrize("put_endpoint, get_endpoint, property, value", TEST_SYS_PARAMETERS)
def test_sys_properties(client, put_endpoint, get_endpoint, property, value, monkeypatch):
    # assume user is a project manager
    monkeypatch.setattr("idms.persistence.api.g", Mock_g("system_user"))

    data = {property: value}
    rv = client.put(put_endpoint, json=data)
    assert rv.status_code == 200
    rv = client.get(get_endpoint)
    assert json.loads(rv.data)[property] == value

def test_bringonline_dependency(client, monkeypatch):
    """Test dependency of omit_bringonline property on omit_staging.
    Since a dataset cannot be staged when it's not brought online."""
    # assume user is a project manager
    monkeypatch.setattr("idms.persistence.api.is_manager", lambda x: True)
    endpoint = "/api/1.0/processes"

    process_data = {
        "name": "test_bringonline",
        "omit_bringonline": 1,
        "omit_staging": 0,
    }
    r_proc_post = client.post(endpoint, json=process_data)
    assert r_proc_post.status_code == 201

    # Test value after POST.
    r_proc_get = client.get("{}/{}".format(endpoint, process_data["name"]))
    proc_stored_data = json.loads(r_proc_get.data)
    assert proc_stored_data["omit_bringonline"] == 0

    r_proc_put = client.put(
        "{}/{}".format(endpoint, process_data["name"]), json=process_data
    )
    assert r_proc_put.status_code == 200

    # Test value after PUT.
    r_proc_get = client.get("{}/{}".format(endpoint, process_data["name"]))
    proc_stored_data = json.loads(r_proc_get.data)
    assert proc_stored_data["omit_bringonline"] == 0


def test_process_references(client):
    endpoint = "/api/1.0"

    r_proc_ref = client.get("{}/{}".format(endpoint, "processes/pr1/references"))
    assert r_proc_ref.status_code == 200
    proc_ref_data = json.loads(r_proc_ref.data)
    assert len(proc_ref_data) == 2
    assert re.match(r'/api/1.0/projects/[0-9]+/processgroups/[0-9]+/processes/[0-9]+', proc_ref_data[0]["url"])
    assert proc_ref_data[0]["project"] == "ngslab"
    assert proc_ref_data[1]["processgroup"] == "pg2"
