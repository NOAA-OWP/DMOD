from itertools import chain

def flatten(d):
    return chain.from_iterable([(k,v)] if not isinstance(v,dict) else flatten(v)
                               for k,v in d.items())

def find(key, value):
    """Finf value for given key in nested dictionary list of json format"""
    for k, v in (value.items() if isinstance(value, dict) else
                 enumerate(value) if isinstance(value, list) else []):
        if k == key:
            yield v
        elif isinstance(v, (dict, list)):
            for result in find(key, v):
                yield result
