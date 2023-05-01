"""
Provides common functionality used to serializing messages
"""
import typing
import json
import os
import traceback

from datetime import datetime

import numpy

from service.application_values import COMMON_DATETIME_FORMAT

from .common import string_might_be_json


TYPE_TO_SERIALIZE = typing.Union[typing.Mapping, str, bytes, datetime, typing.Iterable]
SERIALIZABLE_TYPE = typing.Union[typing.Mapping, str, bytes, datetime, typing.Iterable]


class __MessageSerializer:
    def make_message_serializable(self, message: TYPE_TO_SERIALIZE) -> SERIALIZABLE_TYPE:
        if isinstance(message, typing.Mapping):
            replacement_map = dict()

            for key, value in message.items():
                replacement_map[key] = self.make_message_serializable(value)

            message = replacement_map
        elif isinstance(message, bytes):
            return message.decode()
        elif isinstance(message, float):
            if numpy.isneginf(message):
                return "-Infinity"
            if numpy.isposinf(message):
                return "Infinity"
            if numpy.isnan(message):
                return "NaN"
        elif isinstance(message, datetime):
            return message.strftime(COMMON_DATETIME_FORMAT)
        elif isinstance(message, Exception):
            return os.linesep.join(traceback.format_exception_only(type(message), message))
        elif not isinstance(message, str) and isinstance(message, typing.Iterable):
            return [self.make_message_serializable(submessage) for submessage in message]
        elif string_might_be_json(message):
            try:
                possible_json = json.loads(message)
                return self.make_message_serializable(possible_json)
            except:
                pass

        return message


MessageSerializer = __MessageSerializer()
make_message_serializable = MessageSerializer.make_message_serializable