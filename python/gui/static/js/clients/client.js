import {toJSON} from "../utilities";

class HandlerStore {
    #receivedMessageHandlers = {};
    #openHandlers = {};
    #closeHandlers = {};
    #errorHandlers = {};
    /**
     * A mapping between events that the evaluation service triggers and its handler
     * @type {Object.<string, Object>}
     */
    #eventHandlerMap = {};

    addHandler(eventName, name, newHandler) {
        if (!this.#eventHandlerMap.hasOwnProperty(eventName)) {
            this.#eventHandlerMap[eventName] = {};
        }

        this.#eventHandlerMap[eventName][name] = newHandler;
    }

    removeHandler(eventName, name) {
        const hasEvent = this.#eventHandlerMap.hasOwnProperty(eventName);
        const hasHandler = hasEvent && this.#eventHandlerMap[eventName].hasOwnProperty(name);
        if (hasHandler) {
            delete this.#eventHandlerMap[eventName][name];
        }
    }

    #handleEvent(eventName, eventData) {
        const hasEvent = this.#eventHandlerMap.hasOwnProperty(eventName);
        const hasHandlers = hasEvent && Object.keys(this.#eventHandlerMap[eventName]).length > 0;
        if (hasHandlers) {
            for (let [name, handler] of Object.entries(this.#eventHandlerMap[eventName])) {
                try {
                    handler(eventData);
                } catch (exception) {
                    console.error(`Error encountered when calling the "${name}" handler for the "${eventName}" event:`);
                    console.error(exception);
                }
            }
        }
    }

    #handleSocketEvent(response, handlerMap) {
        for (let [name, handler] of Object.entries(handlerMap)) {
            try {
                handler(response);
            } catch(error) {
                console.error(`The message event handler named ${name} failed to complete.`);
                console.error(error);
            }
        }
    }
    #addSocketHandler(name, handler, handlerMap) {
        handlerMap[name] = handler;
    }

    #removeSocketHandler(name, handlerMap) {
        if (handlerMap.hasOwnProperty(name)) {
            delete handlerMap[name];
        }
    }

    onError(response) {
        this.#handleSocketEvent(response, this.#errorHandlers);
    }

    onOpen(response) {
        this.#handleSocketEvent(response, this.#openHandlers);
    }

    onClose(response) {
        this.#handleSocketEvent(response, this.#closeHandlers);
    }

    onMessage(response) {
        this.#handleSocketEvent(response, this.#receivedMessageHandlers);

        this.#handleEvent(response.event, response.data);
    }

    addReceivedMessageHandler(name, handler) {
        this.#addSocketHandler(name, handler, this.#receivedMessageHandlers);
    }

    removeReceivedMessageHandler(name) {
        this.#removeSocketHandler(name, this.#receivedMessageHandlers);
    }

    addOpenHandler(name, handler) {
        this.#addSocketHandler(name, handler, this.#openHandlers);
    }

    removeOpenHandler(name) {
        this.#removeSocketHandler(name, this.#openHandlers);
    }

    addErrorHandler(name, handler) {
        this.#addSocketHandler(name, handler, this.#errorHandlers);
    }

    removeErrorHandler(name) {
        this.#removeSocketHandler(name, this.#errorHandlers);
    }

    addCloseHandler(name, handler) {
        this.#addSocketHandler(name, handler, this.#closeHandlers);
    }

    removeCloseHandler(name) {
        this.#removeSocketHandler(name, this.#closeHandlers);
    }
}

export class BaseClient {
    #handlers = new HandlerStore();
    /**
     * A socket that will communicate with the evaluation service
     * @type {WebSocket}
     */
    #socket = null;
    #socketAddress = null;
    #connectionAttemptCount = 0;
    #connectionAttemptLimit = 5;
    #connectionWaitSeconds = 5;

    constructor(address) {
        this.#socketAddress = address;

        for (let [name, initializationFunction] of Object.entries(this.initialization_functions)) {
            try {
                initializationFunction();
            } catch (exception) {
                console.error(`Could not call the ${name} function when creating a new service client.`);
                console.error(exception);
            }
        }
    }

    createSocket() {
        return new WebSocket(this.#socketAddress);
    }

    connect(reset_attempts) {
        if (reset_attempts == null) {
            reset_attempts = true;
        }

        if (reset_attempts) {
            this.#connectionAttemptCount = 0;
        }

        if (this.#socket != null && this.#socket.readyState < 2) {
            this.#connectionAttemptCount = 0;
            return;
        }

        if (this.#connectionAttemptCount >= this.#connectionAttemptLimit) {
            console.error("Ran out of attempts to connect to the evaluation service. Call manually to try again.");
            return;
        }

        try {
            this.#socket = this.createSocket();
        } catch (error) {
            alert(error.message);
            this.#handlers.onError(error.message);
            this.#connectionAttemptCount += 1;

            setTimeout(
                this.connect,
                this.#connectionWaitSeconds * 1000,
                false
            );
            return;
        }

        this.#socket.onopen = this.#handlers.onOpen;
        this.#socket.onmessage = this.#handlers.onMessage;
        this.#socket.onerror = this.#handlers.onError;
        this.#socket.onclose = this.#handlers.onClose;

        this.#connectionAttemptCount = 0;
    }

    /**
     * Format arguments into an object that is accepted by the service
     *
     * Must be implemented by subclasses
     *
     * @param args The args given by callers
     * @returns {Object} A javascript Object that will be converted to JSON and sent to the service
     */
    formatRequest(...args) {
        throw Error("The 'formatRequest' function needs to be implemented on a subclass of the BaseClient");
    }

    submit(...args) {
        if (this.#socket == null || this.#socket.readyState > 1) {
            throw Error(
                "A message cannot be submitted through the client's web socket; it is not connected. Please reconnect"
            );
        }

        const message = this.formatRequest(...args)

        this.#socket.send(toJSON(message));
    }

    addReceivedMessageHandler(name, handler) {
        this.#handlers.addReceivedMessageHandler(name, handler);
    }

    removeReceivedMessageHandler(name) {
        this.#handlers.removeReceivedMessageHandler(name);
    }

    addOpenHandler(name, handler) {
        this.#handlers.addOpenHandler(name, handler);
    }

    removeOpenHandler(name, handler) {
        this.#handlers.removeOpenHandler(name);
    }

    addErrorHandler(name, handler) {
        this.#handlers.addErrorHandler(name, handler);
    }

    removeErrorHandler(name) {
        this.#handlers.removeErrorHandler(name);
    }

    addCloseHandler(name, handler) {
        this.#handlers.addCloseHandler(name, handler);
    }

    removeCloseHandler(name) {
        this.#handlers.removeCloseHandler(name);
    }

    on(eventName, name, handler) {
        this.#handlers.addHandler(eventName, name, handler);
    }

    off(eventName, name) {
        this.#handlers.removeHandler(eventName, name);
    }

    get EVENTS() {
        throw new Error("The 'EVENTS' getter needs to be implemented on a subclass of the BaseClient")
    }

    get ACTIONS() {
        throw new Error("The 'ACTIONS' getter needs to be implemented on a subclass of the BaseClient")
    }

    get initialization_functions() {
        return {};
    }
}

