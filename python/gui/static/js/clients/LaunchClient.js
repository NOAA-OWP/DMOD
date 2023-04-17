/**
 * Generated module used to send formatted requests through a web socket
 * Generated at: 2023-04-11 04:00:51 PM CDT
 */

/**
 * @typedef {Object} ActionParameters
 * @description Result data from a server action
 * @property {string} event
 * @property {string} type
 * @property {Object} data
 * @property {String} time
 */

 /**
  * @typedef {(response: ActionParameters, socket: WebSocket) => any} ActionHandler
  * @description A function that can handle events from the client
  */

/**
 * @typedef {(MessageEvent) => any} SocketHandler
 * @description A function that can serve as an event handler for raw websocket messages
 */

/**
 * @typedef {function(string, Object<string, any>?): Error} ExceptionConstructor
 * @description A constructor for a specialized type of error
 */

/**
 * @typedef {(string) => any} ClientErrorHandler
 * @description A function that accepts an error message and an optional function (such as an exception constructor)
 */

/**
 *
 * @param {Array|Object} obj The object to convert to JSON
 * @returns {string}
 */
function toJSON(obj) {
    return JSON.stringify(obj, null, 4);
}

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
 * @param {Number?} iterations The number of blocks to iteratively add to the ID
 * @returns {string}
 */
function generateID(iterations) {
    let IDParts = [];

    iterations = typeof iterations === 'number' ? iterations : 2;

    for (let iterationIndex = 0; iterationIndex < iterations; iterationIndex++) {
        // Random text:
        let idPart = Math.random().toString(36);

        // The above call will return something like '0.7ytgv08253s'.
        // Take everything after the '.' to get the reasonable string
        idPart = idPart.substring(2);
        IDParts.push(idPart);
    }

    return IDParts.join("-");
}

export class LaunchClientError extends Error {}

export class LaunchClientOptions {
    /**
     * A collection of handlers that a client will call when the 'onmessage' event is triggered
     * @type {ActionHandler[]}
     */
    #onmessageHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onerror' event is triggered
     * @type {SocketHandler[]}
     */
    #onSocketErrorHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onopen' event is triggered
     * @type {SocketHandler[]}
     */
    #onopenHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onclose' event is triggered
     * @type {SocketHandler[]}
     */
    #oncloseHandlers = [];

    /**
     * Independent handlers for onmessage event types
     * @type {Object<string, ActionHandler[]>}
     */
    #actions = {};

    /**
     * The maximum number of times to try to reconnect before quiting
     * @type {number}
     */
    #maximumReconnectAttempts = 0;

    /**
     * Whether the client should attempt to reconnect if it gets disconnected
     * @type {boolean}
     */
    #shouldReconnect = false;

    /**
     * Handlers for errors that might occur within the client itself
     * @type {ClientErrorHandler[]}
     */
    #clientErrorHandlers = [];

