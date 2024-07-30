/**
 * Ensure that a given string is a valid URL
 * @param {String} url The URL to format
 * @return {null|undefined|string}
 */
export function toURL(url) {
    if (url == null || url === '' || typeof url != 'string') {
        return url;
    }

    let protocolMatcher = /^(s?ftp|https?|file|dns|geo|h323|imap|info|ldap|mailto|nfs|telnet|vnc|wss?|s3):\/\//g;
    if (!protocolMatcher.test(url)){
        url = `http://${protocolMatcher}`;
    }

    return url;
}

/**
 * Determines if a given string is a URL
 * @param {string} possibleURL
 */
export function isURL(possibleURL) {
    if (possibleURL == null || possibleURL === '' || typeof possibleURL != 'string') {
        return false;
    }

    possibleURL = toURL(possibleURL);

    try {
        new URL(possibleURL);
        return true;
    }
    catch {
        return false;
    }
}

/**
 * Convert a string to an email address if possible
 * @param {String} address The address to ensure is formatted as "mailto://address"
 * @return {string}
 */
export function toEmailAddress(address) {
    if (!isEmailAddress(address)) {
        return address;
    }

    return /^.+:\/\//g.test(address) ? address : `mailto://${address}`;
}

/**
 * Test whether a value could be an email address
 * @param {String} possibleEmailAddress A value that might be an email address
 * @return {Boolean}
 */
export function isEmailAddress(possibleEmailAddress) {
    if (possibleEmailAddress == null || possibleEmailAddress === '' || typeof possibleEmailAddress != 'string') {
        return false;
    }

    const emailExpression = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/gi;

    return emailExpression.test(possibleEmailAddress);
}

/**
 * Check whether a character represents an upper case letter
 * @param {String} character
 * @return {Boolean}
 */
export function characterIsUpperCaseLetter(character) {
    return typeof character === 'string' && /[A-Z]/g.test(character);
}

/**
 * Check whether a character represents a lower case letter
 * @param {String} character
 * @return {Boolean}
 */
export function characterIsLowerCaseLetter(character) {
    return typeof character === 'string' && /[a-z]/g.test(character);
}

/**
 * Check whether a character represents whitespace
 * @param {string} character
 * @return {Boolean}
 */
export function characterIsWhiteSpace(character) {
    return typeof character === 'string' && /[ \t\r\n]/i.test(character);
}

/**
 * Check whether a character is a number
 * @param character
 * @return {Boolean}
 */
export function characterIsDigit(character) {
    return typeof character === 'string' && "0123456789".includes(character);
}

/**
 * Formats the given string into User friendly text
 * @param {string} string
 * @return {string}
 */
export function cleanString(string) {
    if (string == null || string.length === 0) {
        return string;
    }

    string = string.trim();

    let stringParts = [];

    stringParts.push(string[0].toUpperCase());

    for (let letterIndex = 0; letterIndex < string.length - 1; letterIndex++) {
        const currentCharacter = string[letterIndex];
        const nextCharacter = string[letterIndex + 1];

        const currentCharacterIsWhitespace = characterIsWhiteSpace(currentCharacter);

        if (currentCharacterIsWhitespace) {
            stringParts.push(nextCharacter.toUpperCase());
            continue;
        }

        const nextCharacterIsWhiteSpace = characterIsWhiteSpace(nextCharacter);

        if (nextCharacterIsWhiteSpace) {
            stringParts.push(nextCharacter);
            continue;
        }

        const currentCharacterIsLowerCase = characterIsLowerCaseLetter(currentCharacter);
        const currentCharacterIsUpperCase = characterIsUpperCaseLetter(currentCharacter);
        const currentCharacterIsDigit = characterIsDigit(currentCharacter);
        const currentCharacterIsLetter = currentCharacterIsLowerCase || currentCharacterIsUpperCase;

        const nextCharacterIsLowerCase = characterIsLowerCaseLetter(nextCharacter);
        const nextCharacterIsUpperCase = characterIsUpperCaseLetter(nextCharacter);
        const nextCharacterIsDigit = characterIsDigit(nextCharacter);

        const nextCharacterIsLetter = nextCharacterIsLowerCase || nextCharacterIsUpperCase;

        if (currentCharacterIsLowerCase && nextCharacterIsUpperCase) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else if (currentCharacterIsLetter && nextCharacterIsDigit) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else if (currentCharacterIsDigit && nextCharacterIsLetter) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else {
            stringParts.push(nextCharacter.toLowerCase());
        }

    }

    return stringParts.join('').trim();
}

