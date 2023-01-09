"""
Lays out details describing how a request may be created and the different types of requests

@author: Chris Tubbs
"""

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, DataRequirement, TimeRange
from .message import AbstractInitRequest, MessageEventType, Response, InitRequestResponseReason
from abc import ABC, abstractmethod
from numbers import Number
from typing import Dict, List, Optional, Set, Union

class NGENRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NGENRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': True,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {
                'job_id': 1
            }
        }
    }

    Or:
    {
        'job_id': 0,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    response_to_type = NGENRequest
