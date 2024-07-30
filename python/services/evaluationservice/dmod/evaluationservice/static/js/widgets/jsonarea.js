/**
 * Fetches the root editor namespace
 *
 * A namespace is created if it doesn't exist
 *
 * @param {(string|string[])?} path The path to namespace to make sure it exists
 * @param {string?} separator A character that may be used to separate parts of a path. Defaults to '/'
 * @return {object} The desired namespace
 */
function ensureNamespaceExists(path, separator) {
    let namespace = window;

    if (separator === null || separator === undefined) {
        separator = "/";
    } else if (typeof(separator) !== 'string') {
        throw new Error(`An object of type "${typeof(separator)}" may not be used as a path separator`);
    }

    if (path === null || path === undefined) {
        path = ['editors'];
    } else if (typeof(path) === "string") {
        path = path.trim().split(separator)
    } else if (!Array.isArray(path)) {
        throw new Error(`A "${typeof(path)}" object cannot be used to find and or create a namespace`);
    }

    let firstPart = true;
    for (let part of path) {
        if (firstPart && ["#", "$"].includes(part)) {
            continue;
        }

        firstPart = false;

        if (part === '' || part === null || part === undefined) {
            continue
        }

        if (namespace.hasOwnProperty(part)) {
            namespace = namespace[part];
        } else {
            namespace[part] = {};
            namespace = namespace[part];
        }
    }

    return namespace;
}

/**
 * Get data associated with a JSON editor
 *
 * @param {string} editorName The name of the field the editor edits
 * @param {(string|string[])?} path The path to the desired namespace
 * @param {string?} separator A character to use to separate parts of the given path. Defaults to '/'
 * @return {object|null}
 */
function getEditorData(editorName, path, separator) {
    const namespace = ensureNamespaceExists(path, separator)

    if (editorName in namespace && 'data' in namespace[editorName]) {
        return namespace[editorName]['data'];
    }

    return null;
}

/**
 * Get the actual editor object associated with an editor name
 *
 * @param {string} editorName The name of the editor To find
 * @param {(string|string[])?} path The path to the desired namespace
 * @param {string?} separator A character that may be used to separate parts of a path. Defaults to '/'
 * @return {object|null}
 */
function getEditor(editorName, path, separator) {
    const namespace = ensureNamespaceExists(path, separator);

    if (editorName in namespace && "editor" in namespace[editorName]) {
        return namespace[editorName].editor;
    }

    return null;
}

/**
 * Assign an event handler to a DOM element with nothing but strings
 * @param {string} selector A CSS selector used to find an element to attach an event handler to
 * @param {string} eventName The event to handle
 * @param {string|string[]} functionName The name or path to a function to act as a handler for the element's event
 */
function assignEventHandler(selector, eventName, functionName) {
    if ($ === undefined) {
        $ = django.jQuery;
    }

    let func;

    if (functionName in window) {
        func = window[functionName];
    } else if (typeof(functionName) === "string" && functionName.includes(".")) {
        functionName = functionName.split(".");
    } else if (!Array.isArray(functionName)) {
        functionName = [functionName]
    }

    if (func === undefined) {
        let space = window;

        for (let part of functionName) {
            if (part in space || space.includes(part)) {
                space = space[part];
            } else {
                throw new Error(
                    `No event handler could be found at "${functionName.join('.')}". ` +
                    `A handler cannot be attached to the "${eventName}" event.`
                );
            }

            if (!["function", "object"].includes(typeof(space))) {
                throw new Error(
                    `"${functionName.join('.')}" does not lead to a function or indexible object. ` +
                    `The '${eventName}' event may not be handled.`
                );
            }
        }

        if (typeof(space) !== 'function') {
            throw new Error(
                `"${functionName.join('.')}" is not a function and may not be used as an event handler. ` +
                `A handler cannot be attached to the "${eventName}" event.`
            );
        }

        func = space;
    }

    $(selector).on(eventName, func);
}


/**
 * Enable all save buttons
 */
function enableSave() {
    const saveButtons = django.jQuery("input[value*=Save]");
    saveButtons.prop("disabled", false);
}

/**
 * Disable all Save Buttons
 */
function disableSave() {
    const saveButtons = django.jQuery("input[value*=Save]");
    saveButtons.prop("disabled", true);
}

/**
 * Find a child within an object given a path
 *
 * @param {object} obj The object to traverse
 * @param {string|string[]} path The path to the desired value
 * @param {boolean?} allowMissingEntry  Whether to record a missing path entry as an error or to throw an error
 * @param {string?} separator A character that may be used to separate parts of a path. Defaults to '/'
 * @return {*}
 */
