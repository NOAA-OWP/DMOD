// Functions to call when the page loads
const startupScripts = [];

// Handlers to call when the page is being resized
const resizeHandlers = [];

// Custom initialization functions for different widgets like tabs or buttons
const widgetInitializers = [];

// A common namespace for DMOD specific items used to prevent key collisions between browser and application values
window.DMOD = {};

// Modules that should be imported and added to window.DMOD
const MODULES_TO_IMPORT = [
    "/static/js/utilities.js"
];


/**
 * Create a common date formatter
 * @return {DateTimeFormat}
 */
function getDateFormatter() {
    let formatterOptions = {
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    };

    // Base formatter rules based on Canada since it'll yield values in the right order and characters
    // e.g. YYYY-DD-MM where en-us is DD/MM/YYYY
    return new Intl.DateTimeFormat('en-ca', formatterOptions);
}

/**
 * Format the given date into human friendly text
 * @param {Date?} date The date to format. Uses the current local value if a date isn't given
 * @return {string}
 */
function formatDate(date) {
    if (date == null) {
        date = new Date();
    }

    return getDateFormatter().format(date);
}

/**
 * Reposition and size elements on the screen
 * All registered resize functions will be called with no arguments after the core base template elements are sized
 *
 * @param {Event?} event The event that might have caused this resize operation to occur
 */
function resizeScreen(event) {
    let baseContentHeight = $("body").height() - ($("body > header").height() - $("body > footer").height());
    let baseContentSelection = $("#base-content-wrapper");
    baseContentSelection.height(baseContentHeight);

    let baseContent = baseContentSelection[0];
    let paneMargin = Number($(".pane").css("margin").replace("px", ""));

    let contentHeight = baseContent.offsetHeight - (baseContent.offsetTop + paneMargin);
    $("#base-content-wrapper > #content").height(contentHeight);

    resizeHandlers.forEach(handler => handler(event));
}

/**
 * Convert HTML strings into DOM objects
 * @param {String} html HTML representing a single element
 * @return {HTMLElement|null}
 */
function htmlToElement(html) {
    const template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    return template.content.firstChild;
}

/**
 * Cuts off a number after a given number of digits
 *
 * @example
 *      >>> truncateDecimal(5.234234234, 2);
 *      5.23
 *      >>> truncateDecimal(5.234234234);
 *      5.234234234
 *      >>> truncateDecimal(5.234234234, -2);
 *      5.234234234
 *
 * @param {Number} number The number to truncate
 * @param {Number} digits The number of decimal digits to include
 * @return {Number}
 */
function truncateDecimal(number, digits) {
    if (digits == null || digits <= 0) {
        return number;
    }

    if (typeof number == "string") {
        number = parseFloat(number);
    }

    const multiplier = Math.pow(10, digits);
    const adjustedNum = number * multiplier;
    const truncatedNum = Math[adjustedNum < 0 ? 'ceil' : 'floor'](adjustedNum);

    return truncatedNum / multiplier;
}

/**
 * Rounds a number to the given decimal places
 *
 * @example
 *      >>> roundToDigits(5.234234234, 2);
 *      5.23
 *      >>> roundToDigits(5.238234234, 2);
 *      5.24
 *      >>> roundToDigits(5.234234234);
 *      5.234234234
 *      >>> roundToDigits(5.234234234, -2);
 *      5.234234234
 *
 * This is constrained by standard floating point issues. The following call is technically wrong:
 *
 *      >>> roundToDigits(224.9849, 2)
 *      224.98
 *
 * When calculating the rounding by hand, that should result in 224.99, since that final `9` rounds the previous
 * `4` to `5` which will round the final desired digit (taking the place of that `8`) up to `9`. Solutions for this
 * are far more computationally intensive, so it is recommended that this function is used for display purposes only
 * with any need for greater accuracy achieved server side rather than client side.
 *
 * @return {Number}
 * @param number The number to round
 * @param digits The number of digits to round by
 */
function roundToDigits(number, digits) {
    if (digits == null || digits <= 0) {
        return number;
    }

    if (typeof number == "string") {
        number = parseFloat(number);
    }

    // Create an adjuster move the number to the desired number of digits to the left of the decimal point
    const digitAdjustment = Math.pow(10, digits);

    // Move the value the desired number of digits to the left to push all desired digits into non-decimal territory.
    let adjustedNumber = (number * digitAdjustment);

    // Add an adjustment via EPSILON to help avoid floating point issues
    adjustedNumber = adjustedNumber * (1 + Number.EPSILON);

    // Round the adjusted number. This will yield an integer
    const roundedInteger = Math.round(adjustedNumber);

    // Move the desired digits back to the right of the decimal point
    return roundedInteger / digitAdjustment;
}

async function runFunctions(functions, arguments) {
    for (let func of functions) {
        let result = null;

        if (arguments) {
            result = func(...arguments);
        } else {
            result = func();
        }

        while (result != null && Object.keys(result).includes('then') && typeof result.then == "function") {
            result = await result;
        }
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 *  Run and wait for all start up scripts to complete
 */
async function runStartupScripts() {
    return await runFunctions(startupScripts);
}

async function initializeWidgets() {
    const allButtons = $("button");

    allButtons.button();
    allButtons.on("click", event => event.preventDefault());

    await runFunctions(widgetInitializers);
}


function withModule(module) {
    if (!Object.keys(window).includes("DMOD")) {
        window.DMOD = {};
    }

    Object.entries(module).forEach(
        ([name, entity]) => window.DMOD[name] = entity
    );
}

async function assignModules() {
    MODULES_TO_IMPORT.forEach(
        moduleName => {
            import(moduleName).then(withModule);
        }
    )
}

startupScripts.push(assignModules);

$(function() {
    initializeWidgets()
        .then(assignModules)
        .then(runStartupScripts)
        .then(function() {
            resizeScreen();
            window.addEventListener("resize", resizeScreen);
        });
});