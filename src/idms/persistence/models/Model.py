import uuid
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, remote, foreign, backref
from sqlalchemy import ForeignKey, text, UniqueConstraint
from sqlalchemy.exc import AmbiguousForeignKeysError
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.hybrid import hybrid_property
import enum

db = SQLAlchemy()


class Table(enum.Enum):
    projects = 1
    referencedata = 2
    processes2 = 3


class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    # refdataid = db.Column(db.Integer, db.ForeignKey('referencedata.id'), nullable=True)
    # project = relationship("Project", back_populates="contact")
    # referencedata = relationship("ReferenceData", back_populates="contact")

    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    primary = db.Column(db.Integer, default=0)
    notify_data = db.Column(db.Integer, server_default="0")
    notify_pipeline = db.Column(db.Integer, server_default="0")
    notify_errors = db.Column(db.Integer, server_default="0")
    notify_config_changes = db.Column(db.Integer, server_default="0")
    contact_notifications = relationship(
        "Notification", cascade="all,delete", backref="notifications"
    )

    # @hybrid_property
    # def foreign_id(self):
    #    if self.projectid and self.refdataid:
    #        raise AmbiguousForeignKeysError(f"found two foreignkeys for contact {self.id}")
    #    return self.projectid or self.refdataid

    def __init__(
        self,
        entity_id,
        entity_type,
        name,
        email,
        primary=0,
        notify_data=0,
        notify_pipeline=0,
        notify_errors=0,
        notify_config_changes=0,
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.name = name
        self.email = email
        self.primary = primary
        self.notify_data = notify_data
        self.notify_pipeline = notify_pipeline
        self.notify_errors = notify_errors
        self.notify_config_changes = notify_config_changes


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    messagetime = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    # A notification entry will be created FOR EACH contact associated with the entity (see 'notifications.notify(...)
    # This makes querying by contact and or entity easier (a join would have been possible as well)
    contactid = db.Column(db.Integer, db.ForeignKey("contacts.id"))
    # projectid = db.Column(db.Integer, db.ForeignKey('projects.id'))
    entity_id = db.Column(db.Integer, nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    author = db.Column(db.String(50))
    objecttype = db.Column(db.String(50))
    objectname = db.Column(db.String(50))
    message = db.Column(db.String(4000), default="")
    sendtime = db.Column(db.TIMESTAMP)

    def __init__(
        self, contactid, entity_id, entity_type, author, objecttype, objectname, message
    ):
        self.contactid = contactid
        # self.projectid = projectid
        self.entity_id = (entity_id,)
        self.entity_type = entity_type
        self.author = author
        self.objecttype = objecttype
        self.objectname = objectname
        self.message = message


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4)
    description = db.Column(db.String(250), default="")
    # new_description = db.Column(db.String(250))
    creation_date = db.Column(db.TIMESTAMP, default=datetime.now(timezone.utc))
    service_account = db.Column(db.String(32), default="")
    # new_service_account = db.Column(db.String(32))
    default_collection = db.Column(db.String(250), default="")
    # new_default_collection = db.Column(db.String(250))
    user_group = db.Column(db.String(64))
    manager_group = db.Column(db.String(64))
    owner = db.Column(db.String(32))
    # contacts = relationship( "Contact", order_by=Contact.name, backref='contact', lazy=True)
    last_updated = db.Column(db.TIMESTAMP, default=datetime.now(timezone.utc))
    last_verified = db.Column(db.TIMESTAMP, nullable=True)
    last_maintenance = db.Column(db.TIMESTAMP, nullable=True)
    department = db.Column(db.String(32), nullable=True)

    # Is this a project with public accessible data?
    public = db.Column(db.Integer, server_default="0")
    # Does this project use automatic pipelines?
    pipelines = db.Column(db.Integer, server_default="1")

    change_allowed = [
        "description",
        "service_account",
        "default_collection",
        "public",
        "pipelines",
        "department",
    ]
    sys_change_allowed = [
        "description",
        "service_account",
        "default_collection",
        "manager_group",
        "user_group",
        "public",
        "pipelines",
        "last_maintenance",
        "department",
    ]

    processgroups = relationship("ProcessGroup", back_populates="project")

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner


class Process(db.Model):
    """NOT A DATABASE MODEL.

    This is an extended version of the Process2 model, which IS in the database.
    Process is mainly used to create a list of processes including the git tag
    which you can choose from when starting a process manually in the iDMS.
    """

    __tablename__ = "processes"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    projectid = db.Column(db.Integer, db.ForeignKey("projects.id"))
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(250), default="")
    output_prefix = db.Column(db.String(500))  # TODO : this is not used anywhere
    next_projectid = db.Column(db.Integer)
    next_processid = db.Column(db.Integer)
    processid = db.Column(db.String(64))
    distribution = db.Column(db.Integer, default=0)
    modify_in_place = db.Column(db.Integer, default=0)
    restartable = db.Column(db.Integer, default=0)
    omit_staging = db.Column(db.Integer, default=0)
    omit_bringonline = db.Column(db.Integer, default=0)
    repo = db.Column(db.String(512), default="")
    tag = db.Column(db.String(64), default="")
    lsf_queue = db.Column(db.String(64), default="")
    concurrency_limit = db.Column(db.Integer, server_default=text("0"))
    max_runtime = db.Column(db.Integer, server_default=text("0"))
    compatible_clusters = db.Column(db.JSON)
    required_memory = db.Column(db.Integer, server_default=text("0"))

    def __init__(self, projectid, name, processid=None):
        self.projectid = projectid
        self.name = name
        if processid:
            self.processid = processid
        else:
            self.processid = name


