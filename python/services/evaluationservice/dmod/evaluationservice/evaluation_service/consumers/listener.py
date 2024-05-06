#!/usr/bin/env python3
import inspect
import logging
import os
import typing
import json

from urllib.parse import parse_qs

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.models import User
from asgiref.sync import async_to_sync

import redis
import redis.client as redis_client

from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import QuerySet

from dmod.evaluations.specification import EvaluationSpecification

import utilities
from utilities.django import make_message_serializable

from evaluation_service.models import EvaluationDefinition
from evaluation_service.models import EvaluationDefinitionCommunicator

from service.application_values import COMMON_DATETIME_FORMAT
from service.application_values import START_DELAY
from service.application_values import OUTPUT_VERBOSITY
from service.application_values import EVALUATION_QUEUE_NAME

from service import logging as common_logging
from evaluation_service import models

from evaluation_service.specification import SpecificationTemplateManager

from .action import ActionDescriber
from .action import REQUIRED_PARAMETER_TYPES
from .action import required_parameters


LOGGER = common_logging.get_logger()
SOCKET_LOGGER = common_logging.get_logger(common_logging.DEFAULT_SOCKET_LOGGER_NAME)

REQUEST_ID_KEY = "request_id"


def inner_data_is_wrapper(possible_wrapper: dict) -> bool:
    """
    Determines whether the passed dictionary is just a wrapper for a dictionary named 'data'

    Args:
        possible_wrapper: A possible dictionary that just contains another dictionary named 'data'

    Returns:
        Whether the passed dictionary is just a wrapper for a dictionary named 'data'
    """
    return possible_wrapper is not None \
           and isinstance(possible_wrapper, dict) \
           and 'data' in possible_wrapper \
           and isinstance(possible_wrapper['data'], dict) \
           and len(possible_wrapper['data']) == 1 \
           and 'data' in possible_wrapper['data']


def make_message(
    event: str = None,
    response_type: str = None,
    data: typing.Union[str, dict] = None,
    request_id: str = None,
    logger: common_logging.ConfiguredLogger = None
) -> dict:
    """
    creates a message to communicate to either a socket or channel

    Args:
        event: Why the message was sent
        response_type: What type of response this is
        data: The data to send
        request_id: The optional ID of a request to associate with a response
        logger: A logger used to store diagnositic and error data if needed

    Returns:
        A message with useful data to communicate
    """
    if logger is None:
        logger = LOGGER
    elif isinstance(logger, str):
        logger = common_logging.get_logger(logger)

    # Not much can be done with bytes, so go ahead and convert data to a string
    if data and isinstance(data, bytes):
        data = data.decode()

    # If the data might be a json string, try to parse it. If it doesn't parse, we'll just consider it as the
    # basic payload to be communicated. An exception here is ok.
    if utilities.string_might_be_json(data):
        try:
            data = json.loads(data)
        except Exception as load_exception:
            logger.error(
                f"[{inspect.currentframe().f_code.co_name}] The passed data was a non-json string; "
                f"it can't be converted to JSON for further decomposition for a websocket response",
                load_exception
            )

    message_time = utilities.now().strftime(COMMON_DATETIME_FORMAT)

    # If the data is a dict, its contents can be rearranged to properly fit the message format to be sent
    # (such as event data floating to the top instead of being buried below)
    if isinstance(data, dict):
        use_inner_data = False

        # Make sure the contained data can actually be communicated
        data = make_message_serializable(data)

        # If this dictionary has a 'data' member that ALSO has a 'data' member, promote the first data member and tell
        # the logic to use the newly promoted inner-inner 'data' member for investigation
        if 'data' in data and 'data' in data['data']:
            if utilities.string_might_be_json(data['data']):
                try:
                    contained_data = json.loads(data.pop('data'))
                except Exception as loads_exception:
                    logger.error(f"'{str(data)}' didn't parse into a dict so we're using it raw", loads_exception)
                    contained_data = data.pop('data')
            else:
                contained_data = data.pop('data')

            use_inner_data = True
        else:
            contained_data = data

        # Check to see if 'event' has been defined within the passed data or the inner data
        if 'event' in contained_data and contained_data['event']:
            event = contained_data.pop('event')
        elif 'event' in data and data['event']:
            event = data.pop('event')

        # Check to see if 'type' has been defined within the passed data or the inner data
        if 'type' in contained_data and contained_data['type']:
            response_type = contained_data.pop('type')
        elif 'type' in data and data['type']:
            response_type = data.pop('type')

        # Check to see if 'response_type' has been defined within the passed data or inner data
        if 'response_type' in contained_data and contained_data['response_type']:
            response_type = contained_data.pop('response_type')
        elif 'response_type' in data and data['response_type']:
            response_type = data.pop('response_type')

        # Check to see if 'time' has been defined within the passed data or inner data
        if 'time' in contained_data and contained_data['time']:
            message_time = contained_data.pop('time')
        elif 'time' in data and data['time']:
            message_time = data.pop('time')

        # Now that important values have been pulled out of the top level 'data' dictionary,
        # promote the inner level if its used
        data = contained_data['data'] if use_inner_data else contained_data

        # Try to convert data to json one last time
        if utilities.string_might_be_json(data):
            try:
                data = json.loads(data)
            except Exception as loads_exception:
                logger.error("Could not deserialize data", loads_exception)
    elif isinstance(data, str):
        data = {
            "message": data
        }

    # Event can't be null, so set it to something
    if event is None:
        event = "send_message"

    # If no response type was given, go ahead and set it to something
    if not response_type:
        response_type = "send_message"

    if isinstance(data, dict):
        # While the data dictionary just looks like `{"data": {"data": {...}}}`, bring the actual data up a level
        while isinstance(data.get("data"), dict) and len(data) == 1:
            data = data.get('data')

        # Again, promote inner 'data' instances if it just looks like the inner value is just another dict named 'data'
        # Will convert:
        #    data = {"val1": 1, "val2": 2, "data": {"data": [1, 2, 3]}}
        # To
        #    data = {"val1": 1, "val2": 2, "data": [1, 2, 3]}
        # The following will not be changed:
        #    data = {"val1": 1, "val2": 2, "data": {"data": [1, 2, 3], "other_data": 8}}
        while inner_data_is_wrapper(data.get('data')):
            data['data'] = data.get('data').get('data')

    # Create a basic response detailing what event caused the message to be sent, the general gist of the message,
    # when it was sent, and data as a basic payload to be communicated
    message = {
        "event": event,
        "type": response_type,
        'time': message_time,
        "data": data,
        'request_id': request_id
    }

    # Make sure that only data that may be transmitted is within the message (i.e. nothing like binary data)
    message = make_message_serializable(message)

    return message


