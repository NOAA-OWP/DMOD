import os
import pathlib
import typing
import re
import pytz

from pathlib import Path
from datetime import datetime
from datetime import timedelta


def in_debug_mode() -> bool:
    """
    Check to see if the server should be running in debug mode rather than a production environment.

    It is ok to show additional diagnositic information in debug mode, but not production.

    SECURITY WARNING: do not run with debug turned on in production! Diagnostic messages can be used to view
    system environment variables and stack traces.

    Uses the optional `DEBUG` and `DMOD_EVAL_SERVICE_DEBUG` environment variables, equating to
    `DEBUG or DMOD_EVAL_SERVICE_DEBUG`

    Returns:
        Whether the server should run in debug mode
    """
    # Check to see if the global DEBUG value is True
    debug_value = os.environ.get("DEBUG", False)

    # The global DEBUG value is the law of the land; if it says it's in debug mode, it's in debug mode
    if str(debug_value).lower() in ("yes", "y", "1", 'true', 'on', 'debug'):
        return True

    # If the DMOD isn't currently running in debug mode, check to see if the evaluation service itself should be
    # running in debug on its own
    debug_value = os.environ.get("DMOD_EVAL_SERVICE_DEBUG", False)

    return str(debug_value).lower() in ("yes", "y", "1", 'true', 'on', 'debug')


def get_redis_password(password_path_variable: str = None, password_variable_name: str = None) -> typing.Optional[str]:
    """
    Attempts to find a password to the core redis instance, first by checking for a secrets file, then by checking
    an environment variable.

    The optional environment variables that control this are `REDIS_PASSWORD_FILE` for the secret or `REDIS_PASS`
    for the password on its own.

    Args:
        password_path_variable: The path to the secrets file for the password.
        password_variable_name: The name of the environment variable for the password.

    Returns:
        The optional password to the core redis service
    """
    password_filename = os.environ.get(
        password_path_variable or "REDIS_PASSWORD_FILE",
        "/run/secrets/myredis_pass"
    )

    # If a password file has been identified, try to get a password from that
    if os.path.exists(password_filename):
        try:
            with open(password_filename, 'r') as redis_password_file:
                content = redis_password_file.read().rstrip()
                # Only go with the password from the file if there WAS a password in the file
                if len(content) >= 1:
                    return content
        except:
            # Data couldn't be read? Move on to attempting to read it from the environment variable
            pass

    # Fall back to env if no secrets file, further falling back to default if no env value
    return os.environ.get(password_variable_name or "REDIS_PASS")


def get_full_localtimezone():
    """
    Finds the full local timezone name.

    Instead of 'CDT' or 'CST', this will be something like 'America/Chicago'

    Returns:
        The name of the system's timezone
    """
    test_date = datetime.now()

    # It's easy to tell if the system is in UTC; if there isn't an offset, it's UTC, and therefore a format easy to
    # rely on
    if test_date.astimezone().utcoffset() == timedelta(seconds=0):
        return "UTC"

    # If this is a system with 'zoneinfo' set up as part of the environment, parse the name from the linked zone
    zone_path = Path("/etc/localtime")
    # This doesn't actually work in Python 3.8, though does in 3.9
    #zone_path = str(zone_path.readlink()) if zone_path.exists() and zone_path.is_symlink() else ""
    zone_path = str(os.readlink(str(zone_path))) if zone_path.exists() and zone_path.is_symlink() else ""

    # We can predict the path if the zone is linked to a file under 'zoneinfo'.
    if 'zoneinfo' in zone_path:
        name_search = re.search("(?<=zoneinfo/).+$", zone_path)

        # If the found path is indeed preceded by 'zoneinfo/', we can continue on with a check
        if name_search:
            # Get the name of the found timezone
            name = name_search.group()

            # If the found name is in the listing of allowable timezones, we're good to continue
            timezone_name_is_valid = name in pytz.all_timezones
            timezones_match = False

            # Now, test the current informed date with that of a date informed by the found time zone. The stock
            # informed date will have the correct timezone descriptor, but it won't have the descriptor we're
            # looking for ('CDT' instead of 'America/Chicago'). If the offsets for the zone we want matches that of
            # the time zone we infer, we're good to go
            if timezone_name_is_valid:
                expected_timezone = test_date.astimezone().utcoffset()
                proposed_timezone = test_date.astimezone(tz=pytz.timezone(name)).utcoffset()
                timezones_match = expected_timezone == proposed_timezone

            if timezones_match:
                return name

    # A timezone file couldn't be used, so a GMT based time zone will be used instead. There should be a matching
    # time zone for GMT under "Etc/", so that will be the targeted zone.

    # First, get the hour offset for the current timezone
    informed_datetime = test_date.astimezone()
    offset_hours = int(informed_datetime.utcoffset().total_seconds() / 3600)

    # GMT is measured in the opposite direction as UTC offset, so multiply the hours by -1 to get the intended offset
    gmt_hours = offset_hours * -1

    # Plug the adjusted offset hours into the template. If we're currently in 'CDT', that will be 'UTC-0500',
    # which lines up with 'GMT+5', which is accepted as 'Etc/GMT+5'
    timezone_name = f"Etc/GMT{gmt_hours}"

    # If the created timezone is real, we can return that
    if timezone_name in pytz.all_timezones:
        return timezone_name

    # If we still don't have a valid value, just fall back to UTC
    return "UTC"


