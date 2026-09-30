import copy
import logging
import ssl
from flask import current_app, g
from flask_httpauth import HTTPBasicAuth
from irods.exception import CAT_INVALID_AUTHENTICATION
from irods.session import iRODSSession
from idms.persistence.constant import USER_CONNECT_PARAMETERS, DEFAULT_CONNECT_PARAMETERS
from idms.persistence.iconnect import Connection2
from flask_caching import Cache

logger = logging.getLogger(__name__)
cache = Cache()

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    native_password = get_irods_pw_cached(username, password)
    if native_password is None:
        cache.delete_memoized(get_irods_pw_cached)
        native_password = get_irods_pw_cached(username, password)
    if native_password is None:
        return False
    if not hasattr(g, 'sess'):
        return irods_login(username, native_password)
    return True

def irods_login_pam(username, password):
    return irods_login(username, password, authentication_scheme="pam_password")

def irods_login(username, password, authentication_scheme="native"):
    if current_app.testing:
        return True

    context = ssl._create_unverified_context(
        purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None
    )

    ssl_settings = {
        "irods_client_server_negotiation": "request_server_negotiation",
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_ssl_ca_certificate_file": "dummy",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_encryption_key_size": 32,
        "irods_encryption_num_hash_rounds": 16,
        "irods_encryption_salt_size": 8,
        "ssl_context": context,
    }

    user_connect_param = copy.deepcopy(DEFAULT_CONNECT_PARAMETERS)
    connect_parms = current_app.config.get("IRODS_INTERNAL", {})
    for key in USER_CONNECT_PARAMETERS:
        if key in connect_parms:
            user_connect_param[key] = connect_parms.get(key)

    user_connect_param.update(
        {
            "user": username,
            "password": password,
            "authentication_scheme": authentication_scheme,
        }
    )
    user_connect_param.update(ssl_settings)

    irodsSession = iRODSSession(**user_connect_param)
    try:
        irodsSession.collections.get("/")
    except CAT_INVALID_AUTHENTICATION:
        logger.error(f"Password failed for user {username}")
        return False
    except Exception as ex:
        logger.error(f"Unknown authentication error for {username}: {ex}")
        return False

    g.sess = irodsSession
    g.user = irodsSession.users.get(username)
    g.username = username

    return True

@cache.memoize(timeout=3600)
def get_irods_pw_cached(username, password):
    return get_irods_pw(username, password)

def get_irods_pw(username, password):
    context = ssl._create_unverified_context(
        purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None
    )

    ssl_settings = {
        "irods_client_server_negotiation": "request_server_negotiation",
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_ssl_ca_certificate_file": "dummy",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_encryption_key_size": 32,
        "irods_encryption_num_hash_rounds": 16,
        "irods_encryption_salt_size": 8,
        "ssl_context": context,
    }

    user_connect_param = copy.deepcopy(DEFAULT_CONNECT_PARAMETERS)
    connect_parms = current_app.config.get("IRODS_INTERNAL", {})
    for key in USER_CONNECT_PARAMETERS:
        if key in connect_parms:
            user_connect_param[key] = connect_parms.get(key)
    user_connect_param.update(
        {
            "user": username,
            "password": password,
            "authentication_scheme": "pam_password",
        }
    )
    user_connect_param.update(ssl_settings)
    irodsSession = iRODSSession(**user_connect_param)
    try:
        conn = Connection2(irodsSession.pool, irodsSession.pool.account)
        irodsSession.collections.get('/')
    except:
        return None
    native_password = conn.native_password
    g.sess = irodsSession
    g.user = irodsSession.users.get(username)
    g.username = username

    return native_password