def make_websocket_message(
    event: str = None,
    response_type: str = None,
    data: typing.Union[str, dict] = None,
    logger: [logging.Logger, str, common_logging.ConfiguredLogger] = None,
    request_id: str = None
) -> str:
    """
    Formats response data into a form that is easy for the other end of the socket to digest

    Args:
        event: Why the message was sent
        response_type: What type of response this is
        data: The data to send
        logger: A logger used to store diagnostic and error data if needed
        request_id: An optional ID used to link an async request to its async response

    Returns:
        A JSON string containing the data to be sent along the socket
    """
    return json.dumps(
        make_message(
            event=event,
            response_type=response_type,
            data=data,
            request_id=request_id,
            logger=logger
        ), indent=4
    )


class ConcreteScope:
    """
    A typed object with clear attributes for everything expected in a 'scope' dictionary for websockets
    """
    def __init__(self, scope: dict):
        self.__scope = scope
        self.__type: str = scope.get("type")
        self.__path: str = scope.get("path")
        self.__raw_path: bytes = scope.get("raw_path")
        self.__headers: typing.Dict[str, str] = dict()

        for header_name, header_value in scope.get("headers"):  # type: bytes, bytes
            self.__headers[header_name.decode()] = header_value.decode()

        self.__query_arguments: typing.Dict[str, typing.List[str]] = parse_qs(scope.get("query_string", ""))
        self.__client_host: str = scope.get("client")[0] if 'client' in scope and len('scope') > 0 else None
        self.__client_port: str = scope.get("client")[-1] if 'client' in scope and len('scope') > 1 else None
        self.__server_host: str = scope.get("server")[0] if 'server' in scope and len('scope') > 0 else None
        self.__server_port: str = scope.get("server")[-1] if 'server' in scope and len('scope') > 1 else None
        self.__asgi: typing.Dict[str, str] = scope.get("asgi", dict())
        self.__cookies: typing.Dict[str, str] = scope.get("cookies", dict())
        self.__session: typing.Optional[SessionStore] = scope.get("session")
        self.__user: typing.Optional[User] = scope.get("user")
        self.__path_remaining: str = scope.get("path_remaining")

        if 'url_route' in scope and 'args' in scope['url_route']:
            self.__arguments: typing.Tuple[str] = scope['url_route']['args'] or tuple()
        else:
            self.__arguments: typing.Tuple[str] = tuple()

        if 'url_route' in scope and 'kwargs' in scope['url_route']:
            self.__kwargs: typing.Dict[str, str] = scope['url_route']['kwargs'] or dict()
        else:
            self.__kwargs: typing.Dict[str, str] = dict()

    @property
    def type(self) -> typing.Optional[str]:
        """
        The type of object this scope is for
        """
        return self.__type

    @property
    def path(self) -> typing.Optional[str]:
        """
        The path on the server that brought the request here
        """
        return self.__path

    @property
    def raw_path(self) -> typing.Optional[bytes]:
        """
        The raw path on the server that brought the request here
        """
        return self.__raw_path

    @property
    def headers(self) -> typing.Dict[str, str]:
        """
        A dictionary of HTTP headers that came along with the request
        """
        return self.__headers

    @property
    def query_arguments(self) -> typing.Dict[str, typing.List[str]]:
        """
        All arguments passed via query string
        """
        return self.__query_arguments

    @property
    def client(self) -> typing.Optional[str]:
        """
        The address for the client that connected to the socket
        """
        client_address: str = ""
        if self.__client_host:
            client_address += self.__client_host

            if self.__client_port:
                client_address += f":{self.__client_port}"

        return client_address

    @property
    def client_host(self) -> typing.Optional[str]:
        """
        The host for the client that connected to the socket
        """
        return self.__client_host

    @property
    def client_port(self) -> typing.Optional[str]:
        """
        The port for the client that connected to the socket
        """
        return self.__client_port

    @property
    def server(self) -> str:
        """
        The address for the server that received the request for a socket
        """
        server_address: str = ""

        if self.__server_host:
            server_address += self.__server_host

            if self.__server_port:
                server_address += f":{self.__server_port}"

        return server_address

    @property
    def server_host(self) -> typing.Optional[str]:
        """
        The host name of the server that received the request for a socket
        """
        return self.__server_host

    @property
    def server_port(self) -> typing.Optional[str]:
        """
        The port of the server that received the request for a socket
        """
        return self.__server_port

    @property
    def asgi(self) -> typing.Dict[str, str]:
        """
        asgi settings for the gateway

        Expect something like {'version': '3.0'}
        """
        return self.__asgi

    @property
    def cookies(self) -> typing.Dict[str, str]:
        """
        All cookies passed along from the client
        """
        return self.__cookies

    @property
    def session(self) -> typing.Optional[SessionStore]:
        """
        Session data for the connected user (if there is one)
        """
        return self.__session

    @property
    def user(self) -> typing.Optional[User]:
        """
        The user (anonymous or logged in) that tried to make the connection
        """
        return self.__user

    @property
    def path_remaining(self) -> str:
        return self.__path_remaining

    @property
    def arguments(self) -> typing.Tuple[str, ...]:
        """
        Arguments passed into the URL route
        """
        return self.__arguments

    @property
    def keyword_arguments(self) -> typing.Dict[str, str]:
        """
        Keyword arguments passed into the URL route
        """
        return self.__kwargs

    def get(self, key, default) -> typing.Any:
        """
        Call the underlying scope dictionary's `get` function

        Args:
            key: The key for the value to get
            default: A value to return if the key is not present

        Returns:
            The value if the key is present, `None` otherwise
        """
        return self.__scope.get(key, default)

    def __getitem__(self, key):
        return self.__scope[key]

    def keys(self) -> typing.KeysView:
        """
        All keys for the underlying scope dictionary
        """
        return self.__scope.keys()

    def values(self) -> typing.ValuesView:
        """
        All values for the underlying scope dictionary
        """
        return self.__scope.values()

    def items(self) -> typing.ItemsView:
        """
        All items in the underlying scope dictionary, packaged into 2-tuples like (key, value).
        """
        return self.__scope.items()


