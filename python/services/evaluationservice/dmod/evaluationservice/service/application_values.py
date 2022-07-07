import os
import typing
from pathlib import Path


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


DEBUG = in_debug_mode()

BASE_DIRECTORY = Path(__file__).resolve().parent.parent

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

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIRECTORY / 'db.sqlite3',
    }
}
