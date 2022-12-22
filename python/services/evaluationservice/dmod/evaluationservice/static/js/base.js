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

$(function() {
    startupScripts.forEach(script => script());
});