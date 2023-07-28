/**
 * Supplies custom functions and handling for the SpecificationTemplateForm
 */

/**
 * Handler for when the template type selector has changed values
 */
function templateTypeChanged() {
    changeConfigurationSchema(this);
}

/**
 * Update the JSON editor with the selected schema
 *
 * @param {HTMLElement?} selector A select element stating what schema to use
 */
function changeConfigurationSchema(selector) {
    let newSchema = null;
    const editorData = getEditorData("template_configuration");

    if (selector === null || selector === undefined) {
        selector = django.jQuery("select[name=template_specification_type]")[0];
    } else if (selector instanceof django.jQuery) {
        selector = selector[0];
    }

    if (!(selector.hasOwnProperty("value") || "value" in selector)) {
        return;
    }

    if (editorData !== null && "schemas" in editorData && selector.value in editorData.schemas) {
        newSchema = editorData.schemas[selector.value];
    }

    if (newSchema === null || newSchema === undefined) {
        return;
    }

    const editor = getEditor("template_configuration");

    if (editor) {
        editor.setSchema(newSchema);

        let currentText = editor.getText();

        if (currentText === null) {
            currentText = "";
        } else {
            currentText = currentText.trim();
        }

        if (currentText.length === 0 || currentText.match(/^\{?\s*}?$/)) {
            const newData = buildObjectFromSchema(newSchema);
            editor.set(newData);
        }
    }
}

/**
 * Attach the `templateTypeChanged` function to the 'change' event for the template specification type selector
 */
function attachSpecificationTypeChanged() {
    const selector = django.jQuery("select[name=template_specification_type]");
    selector.on("change", templateTypeChanged);
}

/**
 * Make sure that the change handler for the template type selector is attached and
 * that the proper schema is attached to the editor once the page is done loading
 */
document.addEventListener(
    "DOMContentLoaded",
    function() {
        attachSpecificationTypeChanged();
        changeConfigurationSchema();
    }
);