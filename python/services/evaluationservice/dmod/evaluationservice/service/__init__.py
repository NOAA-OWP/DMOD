"""
The core of the DMOD Evaluation Service
"""
from .service_logging import debug
from .service_logging import info
from .service_logging import error
from .service_logging import warn
from .service_logging import ConfiguredLogger

from .application_values import APPLICATION_NAME
from .application_values import COMMON_DATETIME_FORMAT
from .application_values import EVALUATION_QUEUE_NAME

from .application_values import REDIS_HOST
from .application_values import REDIS_PORT
from .application_values import REDIS_USERNAME
from .application_values import REDIS_PASSWORD
from .application_values import REDIS_DB

from .application_values import RUNNER_HOST
from .application_values import RUNNER_PORT
from .application_values import RUNNER_USERNAME
from .application_values import RUNNER_PASSWORD
from .application_values import RUNNER_DB

from .application_values import CHANNEL_HOST
from .application_values import CHANNEL_PORT
from .application_values import CHANNEL_USERNAME
from .application_values import CHANNEL_PASSWORD
from .application_values import CHANNEL_DB

from .application_values import CHANNEL_NAME_PATTERN
