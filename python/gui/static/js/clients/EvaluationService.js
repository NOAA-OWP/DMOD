import {BaseClient} from "/static/js/clients/client.js";

class EvaluationLaunchClient extends BaseClient {
    #actionDefinitions = {};
    get EVENTS() {
        return {
            SEARCH: "search",
            GET_SAVED_DEFINITION: "get_saved_definition",
            SAVE: "save",
            LOCATION_SCORES: "location_scores",
            LAUNCH: "launch",
            UPDATE: "update",
            INFO: "info",
            METRIC: "metric",
            CONNECT: "connect",
            CONNECT_TO_CHANNEL: "connect_to_channel",
            CROSSWALK: "crosswalk"
        }
    }

    get ACTIONS() {
        return {
            LAUNCH: "launch",
            SUBSCRIBE: "subscribe_to_channel",
            SEARCH: "search",
            GET_SAVED_DEFINITION: "get_saved_definition",
            GET_ACTIONS: "get_actions",
            SAVE: "save"
        }
    }

    formatRequest(action, parameters) {
        const validationMessages = this.#validateAction(action, parameters);

        if (validationMessages.length > 0) {
            const errorMessage = validationMessages.join("\n");
            throw new Error(errorMessage);
        }

        let callParameters = {
            "action": action
        }

        if (typeof parameters == 'object') {
            let copiedParameters = {};

            for (let [key, value] of Object.entries(parameters)) {
                copiedParameters[key] = value;
            }

            callParameters["action_parameters"] = copiedParameters;
        }

        return callParameters;
    }

    #validateAction(action, parameters) {
        if (Object.keys(this.#actionDefinitions).length === 0) {
            return [];
        }

        if (!this.#actionDefinitions.hasOwnProperty(action)){
            return [
                `"${action}" is not a valid action for the Evaluation Launch service`
            ];
        }

        const definition = this.#actionDefinitions[action];

        const validations = [];

        if (!this.#actionDefinitions.hasOwnProperty("action_parameters")) {
            return validations;
        }
        else if(Object.keys(this.#actionDefinitions.action_parameters).length === 0) {
            return validations;
        }

        for (let [parameterName, parameterType] of definition.action_parameters) {
            if (!parameters.hasOwnProperty(parameterName)) {
                validations.push(
                    `Arguments given for the "${action}" action are missing the required "${parameterName}" parameter`
                );

                continue;
            }
            const parameterValue = parameters[parameterName];
            if (parameterType === 'integer' && !Number.isInteger(parameterValue)) {
                validations.push(
                    `The "${parameterName}" parameter should be a(n) "${parameterType}", but a ` +
                    `"${typeof parameterValue}" was given instead`
                );
            }
            else if (parameterType === 'float' && typeof parameterValue !== "number") {
                validations.push(
                    `The "${parameterName}" parameter should be a(n) "${parameterType}", but a ` +
                    `"${typeof parameterValue}" was given instead`
                );
            }
            else if(typeof parameterValue !== parameterType) {
                validations.push(
                    `The "${parameterName}" parameter should be a(n) "${parameterType}", but a ` +
                    `"${typeof parameterValue}" was given instead`
                );
            }
        }

        return validations;
    }

    #loadActions(message) {
        const readActions = message.data;

        if (!Array.isArray(readActions)) {
            throw new Error(
                "Cannot load action definitions for the Evaluation Launch client - unexpected message data format. " +
                `Requests cannot be validated prior to sending. Expected an Array but received a ${typeof readActions}`
            );
        }

        for (let definition of readActions){
            this.#actionDefinitions[definition['action']] = definition;
        }
    }

    #askForActions() {
        let socket = null;
        try {
            socket = this.createSocket();
        } catch (exception) {
            console.error(
                "Could not create the socket necessary to ask the server what Evaluation Launch actions are available"
            );
            console.error(exception);
            return;
        }

        socket.onmessage = this.#loadActions;

        try {
            socket.send(JSON.stringify({"action": "get_actions"}));
        } catch (exception) {
            console.error("Could not ask the Evaluation Launch endpoint what actions are available");
            console.error(exception);
        }
    }

    get initialization_functions() {
        return {
            "askForActions": this.#askForActions
        };
    }
}