    /**
     * A collection of handlers that a client will call when the 'onmessage' event is triggered
     * @type {ActionHandler[]}
     */
    get onmessageHandlers() {
        return [...this.#onmessageHandlers]
    }

    /**
     * A collection of handlers that a client will call when the 'onerror' event is triggered
     * @type {SocketHandler[]}
     */
    get onSocketErrorHandlers() {
        return [...this.#onSocketErrorHandlers];
    }

    /**
     * Handlers for errors that might occur within the client itself
     * @returns {ClientErrorHandler[]}
     */
    get clientErrorHandlers() {
        return [...this.#clientErrorHandlers];
    }

    /**
     * A collection of handlers that a client will call when the 'onopen' event is triggered
     * @type {SocketHandler[]}
     */
    get onopenHandlers() {
        return [...this.#onopenHandlers];
    }

    /**
     * A collection of handlers that a client will call when the 'onclose' event is triggered
     * @type {SocketHandler[]}
     */
    get oncloseHandlers() {
        return [...this.#oncloseHandlers];
    }

    /**
     * Independent handlers for onmessage event types
     * @type {Object<string, ActionHandler[]>}
     */
    get actions() {
        const copiedActions = {};

        for (let [actionName, configuredActions] of Object.entries(this.#actions)) {
            copiedActions[actionName] = Array.isArray(configuredActions) ? [...configuredActions] : [];
        }

        return copiedActions;
    }

    /**
     * Add a handler that will be called when the socket fires the `onmessage` event
     * @param {ActionHandler} handler The handler function that will be called
     * @returns {LaunchClientOptions} This set of options
     */
    addMessageHandler = (handler) => {
        this.#onmessageHandlers.push(handler);
        return this;
    }

    /**
     * Add a handler that will be called when the socket fires the `onopen` event
     * @param {SocketHandler} handler The handler function that will be called
     * @returns {LaunchClientOptions} This set of options
     */
    addOpenHandler = (handler) => {
        this.#onopenHandlers.push(handler);
        return this;
    }

    /**
     * Add a handler that will be called when the socket fires the `onclose` event
     * @param {SocketHandler} handler The handler function that will be called
     * @returns {LaunchClientOptions} This set of options
     */
    addCloseHandler = (handler) => {
        this.#oncloseHandlers.push(handler);
        return this;
    }

    /**
     * Add a handler that will be called when the socket fires the `onerror` event
     * @param {SocketHandler} handler The handler function that will be called
     * @returns {LaunchClientOptions} This set of options
     */
    addSocketErrorHandler = (handler) => {
        this.#onSocketErrorHandlers.push(handler);
        return this;
    }

    /**
     * Add a handler that will be called when the client itself encounters an error
     * @param {ClientErrorHandler} handler
     * @returns {LaunchClientOptions}
     */
    addClientErrorHandler = (handler) => {
        this.#clientErrorHandlers.push(handler);
        return this;
    }

    /**
     * Add a handler that will be called when the socket fires the `onmessage` event
     * @param {string} actionName The name of the event that should trigger this function
     * @param {ActionHandler} handler The handler function that will be called
     * @returns {LaunchClientOptions} This set of options
     */
    addActionHandler = (actionName, handler) => {
        if (!Object.keys(this.#actions).includes(actionName)) {
            this.#actions[actionName] = [];
        }

        this.#actions[actionName].push(handler);
        return this;
    }

    get maximumReconnectAttempts() {
        return this.#maximumReconnectAttempts;
    }

    /**
     *
     * @param {number} attempts
     */
    set maximumReconnectAttempts(attempts) {
        this.#maximumReconnectAttempts = Math.min(attempts, 0);
    }

    get shouldReconnect() {
        return this.#shouldReconnect;
    }

    setShouldReconnect(shouldAttempt) {
        if (typeof shouldAttempt !== "boolean") {
            throw new LaunchClientError("LaunchClientOptions.shouldReconnect may only be `true` or `false`");
        }

        this.#shouldReconnect = shouldAttempt;
        return this;
    }
}

/**
 * Web Socket consumer that forwards messages to and from redis PubSub
 */
export class LaunchClient {
    /**
     * The maximum number of times to try to reconnect before quiting
     * @type {number}
     */
    #maximumReconnectAttempts = 0;

    /**
     * Whether the client should attempt to reconnect if it gets disconnected
     * @type {boolean}
     */
    #shouldReconnect = false;

    /**
     * The current number of times that a reconnection has been attempted
     * @type {number}
     */
    #reconnectAttemptCount = 0;

    /**
     * The URL to the service
     * @type {string|null}
     */
    #url = null;

    /**
     * The WebSocket through which communication flows to and fro
     * @type {WebSocket}
     */
    #socket = null;

    /**
     * Independent handlers for onmessage event types
     * @type {Object<string, ActionHandler[]>}
     */
    #actions = {};

    /**
     * Handlers that will be called when the socket receives a message
     * @type {ActionHandler[]}
     */
    #onmessageHandlers = [];

    /**
     * Handlers that will be called when the socket receives an  error
     * @type {ActionHandler[]}
     */
    #onSocketErrorHandlers = [];

    /**
     * Handlers for errors that might arise within the client itself
     * @type {ClientErrorHandler[]}
     */
    #clientErrorHandlers = [];

    /**
     * Handlers that will be called when the socket connection is opened
     * @type {ActionHandler[]}
     */
    #onOpenHandlers = [];

    /**
     * Handlers that will be called when the socket connection is closed
     * @type {ActionHandler[]}
     */
    #onCloseHandlers = [];

    /**
     * Flag stating whether 'attachHandlers' has been called. Calling it multiple times will break how events are
     * handled by feeding the wrong parameters to the wrong functions
     * @type {boolean}
     */
    #addedWrapperHandlers = false;

    /**
     * A mapping of functions to their request IDs. If a response comes in with a matching ID,
     * the matching callback(s) will be used instead of the default or configured handlers and removed from the map
     * @type {Object<string, ActionHandler[]>}
     */
    #callbacks = {};

    constructor(socketOrAddress, options) {
        this.#applyOptions(options);
        if (typeof socketOrAddress === 'string') {
            this.#url = socketOrAddress;
            this.#socket = new WebSocket(socketOrAddress);
        }
        else {
            this.#socket = socketOrAddress;
        }
        this.attachHandlers();
    }

    /**
     * Apply options provided by the constructor
     *
     * @param {LaunchClientOptions|Object} options
     */
    #applyOptions(options) {
        if (options == null) {
            return;
        }

        if ("onmessageHandlers" in options) {
            this.#onmessageHandlers = options.onmessageHandlers;
        }

        if ("onSocketErrorHandlers" in options) {
            this.#onSocketErrorHandlers = options.onSocketErrorHandlers;
        }

        if ("onopenHandlers" in options) {
            this.#onOpenHandlers = options.onopenHandlers;
        }

        if ("oncloseHandlers" in options) {
            this.#onCloseHandlers = options.oncloseHandlers;
        }

        if ("clientErrorHandlers" in options) {
            this.#clientErrorHandlers = options.clientErrorHandlers;
        }

        if ("actions" in options) {
            this.#actions = options.actions;
        }

        if ("maximumReconnectAttempts" in options) {
            this.#maximumReconnectAttempts = options.maximumReconnectAttempts;
            this.#shouldReconnect = options.maximumReconnectAttempts > 0;
        }

        if ("shouldReconnect" in options) {
            this.#shouldReconnect = options.shouldReconnect;
        }
    }

    /**
     * Attach a new onmessage handler to this client's web socket that will call all registered handlers
     *
     * If the socket already has an `onmessage` handler, it will be called from within the new handler
     */
    attachHandlers = () => {
        if (this.#addedWrapperHandlers) {
            this.handleError("Handlers on this LaunchClient instance have already been attached");
        }

        this.#socket['overriddenOnMessageFunction'] = this.#socket.onmessage != null ? this.#socket.onmessage : (_) => null;

        this.#socket.onmessage = (response) => {
            if (Object.keys(this.#socket).includes('overriddenOnMessageFunction')) {
                this.#socket['overriddenOnMessageFunction'](response);
            }

            if (!("data" in response)) {
                if (this.#onmessageHandlers.length > 0) {
                    console.warn("Cannot call registered 'onmessage' handlers - no data payload was received")
                }
                return;
            }

            /**
             * The data formed on the server
             * @type {ActionParameters}
             */
            const actionParameters = JSON.parse(response.data);

            for (let handler of this.#onmessageHandlers) {
                handler(actionParameters, this.#socket);
            }

            if ("request_id" in actionParameters && actionParameters["request_id"] in this.#callbacks) {
                this.#callbacks[actionParameters['request_id']].forEach(
                    handler => handler(actionParameters, this.#socket)
                );
                delete this.#callbacks[actionParameters['request_id']];
                return;
            }

            let event = "";

            if (Object.keys(actionParameters).includes("event")) {
                event = actionParameters.event;
            }

            if (Object.keys(this.#actions).includes(event)) {
                this.#actions[event].forEach(handler => handler(actionParameters, this.#socket));
            }
        };

        this.#socket['overriddenOnOpenFunction'] = this.#socket.onopen != null ? this.#socket.onopen : (_) => null;

        this.#socket.onopen = (response) => {
            if (Object.keys(this.#socket).includes('overriddenOnOpenFunction')) {
                this.#socket['overriddenOnOpenFunction'](response);
            }

            for (let handler of this.#onOpenHandlers) {
                handler(response);
            }
        }

        this.#socket['overriddenOnCloseFunction'] = this.#socket.onclose != null ? this.#socket.onclose : (_) => null;

        this.#socket.onclose = (response) => {
            if (Object.keys(this.#socket).includes('overriddenOnCloseFunction')) {
                this.#socket['overriddenOnCloseFunction'](response);
            }

            for (let handler of this.#onCloseHandlers) {
                handler(response);
            }
        }

        this.#socket['overriddenOnErrorFunction'] = this.#socket.onerror != null ? this.#socket.onerror : (_) => null;

        this.#socket.onerror = (response) => {
            if (Object.keys(this.#socket).includes('overriddenOnErrorFunction')) {
                this.#socket['overriddenOnErrorFunction'](response);
            }

            for (let handler of this.#onSocketErrorHandlers) {
                handler(response);
            }
        }


        this.#addedWrapperHandlers = true;
    }

    /**
     * Reconnect the socket
     * @param {string?} url
     * @param {boolean?} fromClose
     * @returns {boolean} true if the connection was reestablished, false otherwise
     */
    reconnect = async (url, fromClose) => {
        const serviceURL = url || this.#url;

        if (!serviceURL) {
            this.handleError("A URL is required to reconnect to the service but none was provided.");
        }

        this.#reconnectAttemptCount = 0;

        const allowedToReconnect = !fromClose || this.#shouldReconnect;

        let maximumAttempts = this.#maximumReconnectAttempts;

        if (allowedToReconnect && maximumAttempts === 0) {
            maximumAttempts = 5;
        }

        let attemptsAreLeft = this.#reconnectAttemptCount < maximumAttempts;
        let hasNoSocket = this.#socket == null || this.#socket.readyState > 1;

        while (allowedToReconnect && hasNoSocket && attemptsAreLeft) {
            this.#reconnectAttemptCount++;

            try {
                this.#socket = new WebSocket(serviceURL);
                this.#addedWrapperHandlers = false;
                this.#url = serviceURL;
                this.attachHandlers();
            } catch (error) {
                let errorMessage = `Reconnection attempt #${this.#reconnectAttemptCount} failed. ${error}.`;

                if (this.#reconnectAttemptCount < this.#maximumReconnectAttempts) {
                    errorMessage += " Trying again...";
                }
                else {
                    errorMessage += " No more attempts left.";
                }

                this.handleError(errorMessage, null, false);

                // Wait 500ms before attempting to connect again
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            attemptsAreLeft = this.#reconnectAttemptCount < maximumAttempts;
            hasNoSocket = this.#socket == null || this.#socket.readyState > 1;
        }

        return this.#socket == null || this.#socket.readyState > 1;
    }

    /**
     * Add a handler for a specific type of server response
     * @param {string} actionName
     * @param {ActionHandler} handler
     * @returns {LaunchClient} This client
     */
    on = (actionName, handler) => {
        if (actionName == null || actionName === '' || typeof actionName !== 'string') {
            this.handleError("Cannot assign a new action handler - a valid action name was not provided");
        }
        if (typeof handler !== 'function') {
            this.handleError(
                `Cannot assign a handler for the '${actionName}' event - the handler wasn't valid`
            );
        }

        if (!(actionName in this.#actions)) {
            this.#actions[actionName] = [];
        }

        this.#actions[actionName].push(handler);
        return this;
    }

    /**
     * Handles errors that arise from within the client
     * @param {string} message
     * @param {(function(string, Object<string, any>?): Error)?} exceptionConstructor
     * @param {boolean?} throwError
     */
    handleError = (message, exceptionConstructor, throwError) => {
        if (throwError == null) {
            throwError = true;
        }

        let initialError = null;

        for (let handler of this.#clientErrorHandlers) {
            try {
                handler(message);
            } catch(error) {
                if (initialError == null) {
                    initialError = error;
                    continue
                }

                let oldError = initialError;

                if (error instanceof Error) {
                    initialError = new LaunchClientError(error.message);
                }
                else {
                    initialError = new LaunchClientError(error);
                }

                initialError.cause = oldError;
            }
        }

        if (throwError) {
            if (exceptionConstructor == null) {
                exceptionConstructor = error => new LaunchClientError(error);
            }

            throw exceptionConstructor(message);
        }
    }

    /**
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    generateLibrary = (optionalParameters, callbacks) => {
        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "generate_library",
            "action_parameters": {
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'generate_library'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'generate_library' event is received
     */
    onGenerateLibrary = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'generate_library' event."
            );
        }
        if (!Object.keys(this.#actions).includes("generate_library")) {
            this.#actions["generate_library"] = [];
        }

        if (!this.#actions["generate_library"].includes(handler)) {
            this.#actions["generate_library"].push(handler);
        }
    }

    /**
     * Sends a detailed listing of all possible actions and their required parameters through the socket
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getActions = (optionalParameters, callbacks) => {
        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_actions",
            "action_parameters": {
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_actions'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_actions' event is received
     */
    onGetActions = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_actions' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_actions")) {
            this.#actions["get_actions"] = [];
        }

        if (!this.#actions["get_actions"].includes(handler)) {
            this.#actions["get_actions"].push(handler);
        }
    }

    /**
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getAllTemplates = (optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_all_templates",
            "action_parameters": {
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_all_templates'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_all_templates' event is received
     */
    onGetAllTemplates = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_all_templates' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_all_templates")) {
            this.#actions["get_all_templates"] = [];
        }

        if (!this.#actions["get_all_templates"].includes(handler)) {
            this.#actions["get_all_templates"].push(handler);
        }
    }

    /**
     * @param {Number} identifier
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getSavedDefinition = (identifier, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_saved_definition",
            "action_parameters": {
                "identifier": identifier,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_saved_definition'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_saved_definition' event is received
     * @returns {LaunchClient} This client
     */
    onGetSavedDefinition = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_saved_definition' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_saved_definition")) {
            this.#actions["get_saved_definition"] = [];
        }

        if (!this.#actions["get_saved_definition"].includes(handler)) {
            this.#actions["get_saved_definition"].push(handler);
        }
        return this;
    }

    /**
     * @param {String} specification_type
     * @param {String} name
     * @param {String} author
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getTemplate = (specification_type, name, author, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_template",
            "action_parameters": {
                "specification_type": specification_type,
                "name": name,
                "author": author,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_template'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_template' event is received
     * @returns {LaunchClient} This client
     */
    onGetTemplate = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_template' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_template")) {
            this.#actions["get_template"] = [];
        }

        if (!this.#actions["get_template"].includes(handler)) {
            this.#actions["get_template"].push(handler);
        }
        return this;
    }

