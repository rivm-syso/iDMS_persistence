#!usr/bin/env python3

import os
import logging
import logging.handlers
from flask import Flask, jsonify, g
from flask_migrate import Migrate
from idms.persistence.notifications import mailqueue_run
from idms.persistence.logging_module import loghandlers
from idms.persistence.models.Model import db

LOG_HANDLERS = {"bio-rest.log": logging.DEBUG, "bio-rest.err": logging.ERROR}
LOG_FORMAT = "%(asctime)s|%(name)s %(levelname)s: %(message)s"
LOG_PARAMS = {"when": "D", "interval": 5, "backupCount": 20}

migrate = Migrate()


def create_app(test_config=None):
    instance_path = os.environ.get("BIO_REST_INSTANCE_PATH")

    # Initialize app
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

    # Load configuration
    app.config.from_mapping(SECRET_KEY="2480fhsdf24fsdsac")

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    if app.config.get("LOG_SYSLOG"):
        loghandlers.log_to_syslog(log, "bio_rest", logging.DEBUG)
    if logfile := app.config.get("LOG_FILE"):
        loghandlers.log_to_file(log, logfile, logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)
    for name, level in LOG_HANDLERS.items():
        try:
            handler = logging.handlers.TimedRotatingFileHandler(
                os.path.join(app.instance_path, name), **LOG_PARAMS
            )
            handler.setFormatter(formatter)
            handler.setLevel(level)
            log.addHandler(handler)
        except IOError as e:
            log.error("Could not add log handler:\n{}".format(str(e)))

    @app.route("/hello")
    def hello():
        return jsonify({"message": "Hello World!"})

    # import ensures the models being loaded and mapped before the blueprints
    # use print(db.Model.registry.mappers) to see all mapped models

    db.init_app(app)
    migrate.init_app(app, db)

    # need to load all the models first by importing them before using the schemas
    from . import api

    app.register_blueprint(api.bp)

    from .auth import cache

    cache.init_app(app)

    @app.teardown_request
    def cleanup(exc=None):
        if hasattr(g, "sess"):
            g.sess.cleanup()

    return app


def mail_run():
    app = create_app()
    with app.app_context():
        mailqueue_run(app, db)
