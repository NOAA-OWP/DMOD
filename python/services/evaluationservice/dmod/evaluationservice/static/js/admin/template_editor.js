const $ = window.django.jQuery;
let configurationEditor = null;

function shakeError() {
    $("#json-errors").removeClass("cause-shake");
    setTimeout(
        function() {
            $("#json-errors").addClass("cause-shake");
        }, 10
    );
}

function formErrorMessages(message) {
    let messageLines = message.split("\n");
    let outputMessageLines = [];

    for (let line of messageLines) {
        if (line.search(/[a-zA-Z]/g) < 0) {
            break;
        }

        outputMessageLines.push(line);
    }
    return outputMessageLines;
}

function showErrorMessage(message) {
    const lintState = configurationEditor.state.lint;
    let errorMessages = [];
    if (message == null) {
        for (let marker of lintState.marked) {
            if (marker.className.includes("error")) {
                for (let errorMessage of formErrorMessages(marker.__annotation.message)) {
                    errorMessages.push(errorMessage);
                }
            }
        }
    }
    else {
        errorMessages = formErrorMessages(message);
    }

    errorMessages = errorMessages.join(" ");

    const errorBox = $("#json-errors");

    errorBox.text(errorMessages);

    if (errorMessages) {
        errorBox.show();
        shakeError();
        errorBox.addClass("editor-error");
        return true;
    }
    else {
        errorBox.hide();
        errorBox.removeClass("editor-error");
        return false
    }
}

function editorHasError() {
    setTimeout(function() {
        showErrorMessage();
    }, 800);
}

function submitChanges(event) {
    const foundError = showErrorMessage();

    if (foundError) {
        event.preventDefault();
    }
}

$(document).ready(
    function() {
        const field = $("#id_template_configuration");
        field.hide();
        let contents = field.val();

        try {
            const deserializedContent = JSON.parse(contents);
            contents = JSON.stringify(deserializedContent, null, 4);
        } catch (e) {
            console.error("The data for the template configuration was invalid and could not be reformatted");
        }

        const editorArea = $("#template_editor")[0];
        editorArea.value = contents;
        configurationEditor = CodeMirror.fromTextArea(
            editorArea,
            {
                mode: 'application/json',
                json: true,
                indentUnit: 4,
                lineNumbers: true,
                allowDropFileTypes: ['application/json'],
                viewportMargin: Infinity,
                matchBrackets: true,
                autoCloseBrackets: true,
                foldGutter: true,
                gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter", "CodeMirror-lint-markers"],
                lint: true
            }
        );

        configurationEditor.on(
            "change",
            editorHasError
        );

        configurationEditor.on(
            "change",
            (_) => {
                configurationEditor.save();
                field.val(configurationEditor.getValue());
            }
        );

        $('label[for="id_template_configuration"]').css("float", "none");

        $('input[type="submit"]').on("click", submitChanges);
        showErrorMessage();
    }
);