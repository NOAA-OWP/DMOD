window.DMOD = {
    library: {
        GET_URL: null,
        OPTIONS_URL: null,
        added_libraries: []
    }
}

async function addOptions() {
    await fetch(
        window.DMOD.library.OPTIONS_URL
    ).then(
        (response) => response.json()
    ).then(function(json) {
        addToSelector("#language-selector", json.languages);
        addToSelector("#client-selector", json.clients);
    });
}

/**
 * Add entries in a series of value-key pairs to a select element
 *
 * @param {String} id The id value for the select element
 * @param {Object[]} valueKeyPairs
 */
function addToSelector(id, valueKeyPairs) {
    if (!id.startsWith("#")) {
        id = "#" + id;
    }
    const selector = $(id);

    for (let entry of valueKeyPairs) {
        if ($(selector).find(`option[value="${entry.value}"]`).length === 0) {
            let option = document.createElement("option");
            option.value = entry.value;
            option.textContent = entry.text;

            selector.append(option);
        }
    }
}

/**
 * Ask the server to build and deliver library code
 * @param {MouseEvent} event
 */
function getLibrary(event) {
    const languageType = {
        "javascript": "application/javascript"
    }

    const languageExtension = {
        "javascript": "js"
    }

    const language = $("#language-selector").val();
    const client = $("#client-selector").val();

    $.ajax({
        method: "GET",
        url: window.DMOD.library.GET_URL,
        data: {
            "language": language,
            "client": client
        }
    }).done(function(code) {
        const file = new Blob([code], {type: languageType[language]});
        const fileUrl = URL.createObjectURL(file);
        const fileName = `${client}.${languageExtension[language]}`;
        const fileAnchor = document.createElement("a");
        fileAnchor.href = fileUrl;
        fileAnchor.download = fileName;
        document.body.appendChild(fileAnchor);
        fileAnchor.click();

        setTimeout(function() {
            document.body.removeChild(fileAnchor);
            window.URL.revokeObjectURL(fileUrl);
        }, 0);

        return new Promise((resolve, reject) => {
            try {
                const scriptElement = document.createElement("script");
                scriptElement.type = "module";
                scriptElement.async = false;
                scriptElement.src = fileUrl;

                scriptElement.addEventListener("load", (ev) => {
                    resolve({ status: true });
                });

                scriptElement.addEventListener("error", (ev) => {
                    reject({
                        status: false,
                        message: `Failed to load the script ＄{fileURL}`
                    });
                });

                document.body.appendChild(scriptElement);
            } catch (error) {
                reject(error);
            }
        });
    });
}

function initializeLibraryEditor() {
    const allButtons = $("button");

    allButtons.button();
    $("select").selectmenu();

    allButtons.on("click", function(event) {
        event.preventDefault();
    });

    $("#get-library-button").on("click", getLibrary);

    addOptions();
}

startupScripts.push(initializeLibraryEditor);
