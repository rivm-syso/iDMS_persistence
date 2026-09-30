import logging
import smtplib
import datetime

from flask import render_template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from idms.persistence.models.Model import Contact, Notification, db

log = logging.getLogger(__name__)

SENDER_ADDRESS = "noreply@rivm.nl"


def notify(entity_id, entity_type, author, objecttype, objectname, message):
    """Add a notification message for the specified project_id

    Args:
        project_id (int): projectproject_idid of the affected project
        message (str):  Notification message for this project
    """
    entity_contacts = (
        Contact.query.filter(
            Contact.entity_id == entity_id, Contact.entity_type == entity_type
        )
        .filter(Contact.notify_config_changes == 1)
        .all()
    )
    for contact in entity_contacts:
        new_notification = Notification(
            contact.id, entity_id, entity_type, author, objecttype, objectname, message
        )
        db.session.add(new_notification)
    db.session.commit()


def email_message(sender, recipient_name, subject, body):
    """Generate emailmessage from template

    Args:
        sender (string): Sender Mail Address
        recipient_name (string): _description_
        subject (string) : Recipient name
        body (string): mail body
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient_name
    message.attach(MIMEText(body, "html"))
    return message


def mailqueue_run(app, db):
    #   Send consolidated email messages to a contact when
    #   1) There are no new messages for this contact in the last MAIL_CONSOLIDATE_WAIT_TIME seconds
    #    or
    #   2) The oldest unsent message is older than MAX_MAIL_DELAY_TIME seconds
    #
    smtp_object = smtplib.SMTP("localhost")
    min_dt = datetime.datetime.now() - datetime.timedelta(
        0, app.config.get("MAIL_CONSOLIDATE_WAIT_TIME"), 900
    )
    max_dt = datetime.datetime.now() - datetime.timedelta(
        0, app.config.get("MAX_MAIL_DELAY_TIME"), 86400
    )
    # First find the email addresses we have messages for
    qry = "SELECT DISTINCT MIN(N.messagetime) as min_msgtime, MAX(N.messagetime) as max_msgtime, C.name, C.email FROM notifications N inner join contacts C on N.contactid = C.id WHERE N.sendtime IS NULL GROUP BY C.name, C.email"
    recipients = db.session.execute(qry)
    for recipient in recipients:
        if recipient.name is None:
            continue
        if type(recipient.min_msgtime) == "str":
            min_msg_dt = datetime.datetime.fromisoformat(recipient.min_msgtime)
        else:
            min_msg_dt = recipient.min_msgtime
        if type(recipient.max_msgtime) == "str":
            max_msg_dt = datetime.datetime.fromisoformat(recipient.max_msgtime)
        else:
            max_msg_dt = recipient.max_msgtime
        if min_msg_dt > max_dt and max_msg_dt > min_dt:
            continue
        # Select all unsent messages for this email addres for PROJECTS!
        log.info(f"Select project specific messages for {recipient.email}")
        qry = "SELECT P.name as project, N.* FROM notifications N inner join contacts C on N.contactid=C.id INNER JOIN projects P on N.entity_id=P.id WHERE N.entity_type = 'Project' AND N.sendtime is NULL AND C.email = :ml"
        proj_messages = sorted(
            list(db.session.execute(qry, {"ml": recipient.email})),
            key=lambda m: m.messagetime,
        )
        # Group messages by project:
        project_messages = {
            message.project: [
                projmsg
                for projmsg in proj_messages
                if projmsg.project == message.project
            ]
            for message in proj_messages
        }

        message_body = render_template("mailtemplate.html", messages=project_messages)
        recipient_name = f"{recipient.name} <{recipient.email}>"
        message = email_message(
            SENDER_ADDRESS,
            recipient_name,
            "Configuration change report for iRODS projects",
            message_body,
        )
        smtp_object.sendmail("noreply@rivm.nl", recipient.email, message.as_string())

        # Select all unsent messages for this email addres for REFERENCEDATA!
        log.info(f"Select refdata specififc messages for {recipient.email}")
        qry2 = "SELECT R.name as refdata, N.* FROM notifications N inner join contacts C on N.contactid=C.id INNER JOIN referencedata R on N.entity_id=R.id WHERE N.entity_type = 'Reference Data' AND N.sendtime is NULL AND C.email = :ml"
        ref_messages = sorted(
            list(db.session.execute(qry2, {"ml": recipient.email})),
            key=lambda m: m.messagetime,
        )
        # Group messages by refdataset:
        refdata_messages = {
            message.refdata: [
                refmsg for refmsg in ref_messages if refmsg.refdata == message.refdata
            ]
            for message in ref_messages
        }

        message_body = render_template(
            "mailtemplate.html",
            project_messages=project_messages,
            refdata_messages=refdata_messages,
        )
        recipient_name = f"{recipient.name} <{recipient.email}>"
        message = email_message(
            SENDER_ADDRESS,
            recipient_name,
            "Configuration change report for iRODS projects",
            message_body,
        )
        smtp_object.sendmail("noreply@rivm.nl", recipient.email, message.as_string())

        for message in proj_messages:
            notification = Notification.query.filter(
                Notification.id == message.id
            ).one_or_none()
            notification.sendtime = datetime.datetime.now()
        for message in ref_messages:
            notification = Notification.query.filter(
                Notification.id == message.id
            ).one_or_none()
            notification.sendtime = datetime.datetime.now()
        db.session.commit()
