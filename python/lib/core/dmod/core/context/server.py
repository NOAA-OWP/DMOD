"""
Defines a custom implementation for a multiprocessing context Server

Overcomes issues present in the current version of Python (v3.8) and provides extra functionality, such as
advanced handling for properties
"""
from __future__ import annotations

import typing
import threading
import sys

from multiprocessing import managers
from multiprocessing import util

from traceback import format_exc

from ..decorators import version_range

from .base import is_property


@version_range(
    maximum_version="3.12.99",
    message="Python Versions 3.12 and below have an issue where raw values cannot be returned by a Server if the "
            "named value wasn't a function. Check if this is still an issue now that a more recent version is used."
)
class DMODObjectServer(managers.Server):
    """
    A multiprocessing object server that may serve non-callable values
    """
    def serve_client(self, conn):
        """
        Handle requests from the proxies in a particular process/thread

        This differs from the default Server implementation in that it allows access to exposed non-callables
        """
        util.debug('starting server thread to service %r', threading.current_thread().name)

        recv = conn.recv
        send = conn.send
        id_to_obj = self.id_to_obj

        while not self.stop_event.is_set():
            member_name: typing.Optional[str] = None
            object_identifier: typing.Optional[str] = None
            served_object = None
            args: tuple = tuple()
            kwargs: typing.Mapping = {}

            try:
                request = recv()
                object_identifier, member_name, args, kwargs = request
                try:
                    served_object, exposed_member_names, gettypeid = id_to_obj[object_identifier]
                except KeyError as ke:
                    try:
                        served_object, exposed_member_names, gettypeid = self.id_to_local_proxy_obj[object_identifier]
                    except KeyError as inner_keyerror:
                        raise inner_keyerror from ke

                if member_name not in exposed_member_names:
                    raise AttributeError(
                        f'Member {member_name} of {type(served_object)} object is not in exposed={exposed_member_names}'
                    )

                if not hasattr(served_object, member_name):
                    raise AttributeError(
                        f"{served_object.__class__.__name__} objects do not have a member named '{member_name}'"
                    )

                if is_property(served_object, member_name):
                    served_class_property: property = getattr(served_object.__class__, member_name)
                    if len(args) == 0:
                        value_or_function = served_class_property.fget
                        args = (served_object,)
                    else:
                        value_or_function = served_class_property.fset
                        args = (served_object,) + args
                else:
                    value_or_function = getattr(served_object, member_name)

                try:
                    if isinstance(value_or_function, typing.Callable):
                        result = value_or_function(*args, **kwargs)
                    else:
                        result = value_or_function
                except Exception as e:
                    msg = ('#ERROR', e)
                else:
                    typeid = gettypeid and gettypeid.get(member_name, None)
                    if typeid:
                        rident, rexposed = self.create(conn, typeid, result)
                        token = managers.Token(typeid, self.address, rident)
                        msg = ('#PROXY', (rexposed, token))
                    else:
                        msg = ('#RETURN', result)

            except AttributeError:
                if member_name is None:
                    msg = ('#TRACEBACK', format_exc())
                else:
                    try:
                        fallback_func = self.fallback_mapping[member_name]
                        result = fallback_func(self, conn, object_identifier, served_object, *args, **kwargs)
                        msg = ('#RETURN', result)
                    except Exception:
                        msg = ('#TRACEBACK', format_exc())

            except EOFError:
                util.debug('got EOF -- exiting thread serving %r', threading.current_thread().name)
                sys.exit(0)

            except Exception:
                msg = ('#TRACEBACK', format_exc())

            try:
                try:
                    send(msg)
                except Exception:
                    send(('#UNSERIALIZABLE', format_exc()))
            except Exception as e:
                util.info('exception in thread serving %r', threading.current_thread().name)
                util.info(' ... message was %r', msg)
                util.info(' ... exception was %r', e)
                conn.close()
                sys.exit(1)