class LaunchConsumer(AsyncWebsocketConsumer, ActionDescriber):
    """
    Web Socket consumer that forwards messages to and from redis PubSub
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_connection: redis.Redis = utilities.get_redis_connection()
        self.publisher_and_subscriber: typing.Optional[redis_client.PubSub] = self.redis_connection.pubsub()
        self.subscribed_to_channel = False
        self.listener: typing.Optional[redis.client.PubSubWorkerThread] = None
        self.connection_group_id: typing.Optional[str] = None
        self.channel_name: typing.Optional[str] = None
        self.template_manager: SpecificationTemplateManager = SpecificationTemplateManager()
        self.__scope: typing.Optional[ConcreteScope] = None

    @property
    def scope_data(self) -> ConcreteScope:
        """
        Returns:
            A scope object representing the consumer's internal scope dictionary
        """
        if self.__scope is None:
            self.__scope = ConcreteScope(self.scope)

        return self.__scope

    def receive_subscribed_message(self, message):
        """
        Interprets and transforms messages sent along the redis channel.

        Args:
            message: A message that was published from redis
        """
        def is_message_wrapper(possible_wrapper) -> bool:
            return isinstance(possible_wrapper, dict) \
                   and not possible_wrapper.get("event") \
                   and "data" in possible_wrapper

        # The passed message may be a wrapper if it doesn't bear an event, but DOES have a 'data' member.
        # If that's the case, use its data member instead
        while is_message_wrapper(message):
            message = message['data']

        # If it looks like the passed message might be a string or bytes representation of a dict, attempt to
        # convert it to a dict
        if isinstance(message, (str, bytes)) and utilities.string_might_be_json(message):
            try:
                deserialized_message = json.loads(message)
            except:
                # It couldn't be converted, so go ahead use the passed in value
                deserialized_message = message
        else:
            deserialized_message = message
            
        while is_message_wrapper(deserialized_message):
            # This is only considered a message wrapper if it is a dict; linters may think this could be a string,
            # but it will always be a dict here
            deserialized_message = deserialized_message['data']

        # The caller requires this function to be synchronous, whereas `send_message` is async;
        # we're stuck using async_to_sync here as a result
        async_send = async_to_sync(self.send_message)
        async_send(deserialized_message, event="subscribed_message_received")

    async def connect(self):
        """
        Handler for when a client connects to this socket.
        """
        await super().accept()
        await self.send_message(event="connect", result="Connection Accepted")

    @required_parameters(evaluation_name=REQUIRED_PARAMETER_TYPES.text)
    async def subscribe_to_channel(self, payload: typing.Dict[str, typing.Any] = None):
        """
        Subscribe to a redis channel

        Args:
            payload: The arguments sent through the socket
        """
        if not self.subscribed_to_channel:
            self.channel_name = payload['evaluation_name']
            self.connection_group_id = utilities.get_channel_key(self.channel_name)

            if not self.connection_group_id:
                raise ValueError("No channel name was passed; no channel may be subscribed to")

            self.publisher_and_subscriber = self.redis_connection.pubsub()

            self.publisher_and_subscriber.subscribe(
                **{
                    self.connection_group_id: self.receive_subscribed_message
                }
            )

            self.listener = self.publisher_and_subscriber.run_in_thread(sleep_time=0.001)

            await self.channel_layer.group_add(
                self.connection_group_id,
                self.channel_name
            )

            SOCKET_LOGGER.debug(f"[{str(self)}] {self.connection_group_id} was added to the channel layer")
            await self.send_message(
                event="connect_to_channel",
                result=f"Connected to redis channel named {self.connection_group_id}",
                request_id=payload.get("request_id")
            )
            self.subscribed_to_channel = True
        else:
            await self.send_message(
                event="connect_to_channel",
                result=f"Already connected to a redis channel named {self.connection_group_id}",
                request_id=payload.get(REQUEST_ID_KEY)
            )

    async def receive(self, text_data=None, **kwargs):
        """
        Processes messages received via the socket.

        Called when the other end of the socket sends a message

        Args:
            text_data: The data sent over the socket
            **kwargs:
        """
        if not text_data:
            message = f"{str(self)}: No data was received"
            await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
            SOCKET_LOGGER.debug(f"{str(self)}: {message}")
            return

        try:
            payload = json.loads(text_data)
        except Exception as error:
            message = f"Only JSON strings may be received and processed. Received data was {type(text_data)}"
            SOCKET_LOGGER.error(message, error)
            await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
            return

        if payload is None:
            message = f"No payload could be read from: '{text_data}'"
            SOCKET_LOGGER.error(message)
            await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
            return

        try:
            if not payload.get('action'):
                message = f"{str(self)}: No action was received; expected action cannot be performed"
                SOCKET_LOGGER.error(message)
                await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
                return

            if payload['action'] not in self.get_action_handlers():
                message = f"{str(self)}: '{payload['action']}' is an invalid function"
                SOCKET_LOGGER.debug(message)
                await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
                return

            action = payload['action']
            handler = getattr(self, action)
            action_parameters = payload.get('action_parameters')

            if hasattr(handler, "required_parameters"):
                parameters = getattr(handler, "required_parameters")  # type: dict[str, str]

                if parameters and not action_parameters:
                    message = f"{str(self)}: '{action}' cannot be performed; no 'action_parameters' object was received"
                    SOCKET_LOGGER.error(message)
                    await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
                    return

                missing_parameters = list()
                for parameter_name, parameter_type in getattr(handler, "required_parameters").items():
                    if parameter_name not in action_parameters:
                        missing_parameters.append(f"{parameter_name}: {parameter_type}")

                if missing_parameters:
                    message = f"{str(self)}: '{action}' cannot be performed; " \
                              f"the following required parameters are missing: {', '.join(missing_parameters)}"
                    SOCKET_LOGGER.error(message=message)
                    await self.send_error(event='receive', message=message, request_id=kwargs.get(REQUEST_ID_KEY))
                    return
        except Exception as exception:
            await self.send_error(message=exception, event="receive")
            SOCKET_LOGGER.error(message=exception)
            return

        try:
            result = handler(action_parameters)

            while inspect.isawaitable(result):
                result = await result
        except Exception as exception:
            await self.send_error(message=exception, event=action)
            SOCKET_LOGGER.error(message=exception)

    @required_parameters(evaluation_name=REQUIRED_PARAMETER_TYPES.text, instructions=REQUIRED_PARAMETER_TYPES.text)
    async def launch(self, payload: typing.Dict[str, typing.Any] = None):
        """
        Launch an evaluation

        Args:
            payload: Arguments passed along the socket
        """
        evaluation_name: str = payload['evaluation_name']
        try:
            # First, make sure that a channel is subscribed to
            await self.subscribe_to_channel(payload)
        except Exception as exception:
            message = f"Could not launch job; a redis channel named '{evaluation_name}' could not be connected to."
            SOCKET_LOGGER.error(
                message=f"{str(self)}: Could not launch job; the redis channel could not be connected to.",
                exception=exception
            )
            await self.send_error(event="launch", message=message, request_id=payload.get(REQUEST_ID_KEY))

        # If a socket has been subscribed to, it's safe to launch the evaluation and listen
        if self.subscribed_to_channel:
            try:
                instructions: str = payload['instructions']

                channel_key = utilities.get_channel_key(self.channel_name)
                data = {
                    "channel_name": self.channel_name,
                    "channel_key": channel_key,
                    "channel_route": f"ws://{self.scope_data.server}/evaluation_service/ws/channel/{channel_key}"
                }

                launch_parameters = {
                    "purpose": "launch",
                    "evaluation_id": self.channel_name,
                    "verbosity": OUTPUT_VERBOSITY,
                    "start_delay": START_DELAY,
                    "instructions": instructions
                }

                # Send the job parameters through the channel that actively listens for jobs
                self.redis_connection.publish(EVALUATION_QUEUE_NAME, json.dumps(launch_parameters))

                await self.send_message(
                    result=data,
                    event="launch",
                    request_id=payload.get("request_id"),
                    logger="logger"
                )
                await self.tell_channel(event="launch", data=f"{str(self)}: Job Launched")
            except Exception as error:
                SOCKET_LOGGER.error(
                    message=f"{str(self)}: The job named {self.channel_name} could not be launched",
                    exception=error
                )
                await self.send_error(error, event="launch", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters()
    async def search(self, payload: typing.Dict[str, typing.Any] = None):
        try:
            if payload is None:
                payload = dict()

            payload = {
                key.lower(): value
                for key, value in payload.items()
            }

            filter_arguments = dict()

            if "author" in payload:
                filter_arguments['author__icontains'] = payload['author']

            if 'name' in payload:
                filter_arguments['name__icontains'] = payload['name']

            saved_definitions: typing.List[EvaluationDefinition] = EvaluationDefinitionCommunicator.filter(
                **filter_arguments
            )

            definitions_to_return = list()

            for saved_definition in saved_definitions:
                definitions_to_return.append({
                    "identifier": saved_definition.pk,
                    "author": saved_definition.author,
                    "name": saved_definition.name,
                    "description": saved_definition.description,
                })

            await self.send_message(
                event="search",
                result=definitions_to_return,
                request_id=payload.get(REQUEST_ID_KEY)
            )
        except Exception as exception:
            message = f"{str(self)}: Could not retrieve saved evaluation definitions"
            SOCKET_LOGGER.error(message, exception)
            await self.send_error(event="search", message=message, request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters(identifier=REQUIRED_PARAMETER_TYPES.number)
    async def get_saved_definition(self, payload: typing.Dict[str, typing.Any] = None):
        try:
            identifier = int(float(payload['identifier']))

            saved_definition: EvaluationDefinition = EvaluationDefinitionCommunicator.get(pk=identifier)

            payload = {
                "name": saved_definition.name,
                "definition": saved_definition.definition
            }
            await self.send_message(event="get_saved_definition", result=payload, request_id=payload.get(REQUEST_ID_KEY))
        except Exception as exception:
            message = f"{str(self)}: Could not retrieve evaluation definition with an identifier of " \
                      f"'{str(payload['identifier'])}'"
            SOCKET_LOGGER.error(message=message, exception=exception)
            await self.send_error(message, event="get_saved_definition", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters()
    async def get_template_specification_types(self, payload: typing.Dict[str, typing.Any] = None):
        message = {
            "specification_types": self.template_manager.get_specification_types()
        }
        await self.send_message(
            result=message,
            event="get_template_specification_types",
            request_id=payload.get(REQUEST_ID_KEY)
        )

    @required_parameters(specification_type=REQUIRED_PARAMETER_TYPES.text)
    async def get_templates(self, payload: typing.Dict[str, typing.Any] = None):
        message = {
            "templates": list()
        }

        for template in self.template_manager.get_templates(payload.get("specification_type")):
            message['templates'].append({
                "name": template.name,
                "specification_type": template.specification_type,
                "description": template.description
            })

        await self.send_message(result=message, event="get_templates", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters()
    async def get_all_templates(self, payload: typing.Dict[str, typing.Any] = None):
        response_data = {
            "templates": dict()
        }

        for specification_type, specification_type_name in self.template_manager.get_specification_types():
            templates: typing.List[typing.Dict[str, typing.Union[str, int]]] = list()

            matching_templates: typing.Sequence[models.SpecificationTemplate] = models.SpecificationTemplateCommunicator.filter(
                template_specification_type=specification_type
            )

            if not matching_templates:
                continue

            for template in matching_templates:
                templates.append({
                    "name": template.template_name,
                    "description": template.template_description,
                    "id": template.id,
                    "author": template.author
                })

            response_data['templates'][specification_type_name] = templates

        await self.send_message(result=response_data, event="get_all_templates", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters(configuration=REQUIRED_PARAMETER_TYPES.text)
    async def validate_configuration(self, payload: typing.Dict[str, typing.Any] = None):

        messages: typing.List[str] = list()

        try:
            EvaluationSpecification.create(
                payload['configuration'],
                self.template_manager,
                validate=True,
                messages=messages
            )
        except Exception as exception:
            common_logging.error(exception)
            messages.append(str(exception))

        message = {
            "passed": len(messages) == 0,
            "validation_messages": set(messages)
        }

        await self.send_message(result=message, event="validate_configuration", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters(
        specification_type=REQUIRED_PARAMETER_TYPES.text,
        name=REQUIRED_PARAMETER_TYPES.text,
        author=REQUIRED_PARAMETER_TYPES.text
    )
    async def get_template(self, payload: typing.Dict[str, typing.Any] = None):
        template = self.template_manager.get_template(
            specification_type=payload.get("specification_type"),
            name=payload.get("name")
        )
        template_message = {
            "template": json.dumps(template, indent=4)
        }

        await self.send_message(result=template_message, event="get_template", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters(template_id=REQUIRED_PARAMETER_TYPES.number)
    async def get_template_by_id(self, payload: typing.Dict[str, typing.Any] = None):
        template_id = payload.get("template_id")
        possible_template = models.SpecificationTemplateCommunicator.filter(id=template_id)
        response_type = None
        response_data = dict()

        if possible_template:
            template_entry: models.SpecificationTemplate = possible_template[0]
            response_data['template'] = template_entry.template_configuration
            response_data['author'] = template_entry.author
            response_data['specification_type'] = template_entry.specification_type
            response_data['description'] = template_entry.template_description
            response_data['name'] = template_entry.template_name

            await self.send_message(
                result=response_data,
                event="get_template_by_id",
                response_type=response_type,
                request_id=payload.get(REQUEST_ID_KEY)
            )
        else:
            await self.send_error(
                f"No template could be found with an ID of {template_id}",
                event="get_template_by_id",
                request_id=payload.get(REQUEST_ID_KEY)
            )

    @required_parameters()
    async def get_actions(self, payload: typing.Dict[str, typing.Any] = None):
        """
        Sends a detailed listing of all possible actions and their required parameters through the socket

        Args:
            payload: The arguments sent through the socket when asking to perform this action
        """
        actions = self.generate_action_catalog()
        await self.send_message(result=actions, event="get_actions", request_id=payload.get(REQUEST_ID_KEY))

    @required_parameters()
    async def generate_library(self, payload: typing.Dict[str, typing.Any] = None):
        library_data = {
            "library": self.build_code()
        }
        await self.send_message(
            result=library_data,
            response_type="generate_library",
            request_id=payload.get(REQUEST_ID_KEY)
        )

    @required_parameters(
        name=REQUIRED_PARAMETER_TYPES.text,
        description=REQUIRED_PARAMETER_TYPES.text,
        author=REQUIRED_PARAMETER_TYPES.text,
        instructions=REQUIRED_PARAMETER_TYPES.text
    )
    async def save(self, payload: typing.Dict[str, typing.Any] = None):
        """
        Saves the configured evaluation for later use

        Args:
            payload: The arguments passed along the socket
        """
        try:
            # Retrieve the required parameters
            name = payload['name']
            description = payload['description']
            author = payload['author']
            instructions = payload['instructions']

            definition, was_created = models.EvaluationDefinitionCommunicator.update_or_create(
                name=name,
                description=description,
                author=author,
                definition=instructions
            )

            # Prepare data to send back to the caller
            response_data = {
                "evaluation_name": name,
                "description": description,
                "author": author,
                "new_project": was_created
            }

            # Send result information detailing what was saved and whether it was created
            await self.send_message(response_data, event="save", request_id=payload.get(REQUEST_ID_KEY))
        except Exception as error:
            SOCKET_LOGGER.error(message=error)
            await self.send_error(error, event="save")

    async def tell_channel(self, event: str = None, data=None, log_data: bool = False):
        """
        Send data to the redis channel

        Args:
            event: The event that necessitated the communication
            data: The data to send to the redis channel
            log_data: Whether data received should be logged for later reference
        """
        if log_data:
            SOCKET_LOGGER.debug(
                data or f"{str(self)}: No Data was given to publish to {self.connection_group_id}"
            )

        message = make_message(event=event, data=data)
        await self.channel_layer.group_send(
            self.connection_group_id,
            message
        )

    # catches group messages from channel layer and forwards downstream to client
    async def forward_group_message(self, event):
        SOCKET_LOGGER.debug(
            f"[{str(self)}] Captured forwarded message and sending to {self.connection_group_id}"
        )
        await self.send(
            text_data=json.dumps(event) if not isinstance(event, (str,bytes)) else event
        )
        SOCKET_LOGGER.debug(f"[{str(self)}] Sent data to {self.connection_group_id}")

    async def send_message(
        self,
        result: typing.Union[int, str, bytes, typing.Mapping, typing.Sequence],
        event: str = None,
        response_type: str = None,
        request_id: str = None,
        logger: typing.Union[str, logging.Logger, common_logging.ConfiguredLogger] = None,
        **kwargs
    ):
        """
        Formats a message in such a way that it is ready to send through a socket to a client

        Args:
            result: The data to send to a client
            event: The name of the event that triggered the message
            response_type: The type of message
            request_id: An optional ID linking the request to its response
            logger: A logger that all errors for the call should be logged to
            **kwargs:
        """
        if isinstance(result, bytes):
            result = result.decode()

        message = make_websocket_message(
            event=event,
            response_type=response_type,
            data=result,
            request_id=request_id,
            logger=logger or SOCKET_LOGGER
        )

        await self.send(message)

    async def send_error(self, message: typing.Union[str, dict, Exception], event: str = None, request_id: str = None):
        """
        Send a message specifically formatted for errors through the socket

        Args:
            message: Information about the error
            event: The event within which the error occurred
            request_id: An optional ID linking the request with the upcoming response
        """
        if not event:
            event = "error"

        if isinstance(message, bytes):
            message = message.decode()

        if not isinstance(message, (str, dict)):
            message = str(message)

        await self.send_message(
            result=message,
            event=event,
            response_type="error",
            request_id=request_id
        )

    async def disconnect(self, close_code):
        """
        Handles the disconnection of the handler

        Args:
            close_code: A code used to detail the conditions upon which this handler was disconnected
        """
        try:
            await self.send(make_websocket_message(event="disconnect", data="Disconnecting from server"))
        except Exception as error:
            SOCKET_LOGGER.error(f"{str(self)}: Could not tell the client that the socket is disconnecting", error)

        try:
            if self.listener and self.listener.is_alive():
                self.listener.stop()
            SOCKET_LOGGER.debug(f"{str(self)}:  listener closed")
        except Exception as disconnection_error:
            message = f"{str(self)}: Listener thread could not be killed"
            SOCKET_LOGGER.error(
                message,
                disconnection_error
            )

        try:
            if self.publisher_and_subscriber:
                self.publisher_and_subscriber.unsubscribe()
            SOCKET_LOGGER.debug(f"{str(self)}: Redis Channel disconnected")
        except Exception as e:
            SOCKET_LOGGER.error(message=f"{str(self)}: Could not unsubscribe from redis channel", exception=e)

        try:
            if self.redis_connection:
                self.redis_connection.close()
            SOCKET_LOGGER.debug(f"{str(self)}: Redis connection closed")
        except Exception as e:
            SOCKET_LOGGER.error(f"{str(self)}: Could not disconnect from redis", e)

        if self.subscribed_to_channel and self.channel_name and self.connection_group_id:
            await self.channel_layer.group_discard(
                self.connection_group_id,
                self.channel_name
            )
        SOCKET_LOGGER.debug(f"{str(self)}: {self.connection_group_id} has been discarded from the channel layer")

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.channel_name} <=> " \
               f"{':'.join([str(entry) for entry in self.scope['client']])}"

    def __repr__(self):
        """
        Makes a helpful string representation used for object examination (repr(obj), not str(obj))

        Should look something like:


            '{
                "class": "LaunchConsumer",

                "channel_name": "evaluation_name",

                "connection_group_id": "some--prefix--evaluation_name--suffix",

                "redis_connection": "username@host:port",

                "host": "server-address:port"
            }'

        Returns:
            a helpful string representation used for object examination
        """
        redis_connection_details = f"{self.redis_connection.connection.username}" \
                                   f"@{self.redis_connection.connection.host}" \
                                   f":{str(self.redis_connection.connection.port)}"
        return json.dumps({
            "class": self.__class__.__name__,
            "channel_name": self.channel_name,
            "connection_group_id": self.connection_group_id,
            "redis_connection": redis_connection_details,
            "host": self.scope_data.server
        }, indent=4)


class ChannelConsumer(AsyncWebsocketConsumer):
    """
    Web Socket consumer that forwards messages to and from redis PubSub
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_connection: redis.Redis = utilities.get_redis_connection()
        self.publisher_and_subscriber: typing.Optional[redis_client.PubSub] = None
        self.listener: typing.Optional[redis.client.PubSubWorkerThread] = None
        self.connection_group_id: typing.Optional[str] = None
        self.channel_name: typing.Optional[str] = None
        self.__scope: typing.Optional[ConcreteScope] = None

    @property
    def scope_data(self) -> ConcreteScope:
        if self.__scope is None:
            self.__scope = ConcreteScope(self.scope)

        return self.__scope

    def receive_subscribed_message(self, message):
        if isinstance(message, (str, bytes)):
            deserialized_message = json.loads(message)
        else:
            deserialized_message = message

        # This needs to crawl through a dict and make sure that none of its children are bytes
        deserialized_message = make_message_serializable(deserialized_message)

        response = make_websocket_message(
            event="subscribed_message_received",
            data=deserialized_message,
            logger=SOCKET_LOGGER
        )

        # The caller requires this function to be synchronous, whereas `send_message` is async;
        # we're stuck using async_to_sync here as a result
        async_to_sync(self.send_message)(response)

    async def connect(self):
        self.channel_name = self.scope_data.keyword_arguments.get("channel_name")
        self.connection_group_id = utilities.get_channel_key(self.channel_name)

        if not self.connection_group_id:
            raise ValueError("No channel name was passed; no channel may be subscribed to")

        self.publisher_and_subscriber = self.redis_connection.pubsub()

        self.publisher_and_subscriber.subscribe(
            **{
                self.connection_group_id: self.receive_subscribed_message
            }
        )

        self.listener = self.publisher_and_subscriber.run_in_thread(sleep_time=0.001)

        await self.channel_layer.group_add(
            self.connection_group_id,
            self.channel_name
        )

        SOCKET_LOGGER.debug(f"[{str(self)}] {self.connection_group_id} was added to the channel layer")

        await self.accept()

        connection_message = f"{str(self)}: Connection accepted. Connection Group is: {self.connection_group_id}"
        await self.tell_channel(event="Connect", data=connection_message, log_data=True)
        await self.send(make_websocket_message(event="connect", data=connection_message))

    async def receive(self, text_data=None, **kwargs):
        """
        Processes messages received via the socket.

        Called when the other end of the socket sends a message

        Args:
            text_data: The data sent over the socket
            **kwargs:
        """
        message = f"[{str(self)}] This connection only forwards messages from a redis channel"
        await self.tell_channel(
            event="receive",
            data={"received": text_data, "message": message}
        )
        await self.send(make_websocket_message(event="receive", response_type="error", data=message, logger=SOCKET_LOGGER))

        # We don't necessarily want to stop processing if the receive function is encountered since that's
        # more of a client issue, not a listener issue.
        exception = NotImplementedError(message)
        SOCKET_LOGGER.error(exception)
        SOCKET_LOGGER.debug(
            f"[{str(str)}] Error encountered; the listener does not accept general websocket messages. "
            f"Data received: {str(text_data)}"
        )
        try:
            scope_string = f"Scope:{os.linesep}{json.dumps(self.scope, indent=4)}"
        except:
            scope_string = f"Scope: {str(self.scope)}"
        SOCKET_LOGGER.debug(f"[{str(self)}] {scope_string}")

    async def tell_channel(self, event: str = None, data=None, log_data: bool = False):
        """
        Send data to the redis channel

        Args:
            event: The event that necessitated the communication
            data: The data to send to the redis channel
            log_data: Whether data received should be logged for later reference
        """
        if log_data:
            SOCKET_LOGGER.debug(
                data or f"{str(self)}: No Data was given to publish to {self.connection_group_id}"
            )

        message = make_message(event=event, data=data)
        await self.channel_layer.group_send(
            self.connection_group_id,
            message
        )

    # catches group messages from channel layer and forwards downstream to client
    async def forward_group_message(self, event):
        SOCKET_LOGGER.debug(
            f"[{str(self)}] Captured forwarded message and sending to {self.connection_group_id}"
        )
        await self.send(
            text_data=json.dumps(event) if not isinstance(event, (str,bytes)) else event
        )
        SOCKET_LOGGER.debug(f"[{str(self)}] Sent data to {self.connection_group_id}")

    async def send_message(self, result):
        if isinstance(result, bytes):
            result = result.decode()

        await self.send(
            text_data=json.dumps(result) if not isinstance(result, (str, bytes)) else result
        )

    async def disconnect(self, close_code):
        try:
            await self.send(make_websocket_message(event="disconnect", data="Disconnecting from server"))
        except Exception as error:
            SOCKET_LOGGER.error(f"{str(self)}: Could not tell the client that the socket is disconnecting", error)

        try:
            if self.listener and self.listener.is_alive():
                self.listener.stop()
            SOCKET_LOGGER.debug(f"{str(self)}:  listener closed")
        except Exception as disconnection_error:
            message = f"{str(self)}: Listener thread could not be killed"
            SOCKET_LOGGER.error(
                message,
                disconnection_error
            )

        try:
            if self.publisher_and_subscriber:
                self.publisher_and_subscriber.unsubscribe()
            SOCKET_LOGGER.debug(f"{str(self)}: Redis Channel disconnected")
        except Exception as e:
            SOCKET_LOGGER.error(message=f"{str(self)}: Could not unsubscribe from redis channel", exception=e)

        try:
            if self.redis_connection:
                self.redis_connection.close()
            SOCKET_LOGGER.debug(f"{str(self)}: Redis connection closed")
        except Exception as e:
            SOCKET_LOGGER.error(f"{str(self)}: Could not disconnect from redis", e)

        await self.channel_layer.group_discard(
            self.connection_group_id,
            self.channel_name
        )
        SOCKET_LOGGER.debug(f"{str(self)}: {self.connection_group_id} has been discarded from the channel layer")

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.channel_name} <=> " \
               f"{':'.join([str(entry) for entry in self.scope['client']])}"

    def __repr__(self):
        redis_connection_details = f"{self.redis_connection.connection.username}" \
                                   f"@{self.redis_connection.connection.host}" \
                                   f":{str(self.redis_connection.connection.port)}"
        return json.dumps({
            "class": self.__class__.__name__,
            "channel_name": self.channel_name,
            "connection_group_id": self.connection_group_id,
            "redis_connection": redis_connection_details,
            "host": ":".join([str(entry) for entry in self.scope['host']])
        }, indent=4)
