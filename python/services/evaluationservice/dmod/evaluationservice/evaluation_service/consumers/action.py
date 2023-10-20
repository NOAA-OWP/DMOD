"""
Defines a self-describing mixin that can generate its own client library
"""
import inspect
import os
import re
import typing

from datetime import datetime

from dmod.core.common import humanize_text

from service.application_values import COMMON_DATETIME_FORMAT


class __RequiredParameterType:
    @property
    def text(self) -> str:
        return "text"

    @property
    def number(self) -> str:
        return "number"

    @property
    def boolean(self) -> str:
        return "checkbox"

    @property
    def color(self) -> str:
        return "color"

    @property
    def date(self) -> str:
        return "date"

    @property
    def datetime(self) -> str:
        return "datetime-local"

    @property
    def month(self) -> str:
        return "month"

    @property
    def password(self) -> str:
        return "password"

    @property
    def time(self) -> str:
        return "time"

    @property
    def week(self) -> str:
        return "week"

    @property
    def file(self) -> str:
        return "file"

    @property
    def image(self) -> str:
        return "image"


class __SupportedLanguages:
    @property
    def javascript(self):
        return "javascript"

    def all(self) -> typing.Sequence[str]:
        language_members: typing.Mapping[str, typing.Any] = {
            member_name: member
            for member_name, member in inspect.getmembers(self)
            if not member_name.startswith("_")
                and isinstance(getattr(self.__class__, member_name), property)
        }
        return [language.lower() for language in language_members.keys()]

    def is_supported(self, language: str):
        language = language.lower()
        return language in self.all()


REQUIRED_PARAMETER_TYPES = __RequiredParameterType()
SUPPORTED_LANGUAGES = __SupportedLanguages()


def to_javascript_name(word: str) -> typing.Optional[str]:
    """
    Converts a name to one that fits the javascript standard.

    Example:
        >>> to_javascript_name("THIS_IS_A_PHRASE")
        thisIsAPhrase
        >>> to_javascript_name("ThIsIS_aPhrAse")
        thisIsAPhrase

    Params:
        word: The word to format

    Returns:
        The given word in the format that suits Javascript's standard
    """
    if not isinstance(word, str) or len(word) == 0:
        return word

    cleaned_word = humanize_text(word)
    cleaned_word = cleaned_word.replace("-", " ").replace(" ", "")

    first_letter = cleaned_word[0].lower()
    return f"{first_letter}{cleaned_word[1:]}"


def required_parameters(**kwargs) -> typing.Callable:
    """
    Decorator used to add an attribute onto functions detailing their required parameters

    Args:
        **kwargs: Key value pairs

    Returns:
        The updated function
    """
    def function_with_parameters(func):
        """
        Add keyword arguments to the given func under the attribute `required_parameters`

        Args:
            func: The function to add required parameters to

        Returns:
            The updated function
        """
        setattr(func, "required_parameters", kwargs)
        return func

    return function_with_parameters


def parameter_options(**kwargs) -> typing.Callable:
    """
    Decorator used to indicate options for a function call that aren't necessary to call the function,
    but provides further functionality

    Args:
        **kwargs: Key value pairs mapping the name of a parameter to its value type

    Returns:
        The updated function
    """
    keyword_arguments = kwargs or dict()

    def function_with_parameters(function):
        """
        Add keyword arguments to the given function under the attribute 'optional_parameters'

        Args:
            function: The function to add optional parameters to

        Returns:
            The updated function
        """
        setattr(function, 'optional_parameters', keyword_arguments)
        return function

    return function_with_parameters


def outbound_variables(**kwargs) -> typing.Callable:
    """
    Decorator that adds data to a function to describe what values will appear within the transmitted socket response

    Args:
        **kwargs: Key value pairs mapping the name of a response value to its expected type

    Returns:
        The updated function
    """
    keyword_arguments = kwargs or dict()

    def function_with_parameters(function):
        """
        Add the keyword arguments under the attribute `outbound_variables`

        Args:
            function: The function to add outbound parameters to

        Returns:
            The updated function
        """
        setattr(function, "outbound_variables", keyword_arguments)
        return function

    return function_with_parameters


