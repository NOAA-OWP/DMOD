import {getElementHeight, INITIAL_DIGITS_PATTERN} from "/static/js/utilities.js";

window.DMOD.code = {
    views: [],
    initializeCodeViews: function() {
        window.DMOD.code.views.forEach((codeView) => {
            let editorArea = $("textarea" + codeView.textarea)[0];
            codeView.view = CodeMirror.fromTextArea(
                editorArea,
                codeView.config
            );
        });
    },
    resizeCodeViews: function(viewName) {
        window.DMOD.code.views.forEach((codeView) => {
            if (viewName == null || codeView.tab === viewName) {
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
    },
    getCodeView: function(viewName) {
        for (const codeView of window.DMOD.code.views) {
            if (codeView.name === viewName) {
                return codeView;
            }
        }
    }
};

startupScripts.push(window.DMOD.code.initializeCodeViews);