function followSchemaPath(obj, path, allowMissingEntry, separator) {
    let currentObject = obj;

    if (separator === null || separator === undefined) {
        separator = "/";
    } else if (typeof(separator) !== 'string') {
        throw new Error(`An object of type "${typeof(separator)}" may not be used as a path separator`);
    }

    if (allowMissingEntry === null || allowMissingEntry === undefined) {
        allowMissingEntry = false;
    }

    if (!Array.isArray(path)) {
        path = path.split(separator)
    }

    for (let part of path) {
        if (part === "#" || part === "$" || part.length === 0) {
            continue;
        }

        if (currentObject.hasOwnProperty(part) || part in currentObject) {
            currentObject = currentObject[part];
        } else {
            const message = `"${path.join('/')}" cannot be used to find data within a given object.`;
            if (allowMissingEntry) {
                console.error(message);
                return {};
            } else {
                throw new Error(message);
            }
        }
    }

    return currentObject;
}

/**
 * Look at received data to see how it should be interpreted from the point of view of a schema
 *
 * @param {object} fieldInformation Details on what type of value should be generated
 * @param {object} definitionsRoot An object that may contain definitions for nested and defined objects
 * @param {boolean?} allowMissingEntry Whether to record a missing path entry as an error or to throw an error
 * @return {(object|string|Array|Number|null)} A value generated that matches the requirements from the fieldInformation
 */
function getValueFromFieldInformation(fieldInformation, definitionsRoot, allowMissingEntry) {
    let value = null;

    if (allowMissingEntry === null || allowMissingEntry === undefined) {
        allowMissingEntry = false;
    }

    if (fieldInformation.hasOwnProperty("default")) {
        value = fieldInformation.default;
    } else if (fieldInformation.hasOwnProperty("enum") && fieldInformation.enum.length > 0) {
        value = fieldInformation.enum[0];
    } else {
        switch (fieldInformation.type) {
            case "array":
                value = [];
                if (fieldInformation.hasOwnProperty("items") && fieldInformation.items.hasOwnProperty("$ref")) {
                    value.push(
                        buildObjectFromSchema(
                            followSchemaPath(
                                definitionsRoot,
                                fieldInformation.items.$ref,
                                allowMissingEntry
                            ),
                            definitionsRoot,
                            allowMissingEntry
                        )
                    )
                }
                break;
            case "string":
                if (fieldInformation.hasOwnProperty("description")) {
                    value = fieldInformation.description;
                } else if (fieldInformation.hasOwnProperty("title")) {
                    value = fieldInformation.title;
                } else {
                    value = "string";
                }
                break;
            case 'number':
                // Just pick any number if it's supposed to be one
                value = 0;
                break;
            case 'object':
                // If it's supposed to be an object with no expectations, just add an empty object
                value = {};
                break;
            case "boolean":
                // Just pick any boolean value if it's supposed to be one
                value = false;
                break;
            case undefined:
                if (fieldInformation.hasOwnProperty("allOf")) {
                    value = [];
                    for (let subtype of fieldInformation.allOf) {
                        let data = buildObjectFromSchema(
                            followSchemaPath(
                                definitionsRoot,
                                subtype.$ref,
                                allowMissingEntry
                            ),
                            definitionsRoot
                        )
                        value.push(data);
                    }

                    if (value.length === 0) {
                        value = null;
                    } else if (value.length === 1) {
                        value = value[0];
                    }
                    break;
                } else if (fieldInformation.hasOwnProperty("anyOf")) {
                    let subInformation = fieldInformation.anyOf[0];
                    value = getValueFromFieldInformation(subInformation, definitionsRoot);
                }
        }
    }

    return value;
}

/**
 * Create an object based on a schema
 *
 * @param {object} schema
 * @param {object?} definitionsRoot
 * @param {boolean?} allowMissingEntry  Whether to record a missing path entry as an error or to throw an error
 * @return {object}
 */
function buildObjectFromSchema(schema, definitionsRoot, allowMissingEntry) {
    if (schema === null) {
        return {}
    }

    if (definitionsRoot === null || definitionsRoot === undefined) {
        definitionsRoot = schema;
        allowMissingEntry = true;
    }

    if (allowMissingEntry === null || allowMissingEntry === undefined) {
        allowMissingEntry = false;
    }

    let baseObject = {};

    // Fields in the schema will be under the 'properties' key. Iterate through and create a value for each
    // property to show an example for what is optional
    if (schema.hasOwnProperty("properties")) {
        for (let nameAndField of Object.entries(schema.properties)) {
            let fieldName = nameAndField[0];
            let field = nameAndField[1];

            let value = null;
            try {
                value = getValueFromFieldInformation(field, definitionsRoot, allowMissingEntry);
            } catch (e) {
                console.error(e);
            }
            baseObject[fieldName] = value;
        }
    }

    // If the generated value is an object, strip off any attribute whose value is null. That isn't a helpful value
    if (typeof(baseObject) === 'object') {
        baseObject = Object.fromEntries(
            Object.entries(baseObject).filter(
                ([key, value]) => value !== null
            )
        );
    }

    return baseObject;
}

