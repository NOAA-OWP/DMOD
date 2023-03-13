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