/**
 * Formats a string into
 * @param string
 * @return {String}
 */
export function toProgrammaticName(string){
    return string.replaceAll(
        /[` !@#$%^&*()+=\[\]{};':"\\|,.<>\/?~]/g,
        "_"
    ).replace(/_+/g, "_")
    .replaceAll(/ +/g, "-");
}

export function cssSizeToPixels(amount, unit, parent) {
    let convertedAmount = Number(amount);

    switch (unit.toLowerCase()) {
        case "em":
            break;
        case "%":
            break
        case "pt":
            break;
        default:
    }

    return convertedAmount;
}

/**
 * Retrieve a safe to use copy of the given value.
 *
 * Simple values like 'stuff' are safe to assign, but values like ['one', 'two', 'three'] aren't since later use
 * may mutate the earlier copy
 *
 * @example
 *      >>> let x = "stuff";
 *      >>> let y = ["one", "two", "three"];
 *      >>> let x2 = safeGet(x);
 *      >>> let y2 = safeGet(y);
 *      >>> x2 = x2 + "!";
 *      >>> y2.push(1);
 *      >>> console.log(x);
 *      stuff
 *      >>> console.log(x2);
 *      stuff!
 *      >>> console.log(y);
 *      ["one", "two", "three"]
 *      >>> console.log(y2);
 *      ["one", "two", "three", 1]
 *      >>> y.push(8);
 *      >>> console.log(y);
 *      ["one", "two", "three", 8]
 *      >>> console.log(y2);
 *      ["one", "two", "three", 1]
 *
 * @template T
 * @param {T} value
 * @return {T}
 */
export function safeGet(value) {
    if (value == null) {
        return null;
    }
    else if (Array.isArray(value)) {
        return value.map(x => safeGet(x));
    }
    else if (value.isPrototypeOf(Object)) {
        let copiedObject = {};

        for (let [key, entry] of Object.entries(value)) {
            copiedObject[key] = safeGet(entry);
        }

        value = copiedObject;
    }

    return value;
}

export function getWebSocketURL(url) {
    if (url.startsWith("ws://") || url.startsWith("wss://")) {
        return url;
    }

    if (!url.startsWith("/")) {
        url = `/${url}`;
    }
    const protocol = window.location.protocol.startsWith("https") ? "wss" : "ws";
    return `${protocol}://${window.location.host}${url}`;
}

export function getJSONReplacer() {
    return null;
}

export function getExpectedIndentSpaces() {
    return 4;
}

export function toJSON(obj) {
    return JSON.stringify(obj, getJSONReplacer(), getExpectedIndentSpaces());
}

export function downloadData(name, data) {
    if (typeof data != "string") {
        data = toJSON(data);
    }

    const fileType = "application/json";

    const file = new Blob([data], {type: fileType});
    const fileUrl = URL.createObjectURL(file);

    const fileAnchor = document.createElement("a");
    fileAnchor.href = fileUrl;
    fileAnchor.download = name;
    document.body.appendChild(fileAnchor);
    fileAnchor.click();

    setTimeout(function() {
        document.body.removeChild(fileAnchor);
        window.URL.revokeObjectURL(fileUrl);
    }, 0);
}

export async function getServerData(url, dataType) {
    if (dataType == null) {
        dataType = "json";
    }

    dataType = dataType.toLowerCase();

    const validDataTypes = ["blob", "json", "text", "buffer"];

    if (!validDataTypes.includes(dataType)) {
        throw new Error(
            `"${dataType}" is not a valid data type for server retrieval. Valid options are: ${validDataTypes.join(", ")}`
        );
    }

    return await fetch(url)
        .then(
            (response) => {
                if (dataType === "blob") {
                    return response.blob();
                }
                else if (dataType === "json") {
                    return response.json();
                }
                else if (dataType === "buffer") {
                    return response.arrayBuffer();
                }
                return response.text();
            }
        );
}

/**
 * Attach dynamic code to the document
 *
 * Dynamic code may come from a request of some sort
 *
 * WARNING: Be careful about what is calling this; there are no steps to protect the browser from malicious code
 *
 * @param {string} code The code to add
 * @param {string?} languageMIMEType What type of object to convert the following blob into. 'application/javascript' is fine 99% of the time.
 */
export function attachCode(code, languageMIMEType) {
    console.warn("Attaching dynamic code - be sure that the loaded code is safe to use");

    if (languageMIMEType == null || typeof languageMIMEType !== 'string' || languageMIMEType === '') {
        languageMIMEType = "application/javascript";
    }

    const script = new Blob([code], {type: languageMIMEType});
    const fileUrl = URL.createObjectURL(script);

    const scriptElement = document.createElement("script");
    scriptElement.type = "module";
    scriptElement.async = false;
    scriptElement.src = fileUrl;
    scriptElement.id = crypto.randomUUID();
    document.body.appendChild(scriptElement);

    console.info(`Dynamic code has been attached. It may be viewed at "script#${scriptID}"`);
}

/**
 * Short javascript equivalent of python's hasattr function
 *
 * Helps prevent issues that arise from calling `'memberName' in obj`
 *
 * @param {object} obj The object to check
 * @param {string} memberName The name of the property to look for
 * @returns {boolean} Whether the object has the property of interest
 */
export function hasAttr(obj, memberName) {
    return obj != null && memberName != null && typeof obj === 'object' && memberName in obj;
}

/**
 * Wait for the given WebSocket to pass the connecting phase
 *
 * @param {WebSocket} socket The websocket to wait on
 * @param {Number?} delay The number of milliseconds to wait before checking again
 * @returns {Promise<boolean>} Whether there is an active connection
 */
export async function waitForConnection(socket, delay) {
    const maximumNumberOfAttempts = 5;
    let numberOfAttempts = 0;

    const minimumWaitMilliseconds = 500;

    if (delay == null) {
        delay = minimumWaitMilliseconds;
    }
    else if (delay < minimumWaitMilliseconds) {
        console.warn(
            `The given delay is less than the minimum of ${minimumWaitMilliseconds}. Changing to the minimum milliseconds to wait: ${minimumWaitMilliseconds}ms`
        );
        delay = minimumWaitMilliseconds;
    }

    while (socket.readyState === 0 && numberOfAttempts < maximumNumberOfAttempts) {
        numberOfAttempts += 1;
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    return socket.readyState === 1;
}

export const INITIAL_DIGITS_PATTERN = /^[\d.]+/g

export function getStyleSize(element, styleName) {
    if (!(element instanceof jQuery)) {
        element = $(element);
    }

    let size = 0;

    let styleValue = element.css(styleName);

    if (styleValue) {
        const styleAmount = styleValue.match(INITIAL_DIGITS_PATTERN);

        if (styleAmount) {
            size = Number(styleAmount[0]);
        }
    }

    return size;
}

function combineUnitStrings(first, second, combiner) {
    if (combiner == null) {
        combiner = (x, y) => x + y;
    }
    first = first.trim();
    second = second.trim();

    const firstMatch = first.match(INITIAL_DIGITS_PATTERN);

    if (!firstMatch) {
        throw new Error(`Cannot add unit strings - '${first}' is not recognized as a unit string`);
    }

    const secondMatch = second.match(INITIAL_DIGITS_PATTERN);

    if (!secondMatch) {
        throw new Error(`Cannot add unit strings - '${second}' is not recognized as a unit string`);
    }

    const firstUnits = first.replaceAll(INITIAL_DIGITS_PATTERN, "").trim();
    const secondUnits = second.replaceAll(INITIAL_DIGITS_PATTERN, "").trim();

    if (!firstUnits && secondUnits) {
        throw new Error(`Cannot add unit strings - no units were detected in '${first}'`);
    }
    if (firstUnits && !secondUnits) {
        throw new Error(`Cannot add unit strings - no units were detected in '${second}'`);
    }

    if (firstUnits.toLowerCase() !== secondUnits.toLowerCase()) {
        throw new Error(`Cannot add unit strings - '${first}' and '${second}' appear to be in different units`);
    }

    const firstAmount = parseFloat(firstMatch[0]);
    const secondAmount = parseFloat(secondMatch[0]);

    return `${combiner(firstAmount, secondAmount)}${firstUnits}`;
}

/**
 * Add two strings representing an amount of units like '10px', '12rem', '5pt', '8', etc
 *
 * Units must be the same for each
 *
 * @param {string} first
 * @param {string} second
 */
export function addUnitStrings(first, second) {
    return combineUnitStrings(first, second);
}

/**
 * Subtract two strings representing an amount of units like '10px', '12rem', '5pt', '8', etc
 *
 * Units must be the same for each
 *
 * @param {string} first
 * @param {string} second
 */
export function subtractUnitStrings(first, second) {
    return combineUnitStrings(first, second, (x, y) => x - y);
}

/**
 * Get the total height of an HTML element
 *
 * Unreliable results will be returned if units are mixed between height, paddings, borders, and margins
 * @param {string|HTMLElement|jQuery} element
 * @returns {number}
 */
export function getElementHeight(element) {
    if (element == null) {
        return 0;
    }

    if (!(element instanceof jQuery)) {
        element = $(element);
    }

    if (element.length === 0 || !element.is(":visible") || element.is(":hidden")) {
        return 0;
    }

    let height = element.height();
    height += getStyleSize(element, "margin-top");
    height += getStyleSize(element, "margin-bottom");
    height += getStyleSize(element, "padding-bottom");
    height += getStyleSize(element, "padding-top");
    height += getStyleSize(element, "border-bottom-width");
    height += getStyleSize(element, "border-top-width");

    return height;
}

/**
 * Performs a recursive check to make sure two values are the same
 *
 * @example
 * let val1 = {"a": {"b": {"c": {"d": {"e": 42}}}}}
 * let val2 = {"a": {"b": {"c": {"d": {"e": 42}}}}}
 * let val3 = {"a": {"b": {"c": {"d": {"e": '42'}}}}}
 * let val4 = {"a": {"b": {"c": {"d": {"e": 43}}}}}
 *
 * deepEqual(val1, val2)
 * // returns true
 *
 * deepEqual(val1, val3)
 *
 * // returns false
 *
 * deepEqual(val1, val4)
 * // returns false
 *
 * @param first
 * @param second
 * @returns {boolean}
 */
export function deepEqual(first, second) {
  const keysOf = Object.keys;
  const firstType = typeof first;
  const secondType = typeof second;

  return first && second && firstType === 'object' && firstType === secondType ? (
    keysOf(first).length === keysOf(second).length &&
      keysOf(first).every(key => deepEqual(first[key], second[key]))
  ) : (first === second);
}

/**
 * Check to see if the structure of two objects match
 *
 * Two structures are considered the same if:
 *  - each have the same keys
 *  - single valued keys have the same value (i.e. not objects, arrays, but 'b' = 42)
 *  - complex types are the same types (i.e. both have to be arrays or both have to be objects)
 *
 *  The comparison is NOT recursive
 *
 * @example
 * let struct1 = {"a": 99, "b": {"c": "d"}}
 * let struct2 = {"a": 99, "b": {"e": "f"}}
 * let struct3 = {"a": 99, "b": 442}
 *
 * structuresMatch(struct1, struct2)
 * // returns true
 *
 * structuresMatch(struct1, struct3)
 * // returns false
 *
 * @param {Object} first
 * @param {Object} second
 * @returns {boolean}
 */
export function structuresMatch(first, second) {
    const firstType = typeof first;
    const secondType = typeof second;

    if (firstType !== 'object' || secondType !== 'object') {
        throw new Error(`"structuresMatch" may only compare two objects - received ${firstType} and ${secondType}`);
    }

    for (let [firstKey, firstValue] of Object.entries(first)) {
        let matchFound = false;

        for (let [secondKey, secondValue] of Object.entries(second)) {
            if (firstKey !== secondKey) {
                continue;
            }

            if (typeof firstValue !== typeof secondValue) {
                continue;
            }

            if (Array.isArray(firstValue) && Array.isArray(secondValue)) {
                matchFound = true;
                break;
            }
            else if (typeof firstValue === 'object' && typeof secondValue === 'object') {
                matchFound = true;
                break;
            }
            else if (firstValue === secondValue) {
                matchFound = true;
                break;
            }
        }

        if (!matchFound) {
            return false;
        }
    }

    return true;
}


/**
 * Updates a base object in place to contain the data from another object without overriding non-related data
 * @example
 * let base = {"a": {"b": {"c": {"d": 1}}}};
 * let data = {"a": {"b": {"c": {"e": 2}}}};
 * updateObject(base, data);
 * console.log(base);
 * // prints: {"a": {"b": {"c": {"d": 1, "e": 2}}}}
 *
 * @param {Object} base
 * @param {Object} data
 */
export function updateObject(base, data) {
    for (let [key, value] of Object.entries(data)) {
        if (!(key in base) || base[key] == null) {
            base[key] = value;
        }
        else if (value != null) {
            if (typeof base[key] === "object" && typeof value !== 'object') {
                throw new Error(
                    `Cannot update object - the ${key} value on the base and the ` +
                    `${key} value in the new data are not compatible`
                );
            }
            else if (typeof base[key] !== 'object' && typeof value === 'object') {
                throw new Error(
                    `Cannot update object - the ${key} value on the base and the ` +
                    `${key} value in the new data are not compatible`
                );
            }
            else if (Array.isArray(base[key]) && !Array.isArray(value)) {
                throw new Error(
                    `Cannot update object - the ${key} value on the base and the ` +
                    `${key} value in the new data are not compatible`
                );
            }
            else if (!Array.isArray(base[key]) && Array.isArray(value)) {
                throw new Error(
                    `Cannot update object - the ${key} value on the base and the ` +
                    `${key} value in the new data are not compatible`
                );
            }
            else if (Array.isArray(base[key]) && Array.isArray(value)) {
                for (let newEntry of value) {
                    const newEntryIsArray = Array.isArray(newEntry);
                    let entryFound = false;

                    if (!newEntryIsArray) {
                        const newEntryType = typeof newEntry;
                        for (let baseEntry of base[key]) {
                            const baseEntryType = typeof baseEntry;
                            const typesMatch = newEntryType === baseEntryType
                            const bothAreObjects = typesMatch && newEntryType === 'object';

                            if (Array.isArray(baseEntry)) {
                                continue
                            }

                            if (bothAreObjects && structuresMatch(newEntry, baseEntry)) {
                                updateObject(baseEntry, newEntry);
                                entryFound = true;
                                break;
                            } else if (newEntry === baseEntry) {
                                entryFound = true;
                                break;
                            }
                        }
                    }

                    if (!entryFound) {
                        base[key].push(newEntry);
                    }
                }
            }
            else if (typeof base[key] === 'object' && typeof value === 'object') {
                updateObject(base[key], value);
            }
            else {
                base[key] = value;
            }
        }
    }

    return base;
}

export class Enumeration {
    static get values() {
        const ownedProperties = Object.getOwnPropertyDescriptors(this);
        const entryPerProperty = Object.entries(ownedProperties);
        const propertyGetters = entryPerProperty.filter(
            ([name, entity]) => name !== 'values' && Object.hasOwn(entity, 'get') && typeof entity.get === 'function'
        );
        return propertyGetters.flatMap(([name, entity]) => this[name]);
    }

    static has(value) {
        return this.values.includes(value);
    }
}
