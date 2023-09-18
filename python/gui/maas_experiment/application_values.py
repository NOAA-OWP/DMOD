import json
import os
import typing
import re
import pytz
import logging

from pathlib import Path
from datetime import datetime
from datetime import timedelta


def in_debug_mode() -> bool:
    """
    Check to see if the server should be running in debug mode rather than a production environment.

    It is ok to show additional diagnositic information in debug mode, but not production.

    SECURITY WARNING: do not run with debug turned on in production! Diagnostic messages can be used to view
    system environment variables and stack traces.

    Uses the optional `DEBUG` environment variable

    Returns:
        Whether the server should run in debug mode
    """
    # Check to see if the global DEBUG value is True
    debug_value = os.environ.get("DEBUG", False)

    # The global DEBUG value is the law of the land; if it says it's in debug mode, it's in debug mode
    return str(debug_value).lower() in ("yes", "y", "1", 'true', 'on', 'debug')


def get_redis_password() -> typing.Optional[str]:
    """
    Attempts to find a password to the core redis instance, first by checking for a secrets file, then by checking
    an environment variable.

    The optional environment variables that control this are `REDIS_PASSWORD_FILE` for the secret or `REDIS_PASS`
    for the password on its own.

    Returns:
        The optional password to the core redis service
    """
    password_filename = os.environ.get("REDIS_PASSWORD_FILE", "/run/secrets/myredis_pass")

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
    return os.environ.get('REDIS_PASS')


def get_channel_password() -> typing.Optional[str]:
    """
    Attempts to find a password to the core redis instance, first by checking for a secrets file, then by checking
    an environment variable.

    The optional environment variables that control this are `REDIS_PASSWORD_FILE` for the secret or `REDIS_PASS`
    for the password on its own.

    Returns:
        The optional password to the core redis service
    """
    password_filename = os.environ.get("CHANNEL_PASSWORD_FILE", "/run/secrets/channel_password")

    # If a password file has been identified, try to get a password from that
    if os.path.exists(password_filename):
        try:
            with open(password_filename, 'r') as channel_password_file:
                content = channel_password_file.read().strip()
                # Only go with the password from the file if there WAS a password in the file
                if len(content) >= 1:
                    return content
        except:
            # Data couldn't be read? Move on to attempting to read it from the environment variable
            pass

    # Fall back to env if no secrets file, further falling back to default if no env value
    return os.environ.get('CHANNEL_PASSWORD', REDIS_PASSWORD)


def get_full_localtimezone():
    """
    Finds the full local timezone name.

    Instead of 'CDT' or 'CST', this will be something like 'America/Chicago'

    Returns:
        The name of the system's timezone
    """
    configured_timezone = os.environ.get("MAAS_TIMEZONE")

    if configured_timezone is not None:
        matching_timezones = [
            tz for tz in pytz.all_timezones
            if tz.upper() == configured_timezone.upper()
        ]
        if matching_timezones:
            return matching_timezones[0]

    test_date = datetime.now()

    # It's easy to tell if the system is in UTC; if there isn't an offset, it's UTC, and therefore a format easy to
    # rely on
    if test_date.astimezone().utcoffset() == timedelta(seconds=0):
        return "UTC"

    # If this is a system with 'zoneinfo' set up as part of the environment, parse the name from the linked zone
    zone_path = Path("/etc/localtime")
    zone_path = str(zone_path.readlink()) if zone_path.exists() and zone_path.is_symlink() else ""

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

STATIC_RESOURCE_DIRECTORY = BASE_DIRECTORY / "static" / "resources"

APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "Model as a Service")
"""The name of the service"""

APPLICATION_PREFIX = os.environ.get("APPLICATION_PREFIX", "DMOD")
"""The prefix used to separate shared variables used by this application from others"""

KEY_SEPARATOR = os.environ.get("KEY_SEPARATOR", "--")
"""The separator used to delimit elements of generated keys"""

COMMON_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"
"""The default format for datetime strings"""

CURRENT_TIMEZONE = get_full_localtimezone()
"""The timezone for the service"""

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
"""The host of the core redis service"""

REDIS_PORT = int(os.environ.get("REDIS_PORT")) if "REDIS_PORT" in os.environ else 6379
"""The port of the core redis service"""

REDIS_USERNAME = os.environ.get("REDIS_USERNAME", None)
"""The name of the user to use when connecting to the core redis database"""