class Process2(db.Model):
    __tablename__ = "processes2"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(250), default="")
    output_prefix = db.Column(db.String(500))  # TODO : this is not used anywhere
    distribution = db.Column(db.Integer, default=0)
    modify_in_place = db.Column(
        db.Integer, default=0
    )  # TODO: maybe this can go/be renamed
    restartable = db.Column(db.Integer, default=0)  # TODO: maybe this can go
    omit_staging = db.Column(db.Integer, default=0)
    omit_bringonline = db.Column(db.Integer, default=0)
    repo = db.Column(db.String(512), default="")
    manager_group = db.Column(db.String(64))
    concurrency_limit = db.Column(db.Integer, server_default=text("0"))
    max_runtime = db.Column(db.Integer, server_default=text("0"))
    compatible_clusters = db.Column(
        db.JSON
    )
    # type: list[str], we do not use db.ARRAY for compatibility with sqlite
    required_memory = db.Column(db.Integer, server_default=text("0"))

    def __init__(self, name):
        self.name = name


class ProcessGroup(db.Model):
    __tablename__ = "processgroup"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    projectid = db.Column(db.Integer, db.ForeignKey("projects.id"))
    name = db.Column(db.String(64), default="default")
    description = db.Column(db.String(250), default="")
    processrefs = relationship("ProcessRef", back_populates="processgroup")
    project = relationship("Project", back_populates="processgroups")

    def __init__(self, projectid, name):
        self.projectid = projectid
        self.name = name


class ProcessRef(db.Model):
    __tablename__ = "processref"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    processgroupid = db.Column(db.Integer, db.ForeignKey("processgroup.id"))
    processid = db.Column(db.Integer, db.ForeignKey("processes2.id"))
    tag = db.Column(db.String(64), default="")
    input = db.Column(db.Integer)
    lsf_queue = db.Column(db.String(64), default=None)
    name = db.Column(db.String(64), nullable=False)

    processgroup = relationship("ProcessGroup", back_populates="processrefs")

    def __init__(self, processgroupid, name, processid):
        self.name = name
        self.processgroupid = processgroupid
        self.input = 0
        self.processid = processid


class ProcessDependency(db.Model):
    __tablename__ = "processdependencies"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    processrefid = db.Column(db.Integer, db.ForeignKey("processref.id"))
    dependency_type = db.Column(db.String(32))
    depends_on = db.Column(db.Integer, db.ForeignKey("processref.id"))

    def __init__(self, processrefid, depends_on):
        self.processrefid = processrefid
        self.depends_on = depends_on


class ReferenceData(db.Model):
    __tablename__ = "referencedata"
    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String())
    repository = db.Column(db.String(512), nullable=True)
    tag = db.Column(db.String(100), nullable=True)
    synchronize_command = db.Column(db.String(250))
    precheck_command = db.Column(db.String(250))
    execution_environment = db.Column(db.String(50), default="local")
    update_frequency = db.Column(db.Integer)
    synchronization_frequency = db.Column(db.Integer)
    owner = db.Column(db.String(64))
    is_active = db.Column(db.Integer, server_default=text("0"))
    category = db.Column(db.String(250))

    # contacts = relationship( "Contact", order_by=Contact.name, backref='contacts', cascade="all, delete-orphan", lazy=True)
    import_state = relationship(
        "ReferenceDataImport",
        backref="referencedataimport",
        uselist=False,
        cascade="all, delete-orphan",
    )

    change_allowed = [
        "description",
        "repository",
        "tag",
        "synchronize_command",
        "precheck_command",
        "execution_environment",
        "update_frequency",
        "synchronization_frequency",
        "owner",
        "is_active",
        "category",
    ]

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner


