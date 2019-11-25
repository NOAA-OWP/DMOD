from enum import Enum


class RequestType(Enum):
    AUTHENTICATION = 1,
    JOB = 2,
    INVALID = -1