class ActionDescriber:
    @classmethod
    def get_client_name(cls):
        consumer_pattern = re.compile("[Cc][Oo][Nn][Ss][Uu][Mm][Ee][Rr]")
        class_name = consumer_pattern.sub("", cls.__name__) + "Client"
        return class_name

    @classmethod
    def get_action_handlers(cls) -> typing.Dict[str, typing.Callable[[typing.Dict[str, typing.Any]], typing.Coroutine]]:
        """
        Generates a mapping of names for socket actions to functions that bear a dictionary of their required
        parameters mapped to human friendly strings of their expected data types

        Returns:
            A dictionary mapping the name of actions a client may request to the functions that handle them
        """
        def callable_requires_parameters(member) -> bool:
            """
            Checks to see if a passed member counts as an action handler

            Args:
                member: A member retrieved by calling `inspect.get_members`

            Returns:
                Whether the passed member is a callable with a  `required_parameters` map
            """
            return isinstance(member, typing.Callable) \
                   and hasattr(member, 'required_parameters') \
                   and isinstance(getattr(member, 'required_parameters'), dict)

        return {
            handler_name: handler
            for handler_name, handler in inspect.getmembers(cls, predicate=callable_requires_parameters)
        }

    @classmethod
    def _interpret_handler_as_schema(cls, name: str, function: typing.Callable[[typing.Dict[str, typing.Any]], typing.Coroutine]) -> typing.Mapping[str, typing.Union[str, typing.Mapping[str, typing.Any]]]:
        schema = {
            "title": name,
            "type": 'object',
            "required": list(),
            "properties": dict()
        }

        documentation = ""

        if function.__doc__:
            split_documentation = function.__doc__.strip().split("\n")
            if len(split_documentation) > 0:
                documentation = split_documentation[0]

        schema['description'] = documentation

        for parameter_name, parameter_type in getattr(function, 'required_parameters').items():
            schema['required'].append(parameter_name)
            schema['properties'][parameter_name] = {
                "title": parameter_name.replace("_", " ").title(),
                "type": parameter_type
            }

        return schema

    @classmethod
    def _interpret_handler(cls, name: str, function: typing.Callable[[typing.Dict[str, typing.Any]], typing.Coroutine]) -> typing.Mapping[str, typing.Union[str, typing.Mapping[str, typing.Any]]]:
        documentation = ""

        if function.__doc__:
            split_documentation = function.__doc__.strip().split("\n")
            if len(split_documentation) > 0:
                documentation = split_documentation[0]

        descriptor = {
            "action": name,
            "documentation": documentation
        }

        action_parameters = {
            parameter_name: {
                "type": parameter_type,
                "required": False
            }
            for parameter_name, parameter_type in getattr(function, "optional_parameters", dict()).items()
        }

        action_parameters.update(
            {
                parameter_name: {
                    "type": parameter_type,
                    "required": True
                }
                for parameter_name, parameter_type in getattr(function, "required_parameters").items()
            }
        )

        descriptor['action_parameters'] = action_parameters

        return descriptor

    @classmethod
    def generate_action_catalog(cls, schema: bool = None) -> typing.Sequence[typing.Mapping[str, typing.Union[str, typing.Mapping[str, typing.Any]]]]:
        if schema is None:
            schema = False

        actions = list()

        for name, function in cls.get_action_handlers().items():
            # `function` will be a function like `(dict) => Coroutine`, where the function will have a dictionary
            # mapping the name of required parameters for each handler to a human friendly description of its type
            if schema:
                descriptor = cls._interpret_handler_as_schema(name, function)
            else:
                descriptor = cls._interpret_handler(name, function)

            actions.append(descriptor)

        actions = sorted(actions, key=lambda action: action['action'])
        return actions

    @classmethod
    def build_javascript(cls):
        actions = cls.generate_action_catalog()

        class_doc = f'{os.linesep} * '.join(cls.__doc__.strip().split(os.linesep))

        # TODO: Add typedefs for found outbound variable types and replace the ActionParameters typedef with
        #  several similar typedefs that use the new outbound variable typedefs as its value for 'data'
        #  instead of just 'object'

        library = f"""/**
 * Generated module used to send formatted requests through a web socket
 * Generated at: {datetime.now().astimezone().strftime(COMMON_DATETIME_FORMAT)}
 */

/**
 * @typedef {{Object}} ActionParameters
 * @description Result data from a server action
 * @property {{string}} event
 * @property {{string}} type
 * @property {{Object}} data
 * @property {{String}} time
 */

 /**
  * @typedef {{(response: ActionParameters, socket: WebSocket) => any}} ActionHandler
  * @description A function that can handle events from the client
  */

/**
 * @typedef {{(MessageEvent) => any}} SocketHandler
 * @description A function that can serve as an event handler for raw websocket messages
 */

/**
 * @typedef {{function(string, Object<string, any>?): Error}} ExceptionConstructor
 * @description A constructor for a specialized type of error
 */

/**
 * @typedef {{(string) => any}} ClientErrorHandler
 * @description A function that accepts an error message and an optional function (such as an exception constructor)
 */

/**
 *
 * @param {{Array|Object}} obj The object to convert to JSON
 * @returns {{string}}
 */
function toJSON(obj) {{
    return JSON.stringify(obj, null, 4);
}}

/**
 * Generate a fairly unique ID
 *
 * Conflicts are not a big deal - non-unique values are fine as long as their lifetimes don't overlap which is unlikely
 * considering that most operations are short lived. If a greater degree of uniqueness is desired, bundle the action
 * name with the generated ID when recording callbacks.
 *
 * You can expect IDs like:
 *
 * @example
 * generateID()
 * // Returns 'emh75or6lte-nwk4p5kpvpp'
 *
 * generateID(1)
 * // Returns 'wqt14i8esul'
 *
 * generateID(4)
 * // Returns 'pzpaxsm3hsk-ygvd58u1tk-f3kse50r4n4-db5nqxxp5ds'
 *
 *
 * @param {{Number?}} iterations The number of blocks to iteratively add to the ID
 * @returns {{string}}
 */
function generateID(iterations) {{
    let IDParts = [];

    iterations = typeof iterations === 'number' ? iterations : 2;

    for (let iterationIndex = 0; iterationIndex < iterations; iterationIndex++) {{
        // Random text:
        let idPart = Math.random().toString(36);

        // The above call will return something like '0.7ytgv08253s'.
        // Take everything after the '.' to get the reasonable string
        idPart = idPart.substring(2);
        IDParts.push(idPart);
    }}

    return IDParts.join("-");
}}

export class {cls.get_client_name()}Error extends Error {{}}

export class {cls.get_client_name()}Options {{
    /**
     * A collection of handlers that a client will call when the 'onmessage' event is triggered
     * @type {{ActionHandler[]}}
     */
    #onmessageHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onerror' event is triggered
     * @type {{SocketHandler[]}}
     */
    #onSocketErrorHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onopen' event is triggered
     * @type {{SocketHandler[]}}
     */
    #onopenHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onclose' event is triggered
     * @type {{SocketHandler[]}}
     */
    #oncloseHandlers = [];

    /**
     * Independent handlers for onmessage event types
     * @type {{Object<string, ActionHandler[]>}}
     */
    #actions = {{}};

    /**
     * Handlers for errors that might occur within the client itself
     * @type {{ClientErrorHandler[]}}
     */
    #clientErrorHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onmessage' event is triggered
     * @type {{ActionHandler[]}}
     */
    get onmessageHandlers() {{
        return [...this.#onmessageHandlers]
    }}

    /**
     * A collection of handlers that a client will call when the 'onerror' event is triggered
     * @type {{SocketHandler[]}}
     */
    get onSocketErrorHandlers() {{
        return [...this.#onSocketErrorHandlers];
    }}

    /**
     * Handlers for errors that might occur within the client itself
     * @returns {{ClientErrorHandler[]}}
     */
    get clientErrorHandlers() {{
        return [...this.#clientErrorHandlers];
    }}

    /**
     * A collection of handlers that a client will call when the 'onopen' event is triggered
     * @type {{SocketHandler[]}}
     */
    get onopenHandlers() {{
        return [...this.#onopenHandlers];
    }}

    /**
     * A collection of handlers that a client will call when the 'onclose' event is triggered
     * @type {{SocketHandler[]}}
     */
    get oncloseHandlers() {{
        return [...this.#oncloseHandlers];
    }}

    /**
     * Independent handlers for onmessage event types
     * @type {{Object<string, ActionHandler[]>}}
     */
    get actions() {{
        const copiedActions = {{}};

        for (let [actionName, configuredActions] of Object.entries(this.#actions)) {{
            copiedActions[actionName] = Array.isArray(configuredActions) ? [...configuredActions] : [];
        }}

        return copiedActions;
    }}

    /**
     * Add a handler that will be called when the socket fires the `onmessage` event
     * @param {{ActionHandler}} handler The handler function that will be called
     * @returns {{{cls.get_client_name()}Options}} The options for this {cls.get_client_name()} client
     */
    addMessageHandler = (handler) => {{
        this.#onmessageHandlers.push(handler);
        return this;
    }}

    /**
     * Add a handler that will be called when the socket fires the `onopen` event
     * @param {{SocketHandler}} handler The handler function that will be called
     * @returns {{{cls.get_client_name()}Options}} The options for this {cls.get_client_name()} client
     */
    addOpenHandler = (handler) => {{
        this.#onopenHandlers.push(handler);
        return this;
    }}

    /**
     * Add a handler that will be called when the socket fires the `onclose` event
     * @param {{SocketHandler}} handler The handler function that will be called
     * @returns {{{cls.get_client_name()}Options}} The options for this {cls.get_client_name()} client
     */
    addCloseHandler = (handler) => {{
        this.#oncloseHandlers.push(handler);
        return this;
    }}

    /**
     * Add a handler that will be called when the socket fires the `onerror` event
     * @param {{SocketHandler}} handler The handler function that will be called
     * @returns {{{cls.get_client_name()}Options}} The options for this {cls.get_client_name()} client
     */
    addSocketErrorHandler = (handler) => {{
        this.#onSocketErrorHandlers.push(handler);
        return this;
    }}
    
    /**
     * Add a handler that will be called when the client itself encounters an error
     * @param {{ClientErrorHandler}} handler
     * @returns {{{cls.get_client_name()}Options}}
     */
    addClientErrorHandler = (handler) => {{
        this.#clientErrorHandlers.push(handler);
        return this;
    }}

    /**
     * Add a handler that will be called when the socket fires the `onmessage` event
     * @param {{string}} actionName The name of the event that should trigger this function
     * @param {{ActionHandler}} handler The handler function that will be called
     * @returns {{{cls.get_client_name()}Options}} The options for this {cls.get_client_name()} client
     */
    addActionHandler = (actionName, handler) => {{
        if (!Object.keys(this.#actions).includes(actionName)) {{
            this.#actions[actionName] = [];
        }}

        this.#actions[actionName].push(handler);
        return this;
    }}
}}

/**
 * {class_doc}
 */
export class {cls.get_client_name()} {{
    /**
     * The URL to the service
     * @type {{string|null}}
     */
    #url = null;

    /**
     * The WebSocket through which communication flows to and fro
     * @type {{WebSocket}}
     */
    #socket = null;

    /**
     * Independent handlers for onmessage event types
     * @type {{Object<string, ActionHandler[]>}}
     */
    #actions = {{}};

    /**
     * Handlers that will be called when the socket receives a message
     * @type {{ActionHandler[]}}
     */
    #onmessageHandlers = [];

    /**
     * Handlers that will be called when the socket receives an  error
     * @type {{ActionHandler[]}}
     */
    #onSocketErrorHandlers = [];

    /**
     * Handlers for errors that might arise within the client itself
     * @type {{ClientErrorHandler[]}}
     */
    #clientErrorHandlers = [];

    /**
     * Handlers that will be called when the socket connection is opened
     * @type {{ActionHandler[]}}
     */
    #onOpenHandlers = [];

    /**
     * Handlers that will be called when the socket connection is closed
     * @type {{ActionHandler[]}}
     */
    #onCloseHandlers = [];

    /**
     * Flag stating whether 'attachHandlers' has been called. Calling it multiple times will break how events are
     * handled by feeding the wrong parameters to the wrong functions
     * @type {{boolean}}
     */
    #addedWrapperHandlers = false;

    /**
     * A mapping of functions to their request IDs. If a response comes in with a matching ID,
     * the matching callback(s) will be used instead of the default or configured handlers and removed from the map
     * @type {{Object<string, ActionHandler[]>}}
     */
    #callbacks = {{}};

    constructor(socketOrAddress, options) {{
        this.#applyOptions(options);
        if (typeof socketOrAddress === 'string') {{
            this.#url = socketOrAddress;
            this.#socket = new WebSocket(socketOrAddress);
        }}
        else {{
            this.#socket = socketOrAddress;
        }}
        this.attachHandlers();
    }}

    /**
     * Apply options provided by the constructor
     *
     * @param {{{cls.get_client_name()}Options|Object}} options
     */
    #applyOptions(options) {{
        if (options == null) {{
            return;
        }}

        if ("onmessageHandlers" in options) {{
            this.#onmessageHandlers = options.onmessageHandlers;
        }}

        if ("onSocketErrorHandlers" in options) {{
            this.#onSocketErrorHandlers = options.onSocketErrorHandlers;
        }}

        if ("onopenHandlers" in options) {{
            this.#onOpenHandlers = options.onopenHandlers;
        }}

        if ("oncloseHandlers" in options) {{
            this.#onCloseHandlers = options.oncloseHandlers;
        }}

        if ("clientErrorHandlers" in options) {{
            this.#clientErrorHandlers = options.clientErrorHandlers;
        }}

        if ("actions" in options) {{
            this.#actions = options.actions;
        }}
    }}

    /**
     * Attach a new onmessage handler to this client's web socket that will call all registered handlers
     *
     * If the socket already has an `onmessage` handler, it will be called from within the new handler
     */
    attachHandlers = () => {{
        if (this.#addedWrapperHandlers) {{
            this.handleError("Handlers on this {cls.get_client_name()} instance have already been attached");
        }}

        this.#socket['overriddenOnMessageFunction'] = this.#socket.onmessage != null ? this.#socket.onmessage : (_) => null;

        this.#socket.onmessage = (response) => {{
            if (Object.keys(this.#socket).includes('overriddenOnMessageFunction')) {{
                this.#socket['overriddenOnMessageFunction'](response);
            }}

            if (!("data" in response)) {{
                if (this.#onmessageHandlers.length > 0) {{
                    console.warn("Cannot call registered 'onmessage' handlers - no data payload was received")
                }}
                return;
            }}

            /**
             * The data formed on the server
             * @type {{ActionParameters}}
             */
            const actionParameters = JSON.parse(response.data);

            for (let handler of this.#onmessageHandlers) {{
                handler(actionParameters, this.#socket);
            }}

            if ("request_id" in actionParameters && actionParameters["request_id"] in this.#callbacks) {{
                this.#callbacks[actionParameters['request_id']].forEach(
                    handler => handler(actionParameters, this.#socket)
                );
                delete this.#callbacks[actionParameters['request_id']];
                return;
            }}

            let event = "";

            if (Object.keys(actionParameters).includes("event")) {{
                event = actionParameters.event;
            }}

            if (Object.keys(this.#actions).includes(event)) {{
                this.#actions[event].forEach(handler => handler(actionParameters, this.#socket));
            }}
        }};

        this.#socket['overriddenOnOpenFunction'] = this.#socket.onopen != null ? this.#socket.onopen : (_) => null;

        this.#socket.onopen = (response) => {{
            if (Object.keys(this.#socket).includes('overriddenOnOpenFunction')) {{
                this.#socket['overriddenOnOpenFunction'](response);
            }}

            for (let handler of this.#onOpenHandlers) {{
                handler(response);
            }}
        }}

        this.#socket['overriddenOnCloseFunction'] = this.#socket.onclose != null ? this.#socket.onclose : (_) => null;

        this.#socket.onclose = (response) => {{
            if (Object.keys(this.#socket).includes('overriddenOnCloseFunction')) {{
                this.#socket['overriddenOnCloseFunction'](response);
            }}

            for (let handler of this.#onCloseHandlers) {{
                handler(response);
            }}
        }}

        this.#socket['overriddenOnErrorFunction'] = this.#socket.onerror != null ? this.#socket.onerror : (_) => null;

        this.#socket.onerror = (response) => {{
            if (Object.keys(this.#socket).includes('overriddenOnErrorFunction')) {{
                this.#socket['overriddenOnErrorFunction'](response);
            }}

            for (let handler of this.#onSocketErrorHandlers) {{
                handler(response);
            }}
        }}


        this.#addedWrapperHandlers = true;
    }}

    /**
     * Add a handler for a specific type of server response
     * @param {{string}} actionName
     * @param {{ActionHandler}} handler
     * @returns {{{cls.get_client_name()}}} This client
     */
    on = (actionName, handler) => {{
        if (actionName == null || actionName === '' || typeof actionName !== 'string') {{
            this.handleError("Cannot assign a new action handler - a valid action name was not provided");
        }}
        if (typeof handler !== 'function') {{
            this.handleError(
                `Cannot assign a handler for the '${{actionName}}' event - the handler wasn't valid`
            );
        }}

        if (!(actionName in this.#actions)) {{
            this.#actions[actionName] = [];
        }}

        this.#actions[actionName].push(handler);
        return this;
    }}

    /**
     * Handles errors that arise from within the client
     * @param {{string}} message
     * @param {{ExceptionConstructor?}} exceptionConstructor
     * @param {{boolean?}} throwError
     */
    handleError = (message, exceptionConstructor, throwError) => {{
        if (throwError == null) {{
            throwError = true;
        }}
        
        let initialError = null;

        for (let handler of this.#clientErrorHandlers) {{
            try {{
                handler(message);
            }} catch(error) {{
                if (initialError == null) {{
                    initialError = error;
                    continue
                }}
                
                let oldError = initialError;
                
                if (error instanceof Error) {{
                    initialError = new {cls.get_client_name()}Error(error.message);
                }}
                else {{
                    initialError = new {cls.get_client_name()}Error(error);
                }}
                
                initialError.cause = oldError;
            }}
        }}
        
        if (throwError) {{
            if (exceptionConstructor == null) {{
                exceptionConstructor = error => new {cls.get_client_name()}Error(error);
            }}
    
            throw exceptionConstructor(message);
        }}
        else {{
            console.error(message);
        }}
    }}
"""

        for action in actions:
            action_name = action['action']
            lines: typing.List[str] = list()

            signature = f"{to_javascript_name(action_name)} = ("
            parameters: typing.List[str] = [parameter_name for parameter_name in action['action_parameters'].keys()]
            signature += ', '.join(parameters)

            if len(parameters) > 0:
                signature += ", "

            signature += "optionalParameters, callbacks) => {"

            documentation = action.get("documentation")

            documentation_lines: typing.List[str] = ["    /**"]

            if documentation:
                documentation_lines.append(documentation)

            if parameters:
                for parameter_name, metadata in action['action_parameters'].items():
                    parameter_type = metadata['type']
                    required = metadata['required']
                    argument_type = f"{{{'String' if parameter_type == 'text' else parameter_type.title()}"
                    if not required:
                        argument_type += "?"
                    argument_type += f"}}"
                    documentation_lines.append(
                        f"@param {{{'String' if parameter_type == 'text' else parameter_type.title()}}} "
                        f"{parameter_name}"
                    )

            documentation_lines.append("@param {Object<string, any>?} optionalParameters Optional Parameters")
            documentation_lines.append("@param {(ActionHandler|ActionHandler[])?} callbacks")
            documentation_lines.append(f"@returns {{{cls.get_client_name()}}} this client")

            documentation_line = f"{os.linesep}     * ".join(documentation_lines)

            if documentation_line:
                documentation_line += f"{os.linesep}     **/"

            payload_lines: typing.List[str] = [f"""const payload = {{
            "action": "{action_name}",
            "action_parameters": {{"""]

            if parameters:
                for parameter_name in parameters:
                    parameter = f'                "{parameter_name}": {parameter_name},'
                    payload_lines.append(parameter)
            payload_lines.append(f'                "request_id": requestID,')
            payload_lines.append(f'                ...optionalParameters')
            payload_lines.append('            }')
            payload_lines.append("        }")

            lines.append(os.linesep.join(payload_lines))

            library += f"""{os.linesep + documentation_line if documentation_line else ''}
    {signature}
    
        const requestID = generateID();

        if (callbacks != null) {{
            if (!Array.isArray(callbacks)){{
                callbacks = [callbacks];
            }}

            this.#callbacks[requestID] = callbacks;
        }}
        
        {os.linesep.join(payload_lines)}
        this.#socket.send(toJSON(payload));
        return this;
    }}
    
    /**
     * Add a handler that will be called when a message comes through the socket with the event '{action_name}'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {{(ActionParameters) => any}} handler A handler that will be called when the '{action_name}' event is received
     * @returns {{{cls.get_client_name()}}} This client
     */
    {to_javascript_name('on' + humanize_text(action_name))} = (handler) => {{
        if (!this.#addedWrapperHandlers) {{
            this.handleError(
                "The `addHandler` function must be called on this `{cls.get_client_name()}` instance in order to register a handler for the '{action_name}' event."
            );
        }}
        if (!Object.keys(this.#actions).includes("{action_name}")) {{
            this.#actions["{action_name}"] = [];
        }}
        
        if (!this.#actions["{action_name}"].includes(handler)) {{
            this.#actions["{action_name}"].push(handler);
        }}
        return this;
    }}
"""
        library += f"""}}

if (!Object.keys(window).includes('DMOD')) {{
    window.DMOD = {{}};
}}

if (!Object.keys(window.DMOD).includes('clients')) {{
    window.DMOD.clients = {{}};
}}

window.DMOD.clients.{cls.get_client_name()} = {cls.get_client_name()};
window.DMOD.clients.{cls.get_client_name()}Options = {cls.get_client_name()}Options;
"""
        return library

    @classmethod
    def build_code(cls, language: str = None):
        # TODO: Add support for python
        if language is None:
            language = SUPPORTED_LANGUAGES.javascript

        if not SUPPORTED_LANGUAGES.is_supported(language):
            raise ValueError(
                f"'{language}' is not a supported language - code cannot be generated. "
                f"Supported languages are: {','.join(SUPPORTED_LANGUAGES.all())}"
            )

        if language == SUPPORTED_LANGUAGES.javascript:
            return cls.build_javascript()

        raise Exception(
            f"Functionality used to build a client library for {cls.__name__} has not been implemented "
            f"despite being supported."
        )