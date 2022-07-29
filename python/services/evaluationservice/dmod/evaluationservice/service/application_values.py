import os
import typing
import re
import subprocess
import pytz

from pathlib import Path
from datetime import datetime
from datetime import timedelta

import dateutil.tz


def in_debug_mode() -> bool:
    # SECURITY WARNING: don't run with debug turned on in production!
    debug_value = os.environ.get("DEBUG", False)

    return str(debug_value).lower() in ("yes", "y", "1", 'true', 'on', 'debug')


def get_redis_password() -> typing.Optional[str]:
    password_filename = os.environ.get("REDIS_PASSWORD_FILE", "/run/secrets/myredis_pass")

    if os.path.exists(password_filename):
        try:
            with open(password_filename, 'r') as redis_password_file:
                content = redis_password_file.read().rstrip()
                if len(content) >= 1:
                    return content
        except:
            pass

    # Fall back to env if no secrets file, further falling back to default if no env value
    return os.environ.get('REDIS_PASS')


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

BASE_DIRECTORY = Path(__file__).resolve().parent.parent

APPLICATION_NAME = os.environ.get("APPLICATION_NAME", "Evaluation Service")

COMMON_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"
CURRENT_TIMEZONE = get_full_localtimezone()

EVALUATION_QUEUE_NAME = os.environ.get("EVALUATION_QUEUE_NAME", "evaluation_jobs")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT")) if "REDIS_PORT" in os.environ else 6379
REDIS_PASSWORD = get_redis_password()

RQ_HOST = os.environ.get("RQ_HOST", REDIS_HOST)
RQ_PORT = int(os.environ.get("RQ_PORT")) if "RQ_PORT" in os.environ else REDIS_PORT

CHANNEL_HOST = os.environ.get("CHANNEL_HOST", REDIS_HOST)
CHANNEL_PORT = int(os.environ.get("CHANNEL_PORT")) if "CHANNEL_PORT" in os.environ else REDIS_PORT
CHANNEL_NAME_PATTERN = r'[\w\-_\.]+'

RQ_QUEUES = {
    'default': {
        'HOST': RQ_HOST,
        'PORT': RQ_PORT,
        'PASSWORD': os.environ.get("RQ_PASSWORD", None),
        'DB': 0,
        'DEFAULT_TIMEOUT': 99999,
    },
    EVALUATION_QUEUE_NAME: {
        'HOST': RQ_HOST,
        "PORT": RQ_PORT,
        "PASSWORD": os.environ.get("RQ_PASSWORD"),
        "DB": 0,
        "DEFAULT_TIMEOUT": 99999
    }
}

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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIRECTORY / 'db.sqlite3',
    }
}
