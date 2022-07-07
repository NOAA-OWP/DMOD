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

function getJSONReplacer() {
    return null;
}

function getExpectedIndentSpaces() {
    return 4;
}

function submit_evaluation(event) {
    $("#edit-div").attr("action", LAUNCH_URL);
}

$(function(){
    var editorArea = $("textarea#instructions")[0];

    editor = CodeMirror.fromTextArea(
        editorArea,
        editorConfig
    );

    var area = document.querySelector("#editor-content");
    var height = area.offsetHeight;

    editor.setSize(null, height);

    $("#evaluation-submit").click(submit_evaluation);
});