    /**
     * @param {Number} template_id
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getTemplateById = (template_id, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_template_by_id",
            "action_parameters": {
                "template_id": template_id,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_template_by_id'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_template_by_id' event is received
     * @returns {LaunchClient} This client
     */
    onGetTemplateById = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_template_by_id' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_template_by_id")) {
            this.#actions["get_template_by_id"] = [];
        }

        if (!this.#actions["get_template_by_id"].includes(handler)) {
            this.#actions["get_template_by_id"].push(handler);
        }
        return this
    }

    /**
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getTemplateSpecificationTypes = (optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_template_specification_types",
            "action_parameters": {
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_template_specification_types'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_template_specification_types' event is received
     * @returns {LaunchClient} This client
     */
    onGetTemplateSpecificationTypes = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_template_specification_types' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_template_specification_types")) {
            this.#actions["get_template_specification_types"] = [];
        }

        if (!this.#actions["get_template_specification_types"].includes(handler)) {
            this.#actions["get_template_specification_types"].push(handler);
        }

        return this;
    }

    /**
     * @param {String} specification_type
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    getTemplates = (specification_type, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "get_templates",
            "action_parameters": {
                "specification_type": specification_type,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'get_templates'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'get_templates' event is received
     * @returns {LaunchClient} This client
     */
    onGetTemplates = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'get_templates' event."
            );
        }
        if (!Object.keys(this.#actions).includes("get_templates")) {
            this.#actions["get_templates"] = [];
        }

        if (!this.#actions["get_templates"].includes(handler)) {
            this.#actions["get_templates"].push(handler);
        }

        return this;
    }

    /**
     * Launch an evaluation
     * @param {String} evaluation_name
     * @param {String} instructions
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    launch = (evaluation_name, instructions, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "launch",
            "action_parameters": {
                "evaluation_name": evaluation_name,
                "instructions": instructions,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'launch'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'launch' event is received
     * @returns {LaunchClient} This client
     */
    onLaunch = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'launch' event."
            );
        }
        if (!Object.keys(this.#actions).includes("launch")) {
            this.#actions["launch"] = [];
        }

        if (!this.#actions["launch"].includes(handler)) {
            this.#actions["launch"].push(handler);
        }

        return this;
    }

    /**
     * Saves the configured evaluation for later use
     * @param {String} name
     * @param {String} description
     * @param {String} author
     * @param {String} instructions
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    save = (name, description, author, instructions, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "save",
            "action_parameters": {
                "name": name,
                "description": description,
                "author": author,
                "instructions": instructions,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'save'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'save' event is received
     * @returns {LaunchClient} This client
     */
    onSave = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'save' event."
            );
        }
        if (!Object.keys(this.#actions).includes("save")) {
            this.#actions["save"] = [];
        }

        if (!this.#actions["save"].includes(handler)) {
            this.#actions["save"].push(handler);
        }
        return this;
    }

    /**
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    search = (optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "search",
            "action_parameters": {
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'search'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'search' event is received
     * @returns {LaunchClient} This client
     */
    onSearch = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'search' event."
            );
        }
        if (!Object.keys(this.#actions).includes("search")) {
            this.#actions["search"] = [];
        }

        if (!this.#actions["search"].includes(handler)) {
            this.#actions["search"].push(handler);
        }
        return this;
    }

    /**
     * Subscribe to a redis channel
     * @param {String} evaluation_name
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    subscribeToChannel = (evaluation_name, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "subscribe_to_channel",
            "action_parameters": {
                "evaluation_name": evaluation_name,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'subscribe_to_channel'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'subscribe_to_channel' event is received
     * @returns {LaunchClient} This client
     */
    onSubscribeToChannel = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'subscribe_to_channel' event."
            );
        }
        if (!Object.keys(this.#actions).includes("subscribe_to_channel")) {
            this.#actions["subscribe_to_channel"] = [];
        }

        if (!this.#actions["subscribe_to_channel"].includes(handler)) {
            this.#actions["subscribe_to_channel"].push(handler);
        }

        return this;
    }

    /**
     * @param {String} configuration
     * @param {Object<string, any>?} optionalParameters Optional Parameters
     * @param {(ActionHandler|ActionHandler[])?} callbacks
     **/
    validateConfiguration = (configuration, optionalParameters, callbacks) => {

        const requestID = generateID();

        if (callbacks != null) {
            if (!Array.isArray(callbacks)){
                callbacks = [callbacks];
            }

            this.#callbacks[requestID] = callbacks;
        }

        const payload = {
            "action": "validate_configuration",
            "action_parameters": {
                "configuration": configuration,
                "request_id": requestID,
                ...optionalParameters
            }
        }
        this.#socket.send(toJSON(payload));
    }

    /**
     * Add a handler that will be called when a message comes through the socket with the event 'validate_configuration'
     *
     * The `addHandler` function must be called for the added handler to be called
     *
     * @param {(ActionParameters) => any} handler A handler that will be called when the 'validate_configuration' event is received
     * @returns {LaunchClient} This client
     */
    onValidateConfiguration = (handler) => {
        if (!this.#addedWrapperHandlers) {
            this.handleError(
                "The `addHandler` function must be called on this `LaunchClient` instance in order to register a handler for the 'validate_configuration' event."
            );
        }
        if (!Object.keys(this.#actions).includes("validate_configuration")) {
            this.#actions["validate_configuration"] = [];
        }

        if (!this.#actions["validate_configuration"].includes(handler)) {
            this.#actions["validate_configuration"].push(handler);
        }

        return this;
    }
}

if (!Object.keys(window).includes('DMOD')) {
    window.DMOD = {};
}

if (!Object.keys(window.DMOD).includes('clients')) {
    window.DMOD.clients = {};
}

window.DMOD.clients.LaunchClient = LaunchClient;
window.DMOD.clients.LaunchClientOptions = LaunchClientOptions;