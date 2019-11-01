#!/usr/bin/env python3

import jsonschema
from jsonschema.exceptions import best_match
import json
import os


class JsonRequestValidator:

    def __init__(self, schemas_dir=None):
        if schemas_dir is None:
            self.base_schemas_dir = os.path.dirname(os.path.abspath(__file__)) + '/schemas'
        else:
            self.base_schemas_dir = schemas_dir
        resolve_path = self.base_schemas_dir + '/'
        self.schema = None
        self.resolver = None
        with open(os.path.abspath(self.base_schemas_dir + '/request.schema.json')) as schema_file:
            self.schema = json.loads(schema_file.read())
            self.resolver = jsonschema.RefResolver("file://{}/".format(resolve_path), referrer=self.schema)

    def validate_request(self, request):
        """
        Validate the given request.

        :param request:
        :return: A tuple with whether the request is valid and either the error for invalid requests or None
        """
        results = jsonschema.Draft7Validator(self.schema, resolver=self.resolver).iter_errors(request)
        error = best_match(results)
        return (error is None), error


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
