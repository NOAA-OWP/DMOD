import {getElementHeight, INITIAL_DIGITS_PATTERN} from "/static/js/utilities.js";

/**
 * @typedef {Object} CodeViewInput
 * @description Data provided by a server used to create a CodeView
 * @property {string} name An identifier for the CodeView
 * @property {string} tab The tab that the CodeView might lie on
 * @property {string} container The id of the HTML element that will contain the editor
 * @property {Object<string, string|number|boolean|Array|Object<String, any>>} config Configuration options
 *      containing all the necessary options to build the CodeMirror editor
 * @property {string} textarea The css selector of the textarea that will hold the editor's content
 */

/**
 * @typedef {Object} CodeView
 * @description An object pointing to a CodeMirror editor and useful metadata
 * @property {string} name An identifier for the CodeView
 * @property {string} tab The tab that the CodeView might lie on
 * @property {string} container The CSS selector of the HTML element that will contain the editor
 * @property {string} textarea The id of the textarea that will hold the editor's content
 * @property {Object<string, any>} config Configuration options containing all the necessary options to build the CodeMirror editor
 * @property {CodeMirror} view The CodeMirror editor
 */

/**
 * @typedef {Object} CodeNamespace
 * @description Namespace object used to encapsulate functions and objects related to showing and supporting code-based operations
 * @property {(string) => CodeMirror} getEditor
 * @property {(string) => CodeView} getCodeView
 * @property {() => void} initializeCodeViews
 * @property {function(string?): void} resizeCodeViews
 * @property {CodeView[]} views
 */

class CodeNamespace {
    #views = [];

    constructor() {
    }

    initializeCodeViews = () => {
        this.#views.forEach((codeView) => {
            let editorArea = $("textarea" + codeView.textarea)[0];

            if (editorArea.length === 0) {
                console.error(
                    `No editor can be created for ${codeView.name}; the textarea ${codeView.textarea} could not be found.`
                );
                return;
            }

            codeView.view = CodeMirror.fromTextArea(
                editorArea,
                codeView.config
            );
        });
    };

    resizeCodeViews = (viewName) => {
        this.#views.forEach((codeView) => {
            if (viewName == null || codeView.tab === viewName || codeView.name === viewName) {
                let containerID;

                if (codeView.container.startsWith("#")) {
                    containerID = codeView.container;
                }
                else {
                    containerID = `#${codeView.container}`;
                }
                const area = $(containerID);

                let height = area.height();

                const paddingTop = area.css("padding-top");

                if (paddingTop) {
                    const amountTop = paddingTop.match(INITIAL_DIGITS_PATTERN);

                    if (amountTop) {
                        height -= Number(amountTop[0]);
                    }
                }

                const paddingBottom = area.css("padding-bottom");

                if (paddingBottom) {
                    const amountBottom = paddingBottom.match(INITIAL_DIGITS_PATTERN);

                    if (amountBottom) {
                        height -= Number(amountBottom[0]);
                    }
                }

                for (let element of area.find("> :not(div.CodeMirror):visible")) {
                    height -= getElementHeight(element);
                }

                codeView.view.setSize(null, height);
            }
        });
    };

    /**
     *
     * @param {CodeViewInput[]} views
     */
    addViews = (views) => {
        views.forEach(this.addView);
    }

    /**
     *
     * @param {CodeViewInput} viewData
     */
    addView = (viewData) => {
        this.#views.push(viewData);
    }

    /**
     * Get a specific code view based off its name
     * @param {string} viewName The name of the view to find
     * @returns {CodeView}
     */
    getCodeView = (viewName) => {
        for (const codeView of this.#views) {
            if (codeView.name === viewName) {
                return codeView;
            }
        }
        throw new Error(`There is no code view by the name of '${viewName}'`);
    }

    getCode = (viewName) => {
        const editor = this.getEditor(viewName);
        return editor.getValue();
    }

    /**
     * Get the editor associated with a CodeView
     * @param {string} viewName The name of the view
     * @returns {CodeMirror}
     */
    getEditor = (viewName) => {
        const view = this.getCodeView(viewName);
        return view.view;
    }
}

window.DMOD.code = new CodeNamespace();

startupScripts.push(window.DMOD.code.initializeCodeViews);