REDIS_PASSWORD = get_redis_password()
"""The password to the cored redis service"""

REDIS_DB = os.environ.get("REDIS_DB", "0")
"""The identifier for the redis database to use on the redis host"""

NOTIFICATION_CHANNEL = os.environ.get("NOTIFICATION_CHANNEL", "notifications")

CHANNEL_HOST = os.environ.get("CHANNEL_HOST", REDIS_HOST)
"""The host of the redis service used for communicating job information"""

CHANNEL_PORT = int(os.environ.get("CHANNEL_PORT")) if "CHANNEL_PORT" in os.environ else REDIS_PORT
"""The port of the redis service used for communicating job information"""

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", REDIS_USERNAME)
"""The username used to connect to the redis database used for channels"""

CHANNEL_PASSWORD = get_channel_password()
"""The password used to connect to a redis service that is used to communicate messages"""

CHANNEL_DB = os.environ.get("CHANNEL_DB", REDIS_DB)
"""The identifier for the redis database to use on the redis channels host"""

CHANNEL_NAME_PATTERN = r'[\w\-_\.]+'
"""The pattern that redis channel names may follow"""

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(CHANNEL_HOST, CHANNEL_PORT)],
            "prefix": APPLICATION_PREFIX
        },
    },
}

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('SQL_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('SQL_DATABASE', os.path.join(BASE_DIRECTORY, 'db.sqlite3')),
        'USER': os.environ.get('SQL_USER', 'user'),
        'PASSWORD': os.environ.get('SQL_PASSWORD', 'password'),
        'HOST': os.environ.get('SQL_HOST', 'localhost'),
        'PORT': os.environ.get('SQL_PORT', '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}{":" + str(REDIS_PORT) if REDIS_PORT else ""}',
    }
}

SOCKET_FORWARDING_CONFIG_PATH = os.environ.get(
    "SOCKET_FORWARDING_CONFIG_PATH",
    STATIC_RESOURCE_DIRECTORY / "socket_forwarding.json"
)

REST_FORWARDING_CONFIG_PATH = os.environ.get(
    "REST_FORWARDING_CONFIG_PATH",
    STATIC_RESOURCE_DIRECTORY / "rest_forwarding.json"
)

def load_maas_endpoints() -> typing.Dict[str, typing.Dict[str, str]]:
    endpoints: typing.Dict[str, typing.Dict[str, str]] = dict()

    if 'MAAS_ENDPOINT_HOST' in os.environ:
        endpoints['default'] = {
            "host": "wss://" + os.environ.get("MAAS_ENDPOINT_HOST"),
            "port": os.environ.get("MAAS_ENDPOINT_PORT")
        }

    is_key_pattern = re.compile("^maas_endpoint__.+__host$")
    host_key_pattern = re.compile(r"(?<=maas_endpoint__).+(?=__host)")
    has_non_socket_pattern = re.compile(r"^(?!wss).+://.+")
    protocol_pattern = re.compile(r"^.+(?=://)")

    endpoint_hosts = [
        {
            "key": host_key_pattern.search(key.lower()).group(),
            "host": os.environ.get("MAAS_ENDPOINT_HOST")
        }
        for key in os.environ.keys()
        if is_key_pattern.search(key.lower())
    ]

    for host_config in endpoint_hosts:
        port_key = f"maas_endpoint__{host_config['key']}__port"
        possible_keys = [
            key
            for key in os.environ.keys()
            if key.lower() == port_key
        ]

        if len(possible_keys) > 0:
            port_key = possible_keys[0]
        else:
            logging.warning("No port was given for the '{}' MaaS endpoint; skipping it.".format(host_config['key']))
            continue

        if has_non_socket_pattern.search(host_config["host"]):
            protocol = protocol_pattern.search(host_config["host"]).group()
            logging.warning(
                f"The protocol for the host URI for {host_config['key']} must be "
                f"'wss' for web sockets, not {protocol}; skipping"
            )
            continue

        if not host_config["host"].startswith("wss://"):
            host_config["host"] = "wss://" + host_config["host"]

        host_config['port'] = port_key

        endpoints[host_config["key"]] = host_config

    return endpoints


# Must be all caps to be accessible
def GET_MAAS_ENDPOINT(host_type: str) -> str:
    config = MAAS_ENDPOINTS.get(host_type, MAAS_ENDPOINTS.get("default"))
    return config["host"] + ":" + config["port"]


MAAS_ENDPOINTS = load_maas_endpoints()