class ReferenceDataImport(db.Model):
    __tablename__ = "referencedataimport"
    id = db.Column(db.Integer, primary_key=True)

    referenceid = db.Column(db.Integer, db.ForeignKey("referencedata.id"), unique=True)
    last_task_pid = db.Column(db.String(64), default="")
    last_task_changed = db.Column(db.Integer, default=0)
    last_task = db.Column(db.String(64), default="")
    last_task_message = db.Column(db.String(), default="")
    error_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.Integer, default=0)
    last_synchronized = db.Column(db.Integer, default=0)
    last_prechecked = db.Column(db.Integer, default=0)
    current_version = db.Column(db.Integer, default=-1)
    dataset_id = db.Column(db.String(36), default="")
    change_allowed = [
        "last_task_pid",
        "last_updated",
        "last_synchronized",
        "last_prechecked",
        "current_version",
        "dataset_id",
        "error_count",
        "last_task",
        "last_task_changed",
        "last_task_message",
    ]

    def __init__(self, referenceid):
        self.referenceid = referenceid


class ReferenceDataVersion(db.Model):
    __tablename__ = "refdataversion"
    __table_args__ = (
        UniqueConstraint(
            "referenceid", "version", name=f"{__tablename__}_referenceid_version_uc"
        ),
        UniqueConstraint("dataset_id", name=f"{__tablename__}_dataset_id_uc"),
    )
    id = db.Column(db.Integer, primary_key=True)
    referenceid = db.Column(db.Integer, db.ForeignKey("referencedata.id"))
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    version = db.Column(db.Integer, nullable=False)
    version_name = db.Column(db.String(100))
    dataset_id = db.Column(db.String(36), nullable=False)
    is_valid = db.Column(db.Integer, server_default=text("1"))

    change_allowed = ["version_name", "is_valid"]

    def __init__(self, referenceid, version, version_name, dataset_id):
        self.referenceid = referenceid
        self.version = version
        self.version_name = version_name
        self.dataset_id = dataset_id


# https://stackoverflow.com/questions/5033547/sqlalchemy-cascade-delete
class ReferenceDataVersionForProcess(db.Model):
    __tablename__ = "refdataversion2process"
    id = db.Column(db.Integer, primary_key=True)
    referencedataid = db.Column(
        db.Integer, db.ForeignKey("referencedata.id", ondelete="CASCADE")
    )
    referencedataversionid = db.Column(
        db.Integer, db.ForeignKey("refdataversion.id", ondelete="CASCADE")
    )
    processid = db.Column(
        db.Integer, db.ForeignKey("processes2.id", ondelete="CASCADE")
    )
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )
    label = db.Column(db.String(255), nullable=False)

    referencedataversion = relationship(
        "ReferenceDataVersion",
        backref=backref("referencedataversionInProcess", passive_deletes=True),
    )
    referencedata = relationship(
        "ReferenceData", backref=backref("referencedataInProcess", passive_deletes=True)
    )

    change_allowed = ["referencedataversionid"]

    def __init__(self, referencedataid, referencedataversionid, processid, label):
        self.referencedataid = referencedataid
        self.referencedataversionid = referencedataversionid
        self.processid = processid
        self.label = label


class ReferenceDataVersionForProcessRef(db.Model):
    __tablename__ = "refdataversion2processref"
    id = db.Column(db.Integer, primary_key=True)
    processrefid = db.Column(
        db.Integer, db.ForeignKey("processref.id", ondelete="CASCADE")
    )
    supersedingversionid = db.Column(
        db.Integer, db.ForeignKey("refdataversion.id", ondelete="CASCADE")
    )
    processdefaultid = db.Column(
        db.Integer, db.ForeignKey("refdataversion2process.id", ondelete="CASCADE")
    )
    creation_date = db.Column(
        db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False
    )

    # This is the Version which will overwriten (supersede) the default as defined in the process. I.e. the version the pipeline should use.
    supersedingversion = relationship(
        "ReferenceDataVersion",
        backref=backref("supersedingversion", passive_deletes=True),
    )
    # If the superseding version isnt set the process itself might have a version configured.
    # I.E. the processDefault contains the ReferenceDataVersionForProcess defining the version on a process.
    processdefault = relationship(
        "ReferenceDataVersionForProcess",
        backref=backref("processdefault", passive_deletes=True),
    )

    change_allowed = ["referencedataversionid"]

    def __init__(self, processrefid, supersedingversionid, processdefaultid):
        self.processrefid = processrefid
        self.supersedingversionid = supersedingversionid
        self.processdefaultid = processdefaultid
