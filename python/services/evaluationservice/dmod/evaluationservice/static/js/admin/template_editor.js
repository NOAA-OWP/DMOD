import {JSONConfigurationEditor} from "./json_editor.js";
const $ = window.django.jQuery;

$(document).ready(
    function() {
        const editor = new JSONConfigurationEditor(
            "#id_template_configuration",
            "#template_editor"
        );
        editor.initialize();
    }
);