/**
 * Get the amount and the unit from an attribute that may be measured
 * @param {string|HTMLElement} element The element that should have the attribute
 * @param {string} attributeName The attribute to measure
 * @param {(RegExp|string)?} unitRegex A regular expression that will indicate where the unit is so that the
 * @return {{amount: number, unit: string}}
 */
function measureAttribute(element, attributeName, unitRegex) {
    /**
     * A regex used to separate the amount determining the size of an object and the unit it is measured in
     */
    if (unitRegex === null || unitRegex === undefined) {
        unitRegex = /[a-zA-Z]+/;
    } else if (typeof(unitRegex) === 'string') {
        unitRegex = new RegExp(unitRegex);
    }

    if (typeof(element) == "string") {
        element = django.jQuery(element);
    }

    if (element === null || element === undefined || element.hasOwnProperty("length") && element.length === 0) {
        throw new Error("No element could be found to take a measure of");
    }

    const attributeValue = element.css(attributeName);

    if (attributeValue === null || attributeValue === undefined || attributeValue === "") {
        throw new Error(`No measurable attribute named '${attributeName}' could be found.`)
    } else if (attributeValue.search(/^-?[0-9]+\.?[0-9]*([a-zA-Z]+)?$/) < 0) {
        throw new Error(`"${attributeValue}" is not a measurable value`)
    }

    const unitIndex = attributeValue.search(unitRegex);

    let amount;
    let unit;

    if (unitIndex < 0) {
        let valueIndex = attributeValue.search(/^-?[.0-9]+$/);

        if (valueIndex >= 0) {
            amount = attributeValue * 1;
            unit = "";
        }
        else {
            throw new Error(`'${attributeValue}' could not be considered as a measured attribute`);
        }
    } else {
        amount = attributeValue.slice(0, unitIndex) * 1
        unit = attributeValue.slice(unitIndex)
    }

    return {
        amount: amount,
        unit: unit
    };
}

/**
 * Subtract the amount in the attribute
 * @param {{amount: number, unit: string}|number} accumulatedMeasurement The result of the subtracted measurements so far
 * @param {{amount: number, unit: string}} measurement The measurement to subtract from the accumulated measurement
 * @return {number}
 */
function subtractMeasurement(accumulatedMeasurement, measurement) {
    if (typeof(accumulatedMeasurement) === 'object') {
        return accumulatedMeasurement.amount - measurement.amount;
    }

    return accumulatedMeasurement - measurement.amount;
}

/**
 * Determine what the width attribute for a given error box should be to make sure that the element on screen
 * matches the width of the given editor
 *
 * @param {string|HTMLElement} editorElement The HTML element to use as the desired width.
 *                                           The element will be searched for if a string is passed
 * @param {string|HTMLElement} errorBoxElement The HTML element that needs to be resized.
 *                                             The element will be searched for if a string is passed
 * @param {(RegExp|string)?} unitRegex A regular expression used to separate an amount from a unit
 * @return {string} The desired css width value given as "<amount><unit>", like "500px"
 */
function getDesiredErrorBoxWidth(editorElement, errorBoxElement, unitRegex) {
    if (typeof(editorElement) === 'string') {
        editorElement = django.jQuery(editorElement);
    }

    if (typeof(errorBoxElement) === 'string') {
        errorBoxElement = django.jQuery(errorBoxElement);
    }

    if (unitRegex === null || unitRegex === undefined) {
        unitRegex = /[a-zA-Z]+/;
    } else if (typeof(unitRegex) === 'string') {
        unitRegex = new RegExp(unitRegex);
    }

    let measurements = [
        measureAttribute(editorElement, "width")
    ];

    // The formula needs to look like "box + border left + border right + padding right + padding left = editor width"
    // Since we don't know what the width of the box needs to be, get the widths of the other independent elements and
    // subtract them from the editor width
    const contributingErrorBoxFactors = [
        "border-left-width",
        "border-right-width",
        "padding-left",
        "padding-right"
    ];

    // Add a measurement entry for each of the defined contributing factors to the list
    measurements = measurements.concat(
        contributingErrorBoxFactors.map(
            (attributeName) => measureAttribute(errorBoxElement, attributeName, unitRegex)
        )
    )

    // Subtract each of the contributing factors from the expected width to find the desired width
    const width = measurements.reduce(subtractMeasurement);

    // Attach the calculated amount to the editor's unit to find the css value to return
    return width + measurements[0].unit;
}
