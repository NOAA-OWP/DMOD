#!/usr/bin/env python3

import jsonschema
from jsonschema.exceptions import best_match
import json
import os

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
    """Validate model request against defined model schema

    """
    #TODO handle type of request
    base_schemas_dir = os.path.dirname(os.path.abspath(__file__)) + '/schemas'
    with open(os.path.abspath(base_schemas_dir + '/request.schema.json')) as schema_file:
        schema = json.loads(schema_file.read())
        resolve_path = base_schemas_dir + '/'
        #os._exit(1)
        #os._exit(1)
        """
        store={}
        with open(os.path.join(resolve_path, 'request.schema.json')) as subschema:
            store['nwm.model.parameter.schema.json'] = jsonref.loads(subschema.read(), jsonschema=True)

        with open(os.path.join(resolve_path, 'nwm.schema.json')) as subschema:
            store['nwm.schema.json'] = jsonref.loads(subschema.read(), jsonschema=True)

        with open(os.path.join(resolve_path, 'xyz.schema.json')) as subschema:
            store['xyz.schema.json'] = jsonref.loads(subschema.read(), jsonschema=True)

        with open(os.path.join(resolve_path, 'nwm.model.parameter.schema.json')) as subschema:
            store['nwm.model.parameter.schema.json'] = jsonref.loads(subschema.read(), jsonschema=True)
        resolver = jsonschema.RefResolver(base_uri="", referrer=None, cache_remote=False, store=store)
        """
        resolver = jsonschema.RefResolver("file://{}/".format(resolve_path), referrer=schema)
        #result = jsonschema.validate(test_data, schema)

        results = jsonschema.Draft7Validator(schema, resolver=resolver).iter_errors(request)


        #print(list(results))
        #for r in results:
        #    print(r.context)
        #error_tree
        #results = jsonschema.exceptions.ErrorTree(results)
        #print( error_tree['properties'].errors )#['model']['oneOf'].errors )
        #if results.total_errors > 0:
        #    print("{} errors found".format(results.total_errors))
        #    traverse_error_tree(results)
        #else:
        #    print("No Errors")
        error = best_match(results)
        if error is not None:
            raise(error)
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
