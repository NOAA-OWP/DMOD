# About
Python package for core DMOD types, both concrete and abstract, that are depended upon by other DMOD Python packages and themselves have no dependencies outside of Python and its standard library.

Classes belong here if placing them in a more specialized package would cause undesired consequences, such as circular dependencies or transitive dependency on otherwise unnecessary packages.

## `common`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common` package

### `collection`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.collection` module

### `failure`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.failure` module

### `helper_functions`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.helper_functions` module

### `protocols`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.protocols` module

### `reader`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.reader` module

### `tasks`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.tasks` module

### `types`

<b style="color: red">TODO:</b> Write information about the `dmod.core.common.types` module

## `decorators`

<b style="color: red">TODO:</b> Write information about the `dmod.core.decorators` package

### `decorator_constants`

<b style="color: red">TODO:</b> Write information about the `dmod.core.decorators.decorator_constants` module

### `decorator_functions`

<b style="color: red">TODO:</b> Write information about the `dmod.core.decorators.decorator_functions` module

### `message_handlers`

<b style="color: red">TODO:</b> Write information about the `dmod.core.decorators.message_handlers` module

## `context`

The `dmod.core.context` module provides the functionality needed to create automatic proxies for remote objects,
provide a DMOD specific multiprocessed object manager, and a custom implementation of the object manager's server to
overcome issues with the base functionality as of python 3.8. If
`dmod.core.context.DMODObjectManager.register_class(NewClass)` is called after its definition, a proxy for it will be
defined dynamically and a proxy for that type (`NewClass` in this example) may be constructed through code such as:

```python
from dmod.core import context

with context.get_object_manager() as manager:
    class_instance = manager.create_object('NewClass', 'one', 2, other_parameter=9)
```

where <code style="color: green">'NewClass'</code> is the name of the desired class and
<code style="color: green">'one'</code>, <code style="color: blue">2</code>, and <code>other_parameter</code>
are the parameters for `NewClass`'s constructor.

Scopes for the manager may be created to track objects that are passed from one process to another. If a
proxy is instantiated within a called function, passed to a new process, and the function returns, the
`decref` function on the server will be called before the `incref` function is called and lead to the
destruction of the object before it may be used. Creating the object through a scope may keep the object
alive and assigning the process to it will allow the object manager to destroy its objects when the process
completes.

For example:

```python
from dmod.core import context
from concurrent import futures

def do_something(new_class: NewClass):
    ...

def start_process(manager: context.DMODObjectManager, pool: futures.ProcessPoolExecutor):
    scope = manager.establish_scope("example")
    example_object = scope.create_object('NewClass', 'one', 2, other_parameter=9)
    task = pool.submit(do_something, example_object)

    # The scope and everything with it will be deleted when `task.done()`
    manager.monitor_operation(scope, task)

# Tell the object manager to monitor scopes when creating it
with futures.ProcessPoolExecutor() as pool, context.get_object_manager(monitor_scope=True) as manager:
    start_process(manager, pool)
```

### <span style="color: red">Common Errors</span>

#### Remote Error in `Server.incref`

Sometimes you might encounter an error that reads like:

```shell
Traceback (most recent call last):
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/pool.py", line 114, in worker
    task = get()

  File "/path/to/python/3.8/lib/python3.8/multiprocessing/queues.py", line 358, in get
    return _ForkingPickler.loads(res)
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 959, in RebuildProxy
    return func(token, serializer, incref=incref, **kwds)
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 809, in __init__
    self._incref()
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 864, in _incref
    dispatch(conn, None, 'incref', (self._id,))
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 91, in dispatch
    raise convert_to_error(kind, result)
multiprocessing.managers.RemoteError:
---------------------------------------------------------------------------
Traceback (most recent call last):
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 210, in handle_request
    result = func(c, *args, **kwds)
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 456, in incref
    raise ke
  File "/path/to/python/3.8/lib/python3.8/multiprocessing/managers.py", line 443, in incref
    self.id_to_refcount[ident] += 1
KeyError: '3067171c0'
```

This sort of error occurs when an instantiated object has fallen out of scope _before_ another process has had
a chance to use it. The Server (in this case the `dmod.core.context.DMODObjectServer`) that the manager (in this case
the `dmod.core.context.DMODObjectManager`) keeps track of objects via reference counters. When a proxy is created, the
real object is created on the instantiated server and its reference count increases. When the created proxy leaves
scope, that reference count decreases. When that number reaches 0, the real object that the proxy refers to is
removed. If a proxy is created in the scope of one function and passed to another process, the reference count will
be decremented when that function exits unless the proxy is created within a scope that does not end when the
function does.

## `dataset`

<b style="color: red">TODO:</b> Write information about the `dmod.core.dataset` module

## `enum`

<b style="color: red">TODO:</b> Write information about the `dmod.core.enum` module

## `exception`

<b style="color: red">TODO:</b> Write information about the `dmod.core.exception` module

## `execution`

<b style="color: red">TODO:</b> Write information about the `dmod.core.execution` module

## `meta_data`

<b style="color: red">TODO:</b> Write information about the `dmod.core.meta_data` module

## `serializable`

<b style="color: red">TODO:</b> Write information about the `dmod.core.serializable` module
