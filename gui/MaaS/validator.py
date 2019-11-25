#!/usr/bin/env python3

from .request_type import RequestType
from abc import ABC
import json
import jsonschema
from jsonschema.exceptions import best_match
from pathlib import Path
from typing import Any, Optional, Tuple


class JsonRequestValidator(ABC):

    def __init__(self, base_schema_filename, request_type: RequestType, schemas_dir=None):
        if schemas_dir is None:
            script_dir = Path(__file__).resolve().parent
            self.base_schemas_dir = script_dir.parent.joinpath('schemas')
        else:
            self.base_schemas_dir = schemas_dir
        resolve_path = str(self.base_schemas_dir) + '/'
        self.schema = None
        self.resolver = None
        self._request_type: RequestType = request_type
        with self.base_schemas_dir.joinpath(base_schema_filename).open(mode='r') as schema_file:
            self.schema = json.loads(schema_file.read())
            self.resolver = jsonschema.RefResolver("file://{}/".format(resolve_path), referrer=self.schema)

    def validate_request(self, request: dict) -> Tuple[bool, Optional[Any]]:
        """
        Validate the given request.

        :param request:
        :return: A tuple with whether the request is valid and either the error for invalid requests or None
        """
        results = jsonschema.Draft7Validator(self.schema, resolver=self.resolver).iter_errors(request)
        error = best_match(results)
        return (error is None), error

    @property
    def request_type(self) -> RequestType:
        return self._request_type


class JsonJobRequestValidator(JsonRequestValidator):
    def __init__(self, schemas_dir=None):
        super().__init__(schemas_dir=schemas_dir, request_type=RequestType.JOB,
                         base_schema_filename='request.schema.json')


class JsonAuthRequestValidator(JsonRequestValidator):
    def __init__(self, schemas_dir=None):
        super().__init__(schemas_dir=schemas_dir, request_type=RequestType.AUTHENTICATION,
                         base_schema_filename='nwm.maas.auth.schema.json')


def traverse_suberrors(error, level=''):
    """Recursiverly tranverse subschema errors

    """
    print("{} {} {}".format(level, error.schema_path, error.message))
    level=level+'    '
    for suberror in error.context:
        print('{}{}'.format(level, list(suberror.schema_path)))
        print('{}{}'.format(level, suberror.message ))
        print("---------------------------------------")
        traverse_suberrors(suberror, level)


def traverse_error_tree(error_tree):
    """Recursively traverse and report errors in error tree.  Includes suberrors.

    """
    print(error_tree.errors)
    for validator, error in error_tree.errors.items():
        #print(error)
        traverse_suberrors(error)
    for error in error_tree:
        print("ERROR: {}".format(error))
        traverse_error_tree( error_tree[error] )
        print("++++++++++++++++++++++++++++++++++")
        #for validator, error in error_tree[error].errors.items():
        #     #print(error)
        #     traverse_suberrors(error)
        #    print(list(suberror.schema_path), suberror.message, sep=", ")
        #    #traverse_errors(suberror)
        #traverse_errors(error_tree)
        print("++++++++++++++++++++++++++++++++++")


def validate_request(request):
    """
    Validate model request against defined model schema
    """
    #TODO handle type of request
    validator = JsonRequestValidator()
    is_valid, error = validator.validate_request(request=request)
    if error is not None:
        raise error
    else:
        print("Valid")


if __name__ == "__main__":
    with open("./schemas/request.json", 'r') as data_file:
        test_data = json.load( data_file )
    print("Validating")
    validate_request( test_data )
    with open("./schemas/request_bad.json") as data_file:
        test_data = json.load( data_file )
    print("Validating")
    validate_request( test_data )