DEBUG = in_debug_mode()
"""Whether the service is in a non-production, development state"""

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
"""The path to the base directory of the service"""

BASE_DIR = BASE_DIRECTORY
"""The expected Django variable for the base directory"""

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = os.environ.get("EVALUATION_STATIC_URL", '/static/')
"""The URL to direct requests for static resources to"""

STATICFILES_DIRS: typing.Iterable[typing.Union[str, pathlib.Path]] = [
    BASE_DIR / "static"
]
"""Directories that contain static files"""

STATIC_RESOURCES_PATH = os.path.join(BASE_DIR, "static", "resources")
"""The path to static resources that are not code, stylesheets, images, or other standard media"""

APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "Evaluation Service")
"""The name of the service"""

COMMON_DATETIME_FORMAT = "%Y-%m-%d %I:%M:%S %p %Z"
"""The default format for datetime strings"""

CURRENT_TIMEZONE = get_full_localtimezone()
"""The timezone for the service"""

EVALUATION_QUEUE_NAME = os.environ.get("EVALUATION_QUEUE_NAME", "evaluation_jobs")
"""The name for the redis queue through which to communicate jobs through"""

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
"""The host of the core redis service"""

REDIS_PORT = int(os.environ.get("REDIS_PORT")) if "REDIS_PORT" in os.environ else 6379
"""The port of the core redis service"""

REDIS_USERNAME = os.environ.get("REDIS_USER", None)
"""The name of the user for the default redis connection"""

REDIS_PASSWORD = get_redis_password()
"""The password to the cored redis service"""

RUNNER_HOST = os.environ.get("RUNNER_HOST", REDIS_HOST)
"""The host of the redis service used for launching jobs"""

REDIS_DB: typing.Final[int] = int(os.environ.get("REDIS_DB", 0))

RUNNER_PORT = int(os.environ.get("RUNNER_PORT")) if "RUNNER_PORT" in os.environ else REDIS_PORT
"""The port of the redis service used for launching jobs"""

RUNNER_USERNAME = os.environ.get("RUNNER_USERNAME", REDIS_USERNAME)

RUNNER_PASSWORD = get_redis_password(
    password_path_variable="RUNNER_PASSWORD_FILE",
    password_variable_name="RUNNER_PASSWORD"
) or REDIS_PASSWORD

RUNNER_DB: typing.Final[int] = int(os.environ.get("RUNNER_DB", REDIS_DB))

CHANNEL_HOST = os.environ.get("CHANNEL_HOST", REDIS_HOST)
"""The host of the redis service used for communicating job information"""

CHANNEL_PORT = int(os.environ.get("CHANNEL_PORT")) if "CHANNEL_PORT" in os.environ else REDIS_PORT
"""The port of the redis service used for communicating job information"""

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", REDIS_USERNAME)

CHANNEL_PASSWORD = get_redis_password(
    password_path_variable="CHANNEL_PASSWORD_FILE",
    password_variable_name="CHANNEL_PASSWORD"
) or REDIS_PASSWORD

CHANNEL_DB = int(os.environ.get("CHANNEL_DB", REDIS_DB))

CHANNEL_NAME_PATTERN = r'[\w\-_\.]+'
"""The pattern that redis channel names may follow"""

RQ_QUEUES = {
    'default': {
        'HOST': RUNNER_HOST,
        'PORT': RUNNER_PORT,
        'PASSWORD': os.environ.get("RQ_PASSWORD") or REDIS_PASSWORD,
        'DB': 0,
        'DEFAULT_TIMEOUT': 99999,
    },
    EVALUATION_QUEUE_NAME: {
        'HOST': RUNNER_HOST,
        "PORT": RUNNER_PORT,
        "PASSWORD": os.environ.get("RQ_PASSWORD") or REDIS_PASSWORD,
        "DB": 0,
        "DEFAULT_TIMEOUT": 99999
    }
}
"""Default configuration for if RQ is used (RQ credentials will be used regardless)"""

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(CHANNEL_HOST, CHANNEL_PORT)],
        },
    },
}

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('SQL_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('SQL_DATABASE', BASE_DIRECTORY / 'db.sqlite3'),
        'USER': os.environ.get('SQL_USER', 'user'),
        'PASSWORD': os.environ.get('SQL_PASSWORD', 'password'),
        'HOST': os.environ.get('SQL_HOST', 'localhost'),
        'PORT': os.environ.get('SQL_PORT', '5432'),
    }
}
"""Configuration for the default database for Django"""

# Concurrency in SQLite is not reliable, so add a timeout to any detected SQLite databases that
#   don't already have a timeout. This isn't guaranteed to work, but should provide a bare-bones mitigation
for database_configuration in DATABASES.values():
    if 'lite' in database_configuration['ENGINE']:
        if 'OPTIONS' not in database_configuration:
            database_configuration['OPTIONS'] = dict()

        if 'timeout' not in database_configuration['OPTIONS']:
            database_configuration['OPTIONS']['timeout'] = os.environ.get("SQLITE_TIMEOUT", 20)

START_DELAY = os.environ.get('EVALUATION_START_DELAY', '5')
"""The amount of seconds that an evaluation should wait before launching"""

OUTPUT_VERBOSITY = os.environ.get("EVALUATION_OUTPUT_VERBOSITY", "ALL")
"""The amount of data that should flow through an evaluation's channel for cross process communication"""
