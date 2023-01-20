let startupScripts = [];


function getDateFormatter() {
    var channel = $("#channel-name").text();
    var formatterOptions = {
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
    var formatter = new Intl.DateTimeFormat('en-ca', formatterOptions);

    return formatter;
};

function resizeScreen() {
    var baseContentHeight = $("body").height() - ($("body > header").height() - $("body > footer").height())
    $("#base-content-wrapper").height(baseContentHeight);

    var baseContent = $("#base-content-wrapper")[0];
    var paneMargin = Number($(".pane").css("margin").replace("px", ""));

    var contentHeight = baseContent.offsetHeight - (baseContent.offsetTop + paneMargin);
    $("#base-content-wrapper > #content").height(contentHeight);
}

/**
 * @param {String} HTML representing a single element
 * @return {Element}
 */
function htmlToElement(html) {
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    return template.content.firstChild;
}

/**
 * Cuts off a number after a given number of digits
 *
 *      >>> truncateDecimal(5.234234234, 2);
 *      5.23
 *      >>> truncateDecimal(5.234234234);
 *      5.234234234
 *      >>> truncateDecimal(5.234234234, -2);
 *      5.234234234
 *
 * @param {Number} The number to truncate
 * @param {Number} The number of decimal digits to include
 * @return {Number}
 */
function truncateDecimal(number, digits) {
    if (digits == null || digits <= 0) {
        return number;
    }

    if (typeof number == "string") {
        number = parseFloat(number);
    }

    var multiplier = Math.pow(10, digits);
    var adjustedNum = number * multiplier;
    var truncatedNum = Math[adjustedNum < 0 ? 'ceil' : 'floor'](adjustedNum);

    return truncatedNum / multiplier;
}



/**
 * Rounds a number to the given decimal places
 *
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
 * @param {Number} The number to round
 * @param {Number} The number of decimal digits to include
 * @return {Number}
 */
function roundToDigits(number, digits) {
    if (digits == null || digits <= 0) {
        return number;
    }

    if (typeof number == "string") {
        number = parseFloat(number);
    }

    // Create an adjuster move the number to the desired number of digits to the left of the decimal point
    var digitAdjustment = Math.pow(10, digits);

    // Move the value the desired number of digits to the left to push all desired digits into non-decimal territory.
    var adjustedNumber = (number * digitAdjustment);

    // Add an adjustment via EPSILON to help avoid floating point issues
    adjustedNumber = adjustedNumber * (1 + Number.EPSILON);

    // Round the adjusted number. This will yield an integer
    var roundedInteger = Math.round(adjustedNumber);

    // Move the desired digits back to the right of the decimal point
    var roundedNumber = roundedInteger / digitAdjustment;

    return roundedNumber;
}

$(function() {
    resizeScreen();
    window.addEventListener("resize", resizeScreen);
    startupScripts.forEach(script => script());
});