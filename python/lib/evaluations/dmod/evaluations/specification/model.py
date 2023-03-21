import os
import typing
import abc
import json
import inspect
import logging
import collections
import math

from datetime import datetime
from datetime import date
from datetime import time

import pandas
import numpy
import pytz

from dateutil.parser import parse as parse_date

import dmod.metrics as metrics
import dmod.metrics.metric as metric_functions

import dmod.core.common as common

from .. import util
from .template import TemplateManager
from .template import TemplateDetails
from .base import Specification
from .base import TemplatedSpecification

logging.basicConfig(
    filename='evaluation.log',
    level=logging.getLevelName(os.environ.get('METRIC_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "DEBUG"))),
    format=os.environ.get("LOG_FORMAT", "%(asctime)s,%(msecs)d %(levelname)s: %(message)s"),
    datefmt=os.environ.get("LOG_DATEFMT", "%H:%M:%S")
)
