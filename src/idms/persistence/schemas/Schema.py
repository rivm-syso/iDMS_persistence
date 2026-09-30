from marshmallow import Schema, fields, validate
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, remote, foreign, backref
from sqlalchemy import ForeignKey, text, UniqueConstraint
from datetime import datetime, timezone
from idms.persistence.models.Model import *

ma = Marshmallow()


### SCHEMAS ###
class ContactSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Contact


class ContactsSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    entity_id = fields.String()
    entity_type = fields.String()
    name = fields.String(required=True)
    email = fields.String(required=True)
    primary = fields.Integer()
    notify_data = fields.Integer()
    notify_pipeline = fields.Integer()
    notify_errors = fields.Integer()
    notify_config_changes = fields.Integer()


class ProjectsSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(1))
    description = fields.String()
    default_collection = fields.String()
    # TODO: maybe for the oerview could be restricted to primary contacts?
    contacts = fields.Nested("ContactSchema", many=True)
    # Smart hyperlinking
    # _links = ma.Hyperlinks(
    #     {"self": ma.URLFor("resources.Projects.ProjectResource.get", id="<id>"), "collection": ma.URLFor("resources.Projects.ProjectsResource.get")}
    # )


class ProjectSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Project

    contacts = fields.Nested("ContactSchema", many=True)


class ProcessesSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    description = fields.String()
    projectid = fields.String()
    repo = fields.String()
    tag = fields.String()
    lsf_queue = fields.String()
    next_projectid = fields.Integer()
    next_processid = fields.Integer()
    modify_in_place = fields.Integer()
    processid = fields.String()
    restartable = fields.Integer()
    distribution = fields.Integer()
    omit_staging = fields.Integer()
    omit_bringonline = fields.Integer()
    concurrency_limit = fields.Integer()
    max_runtime = fields.Integer()
    required_memory = fields.Integer()
    compatible_clusters = fields.List(fields.String())


class Process2Schema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Process2


class Processes2Schema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    description = fields.String()


class ProcessgroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessGroup


class ProcessRefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessRef

    processid = fields.Integer()


class ProcessDependencySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessDependency

    depends_on = fields.Integer()
    processrefid = fields.Integer()


class ReferenceDataImportSchema(ma.SQLAlchemyAutoSchema):
    referenceid = ma.auto_field(dump_only=True)

    class Meta:
        model = ReferenceDataImport


class ReferenceDataSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReferenceData

    contacts = fields.Nested(ContactSchema, many=True)
    data_import = fields.Nested(ReferenceDataImportSchema, many=False)


class ReferenceDataVersionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReferenceDataVersion

    referenceid = fields.Integer()


class ReferenceDataVersionForProcessSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReferenceDataVersionForProcess

    processid = fields.Integer()
    referencedataid = fields.Integer()
    referencedataversionid = fields.Integer()
    referencedataversion = fields.Nested(ReferenceDataVersionSchema, many=False)
    referencedata = fields.Nested(ReferenceDataSchema, many=False)
    label = fields.String(required=True)


class ReferenceDataVersionForProcessRefSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ReferenceDataVersionForProcessRef

    processrefid = fields.Integer()
    referencedataid = fields.Integer()
    supersedingversionid = fields.Integer()
    processdefaultid = fields.Integer()
    # the direct connection to reference data might not be necessary, since its included in processreferencedataversion
    referencedata = fields.Nested(ReferenceDataSchema, many=False)
    supersedingversion = fields.Nested(ReferenceDataVersionSchema, many=False)
    processdefault = fields.Nested(ReferenceDataVersionSchema, many=False)
