const $ = window.django.jQuery;

export class JSONConfigurationEditor {
    /**
     * The element that stores the actual data that will be submitted to the server
     */
    #field;
    /**
     * The textarea that holds the data to edit and that the editor will be centered on
     */
    #textArea;
    /**
     * The CodeMirror editor
     */
    #editor;
    /**
     * The label that accompanies the field
     */
    #label;

    constructor(fieldID, textAreaID) {
        this.#field = $(fieldID);
        this.#textArea = $(textAreaID)[0];
        this.#label = $(`label[for="${fieldID}"]`)
    }

    initialize() {
        this.#field.hide();
        let contents = this.#field.val();

        try {
            const deserializedContent = JSON.parse(contents);
            contents = JSON.stringify(deserializedContent, null, 4);
        } catch (e) {
            console.error("The data for the template configuration was invalid and could not be reformatted");
        }

        this.#textArea.value = contents;
        this.#editor = CodeMirror.fromTextArea(
            this.#textArea,
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

        this.#editor.on(
            "change",
            this.editorHasError
        );

        this.#editor.on(
            "change",
            this.onChange
        );

        this.#label.css("float", "none");

        $('input[type="submit"]').on("click", this.submitChanges);
        this.showError();
    }

    onChange() {
        this.#editor.save();
        this.#field.val(this.#editor.getValue());
    }

    submitChanges(event) {
        const foundError = this.showError();

        if (foundError) {
            event.preventDefault();
        }
    }

    editorHasError() {
        setTimeout(this.showError, 800);
    }

    showError(message) {
        const lintState = this.#editor.state.lint;
        let errorMessages = [];
        if (message == null) {
            for (let marker of lintState.marked) {
                if (marker.className.includes("error")) {
                    for (let errorMessage of formatErrorMessages(marker.__annotation.message)) {
                        errorMessages.push(errorMessage);
                    }
                }
            }
        }
        else {
            errorMessages = formatErrorMessages(message);
        }

        errorMessages = errorMessages.join(" ");

        const errorBox = $("#json-errors");

        errorBox.text(errorMessages);

        if (errorMessages) {
            errorBox.show();
            this.shakeError();
            errorBox.addClass("editor-error");
            return true;
        }
        else {
            errorBox.hide();
            errorBox.removeClass("editor-error");
            return false
        }
    }

    shakeError() {
        $("#json-errors").removeClass("cause-shake");
        setTimeout(
            function() {
                $("#json-errors").addClass("cause-shake");
            }, 10
        )
    }
}

function formatErrorMessages(message) {
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

if (!Object.keys(window).includes('DMOD')) {
    window.DMOD = {};
}

if (!Object.keys(window.DMOD).includes('admin')) {
    window.DMOD.admin = {};
}

window.DMOD.admin.JSONConfigurationEditor = JSONConfigurationEditor;