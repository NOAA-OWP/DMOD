import {
    getWebSocketURL,
    toJSON,
    downloadData,
    attachCode,
    getServerData,
    hasAttr,
    waitForConnection,
    subtractUnitStrings
} from "/static/js/utilities.js";

import {TreeView} from "/static/js/widgets/tree.js";

import {TemplateObjectConstructor} from "/static/maas/js/template.js";


/**
 * @typedef {{event: string, response_type: string, data: Object, message_time: string}} ActionParameters
 *
 * @typedef {(response: ActionParameters, socket: WebSocket) => any} ActionHandler
 */


window.DMOD.evaluation = {};

/**
 *
 * @type {Object|null}
 */
window.DMOD.evaluation.visualizationMap = null;

/**
 *
 * @type {LaunchClient}
 */
window.DMOD.evaluation.client = null;

/**
 * A record of messages returned from the service
 * @type {Object<string, Object[]>}
 */
window.DMOD.evaluation.digest = {};

/**
 *
 * @type {Object<string, Object>}
 */
window.DMOD.evaluation.metricDefinitions = {};


/**
 *
 * @type {TreeView|null}
 */
window.DMOD.evaluation.templateTree = null;

const tabChangedHandlers = {};

function recordMessage(dateAndTime, message) {
    if ($("#record-messages").val() === "on") {
        const event = message['event'];
        if (!hasAttr(window.DMOD.evaluation.digest, event)) {
            window.DMOD.evaluation.digest[event] = [];
        }
        message['time'] = dateAndTime;
        window.DMOD.evaluation.digest[event].push(message);
    }
}

function getDigestFileName() {
    const formatter = getDateFormatter();
    const channel = $("#channel-name").text();

    let filename = `Digest_for_${channel}_at_${formatter.format(new Date())}.json`
    // filename is now 'Digest_for_channel name_at_2022-06-15, 11:38 CDT.json'

    filename = filename.replaceAll(",", "");
    // filename is now 'Digest_for_channel name_at_2022-06-15 11:38 CDT.json'

    filename = filename.replaceAll(" ", "_");
    // filename is now 'Digest_for_channel_name_at_2022-06-15_11:38_CDT.json'

    filename = filename.replaceAll(":", ".");
    // filename is now 'Digest_for_channel_name_at_2022-06-15_11.38_CDT.json'

    return filename;
}

function filterDigest() {
    let filteredDigest = {};
    let eventsToInclude = $("#digest-event-selectors input:checked").toArray().map((element) => {return element.name;});

    for (let event of eventsToInclude) {
        filteredDigest[event] = window.DMOD.evaluation.digest[event];
    }

    return filteredDigest;
}

function getDigest(event) {
    if (event) {
        event.preventDefault();
    }

    const filteredDigest = filterDigest();

    if (filteredDigest.length === 0) {
        $("#digest-error-message").text("No messages in the digest match the given filter.");
        return;
    }

    const filename = getDigestFileName();

    downloadData(filename, filteredDigest)

    closePopups();
}

/**
 *
 * @param {Event} event
 * @returns {Promise<void>}
 */
async function submit_evaluation(event) {
    if (event) {
        event.preventDefault();
    }

    let editorData = window.DMOD.code.getCodeView("editor");

    const instructions = editorData.view.getValue();
    const evaluationName = document.getElementById("evaluation_id").value;

    await window.DMOD.evaluation.client.launch(evaluationName, instructions);

    if (!editorData.view.getOption("readonly")) {
        editorData.view.setOption("readonly", true);
    }

    $("#tabs").tabs("option", "active", 1);
}

/**
 *
 * @param {Event} event
 * @param {string} tabID
 */
async function switchTabs(event, tabID) {
    await closePopups(event);

    $(".tab").hide();
    $("#" + tabID).show();

    if (tabID in tabChangedHandlers) {
        for (let handler of tabChangedHandlers) {
            let result = handler(event);

            while (result instanceof Promise) {
                result = await result;
            }
        }
    }

    await pageChanged();
}

/**
 *
 * @param {HTMLElement} panel
 */
function resizeTabContent(panel) {
    const headerSelector = `#${panel.id} .tab-header`;
    const contentSelector = `#${panel.id} .tab-content`;
    const footerSelector = `#${panel.id} .tab-footer`;

    const header = $(headerSelector)[0];
    const content = $(contentSelector)[0];
    const footer = $(footerSelector)[0];

    const newContentHeight = panel.offsetHeight - (panel.offsetTop + header.offsetHeight + footer.offsetHeight);

    content.style.height = `${newContentHeight}px`;
}

/**
 *
 * @param {number} panelIndex
 */
function resizePanel(panelIndex) {
    const tabInstance = $("#tabs").tabs("instance");
    const panel = tabInstance.panels[panelIndex];
    const tabsElement = tabInstance.element[0];

    const tabsElementTop = tabsElement.offsetTop;
    const tabsElementHeight = tabsElement.offsetHeight;

    panel.style.height = `${tabsElementHeight - tabsElementTop}px`;

    resizeTabContent(panel);

    const panelID = panel.id;

    DMOD.code.resizeCodeViews(panelID);

    const mapSelector = `#${panelID} #${DMOD.evaluation.visualizationMap.getContainer().id}`;

    if ($(mapSelector).length) {
        DMOD.evaluation.visualizationMap.updateSize();
    }
}

function resizeTabs() {
    let tabs = $("#tabs");
    tabs.height(tabs.parent().height());

    let activeTabNumber = tabs.tabs("option", "active");

    resizePanel(activeTabNumber);
}

/**
 *
 * @param {Event} event
 */
function syncNameChange(event) {
    $("#evaluation_name").val(event.target.value);
}

/**
 *
 * @param {string?} message
 */
function updateError(message) {
    const errorBox = $("#general-error-box");

    if (message) {
        errorBox.show();
        document.getElementById("error-message").textContent = message;
    }
    else {
        errorBox.hide();
    }

    resizeScreen();
}

/**
 * Update a location on the map based on a received location score
 * @param {ActionParameters} message
 * @param {WebSocket?} socket
 */
function updateLocationScore(message, socket) {
    const data = message.data;
    const predictedLocation = data.predicted_location;

    const feature = DMOD.evaluation.visualizationMap.getFeature(predictedLocation);

    if (feature) {
        const grade = data.scores.grade;
        const gradeColor = getGradeColor(grade);

        feature.setStyle({
            "fillColor": gradeColor,
            "color": gradeColor,
        });

        updateLocationPopup(feature, data);
        updateLocationTooltip(feature, data);
    }
}

/**
 *
 * @param {number} metricCount
 * @returns {number}
 */
function getLocationMetricColumnCount(metricCount) {
    if (metricCount === 1 || metricCount == null || metricCount <= 0) {
        return 1;
    }
    else if (metricCount === 2) {
        return 2;
    }
    else if (metricCount === 4) {
        return 2;
    }
    else if (metricCount < 10) {
        return 3;
    }
    else {
        return 4;
    }
}

/**
 *
 * @param {Layer} featureLayer
 * @param {Object} data
 */
function updateLocationTooltip(featureLayer, data) {
    if (featureLayer == null) {
        return;
    }

    const grade = getGradeLetter(data.scores.grade);
    const text = `${data.observed_location} vs ${data.predicted_location}: ${grade}`;

    featureLayer.bindTooltip(text);
}

/**
 *
 * @param {Layer} featureLayer
 * @param {{observed_location: string, predicted_location: string, scores: {grade: number, scores: Object<string, {scaled_value: number, weight: number, thresholds: Object<string, any>[]}>}}} data
 */
function updateLocationPopup(featureLayer, data) {
    if (featureLayer == null) {
        return;
    }

    const wrapperDiv = document.createElement("div");
    wrapperDiv.classList.add("freature-result-wrapper");

    const content = document.createElement("fieldset");
    content.classList.add("feature-result-fields");

    wrapperDiv.appendChild(content);

    const legend = document.createElement("legend");
    legend.classList.add("feature-result-legend");

    legend.textContent = `${data.observed_location} vs ${data.predicted_location}`;

    content.appendChild(legend);

    const metrics = Object.entries(data.scores.scores);

    const columnCount = getLocationMetricColumnCount(metrics.length);

    let gridColumnTemplate = "";

    for (let i = 0; i < columnCount; i++) {
        gridColumnTemplate = gridColumnTemplate + "auto ";
    }

    content.style['grid-template-columns'] = gridColumnTemplate;

    for (let [metricName, metricData] of metrics) {
        const metricFieldSet = document.createElement("fieldset");
        metricFieldSet.classList.add("metric-result-fields");

        if (metricName in DMOD.evaluation.metricDefinitions) {
            metricFieldSet.setAttribute(
                "title",
                DMOD.evaluation.metricDefinitions[metricName].description
            );
        }

        const metricLegend = document.createElement("legend");
        metricLegend.classList.add("metric-result-legend");

        metricLegend.textContent = metricName;

        metricFieldSet.appendChild(metricLegend);

        const metricGrade = (metricData.scaled_value / metricData.weight * 100.0).toFixed(2);
        const gradeMarkup = `<span class="metric-result-grade"><b>Grade</b>: ${metricGrade}%`;
        metricFieldSet.appendChild(htmlToElement(gradeMarkup));

        metricFieldSet.appendChild(document.createElement("br"));

        const weightMarkup = `<span class="metric-result-weight"><b>Weight</b>: ${metricData.weight}</span>`;
        metricFieldSet.appendChild(htmlToElement(weightMarkup));

        metricFieldSet.appendChild(document.createElement("br"));
        metricFieldSet.appendChild(document.createElement("hr"));

        const thresholdTable = document.createElement("table");
        thresholdTable.classList.add("metric-result-threshold-table");

        const headerRow = document.createElement("tr");
        headerRow.appendChild(document.createElement("th"));

        const gradeColumn = document.createElement("th");
        gradeColumn.classList.add("metric-result-grade-column");
        gradeColumn.classList.add("metric-result-grade-column-header");
        gradeColumn.textContent = "Grade";

        headerRow.appendChild(gradeColumn);

        const weightColumn = document.createElement("th");
        weightColumn.classList.add("metric-result-weight-column");
        weightColumn.classList.add("metric-result-weight-column-header");
        weightColumn.textContent = "Weight";

        headerRow.appendChild(weightColumn);

        thresholdTable.appendChild(headerRow);

        for (let entry of Object.values(metricData.thresholds)) {
            const thresholdEntryRow = document.createElement("tr");

            const thresholdNameCell = document.createElement("th");
            thresholdNameCell.classList.add("metric-result-threshold-name-cell");
            thresholdNameCell.textContent = entry.threshold;

            thresholdEntryRow.appendChild(thresholdNameCell);

            const thresholdGradeCell = document.createElement("td");
            thresholdGradeCell.classList.add("metric-result-grade-column");

            thresholdGradeCell.textContent = `${entry.grade.toFixed(2)}%`;

            thresholdEntryRow.appendChild(thresholdGradeCell);

            const thresholdWeightCell = document.createElement("td");
            thresholdWeightCell.classList.add("metric-result-weight-column");
            thresholdWeightCell.textContent = entry.weight;

            thresholdEntryRow.appendChild(thresholdWeightCell);

            thresholdTable.appendChild(thresholdEntryRow);
        }

        metricFieldSet.appendChild(thresholdTable);
        content.appendChild(metricFieldSet);
    }

    const finalGradeMarkup = `<h2 class="feature-result-grade">Grade: ${data.scores.grade.toFixed(2)}%</h2>`;
    wrapperDiv.appendChild(htmlToElement(finalGradeMarkup));

    // @todo: evaluate the maxHeight and maxWidth so that it works better at different resolutions

    const popupOptions = {
        "maxWidth": "900px",
        "maxHeight": "500px"
    }

    featureLayer.bindPopup(
        wrapperDiv,
        popupOptions
    );
}

/**
 * Get the letter grade for a number from [0, 100]
 * @param {number} grade
 * @returns {string}
 */
function getGradeLetter(grade) {
    if (grade == null) {
        return "Unknown";
    }

    if (grade >= 96.66) {
        return "A+";
    }
    else if (grade >= 93.33) {
        return "A";
    }
    else if (grade >= 90.0) {
        return "A-";
    }
    else if (grade >= 86.66) {
        return "B+";
    }
    else if (grade >= 83.33) {
        return "B";
    }
    else if (grade >= 80.0) {
        return "B-";
    }
    else if (grade >= 76.66) {
        return "C+";
    }
    else if (grade >= 73.33) {
        return "C";
    }
    else if (grade >= 70.0) {
        return "C-";
    }
    else if (grade >= 66.66) {
        return "D+";
    }
    else if (grade >= 63.33) {
        return "D";
    }
    else if (grade >= 60.0) {
        return "D-";
    }

    return "F";
}

/**
 * Get the color that corresponds with a grade
 * @param {string} gradeLetter
 * @returns {string}
 */
function getGradeColor(gradeLetter) {
    let color;

    if (typeof gradeLetter == 'number') {
        gradeLetter = getGradeLetter(gradeLetter);
    }

    switch(gradeLetter) {
        case "A+":
        case "A":
        case "A-":
            color = "#09d60f";
            break;
        case "B+":
        case "B":
        case "B-":
            color = "#bcff12";
            break;
        case "C+":
        case "C":
        case "C-":
            color = "#f5f50c";
            break;
        case "D+":
        case "D":
        case "D-":
            color = "#ffc247";
            break;
        default:
            if (gradeLetter !== 'F') {
                console.warn(`Defaulting to the color for F; ${gradeLetter} is not a valid letter grade.`);
                let stackError = new Error();
                console.warn(stackError.stack);
            }
            color = "#d12828";
    }

    if (color[0] !== "#") {
        color = `#${color}`;
    }

    return color;
}

/**
 *
 * @param {ActionParameters} responseData
 */
function handleErrorMessage(responseData) {
    if (!actionErrored(responseData)) {
        return;
    }

    updateError(responseData.data?.message || "An error occurred");
}

/**
 *
 * @param {ActionParameters} actionData
 */
function handleLaunchError(actionData) {
    if (actionErrored(actionData)) {
        $("#evaluation-submit").prop("disabled", false);
    }
}

/**
 * Update the message view with incoming data
 * @param {ActionParameters} actionData
 */
function updateMessages(actionData) {
    let messageView = DMOD.code.getCodeView("messages");

    if (messageView && messageView.view) {
        const newText = toJSON(actionData);
        const currentDate = new Date().toLocaleString();
        recordMessage(currentDate, actionData);
        let newMessage = messageView.view.getValue();
        newMessage += `\n//${Array(200).join("=")}\n\n// [${currentDate}]:\n\n${newText}\n\n`

        messageView.view.setValue(newMessage);
        messageView.view.scrollIntoView(messageView.view.lastLine());
        $("#last-updated").text(currentDate);

        const messageCountField = $("#message-count");
        const updateCount = Number(messageCountField.text()) + 1;
        messageCountField.text(updateCount);
    }
}

/**
 * Update the message view with incoming data
 * @param {ActionParameters} actionData
 */
function updateDigest(actionData) {
    let digestView = DMOD.code.getCodeView("digest");

    if (digestView && digestView.view) {
        let digestText = toJSON(DMOD.evaluation.digest);
        digestView.view.setValue(digestText);
    }
}

/**
 * Show validation information
 * @param {ActionParameters} actionParameters
 * @param {WebSocket} socket
 */
async function showValidationMessages(actionParameters, socket) {
    /**
     * @type {Object}
     * @property {boolean} passed
     * @property {string[]} validation_messages
     */
    const validationData = actionParameters.data;
    const messageContainer = $("#individual-validation-messages");
    const overallValidationMessage = $("#overall-validation-message");

    messageContainer.empty();

    await showPopup(null, "validation-popup");

    if (validationData.passed) {
        overallValidationMessage.removeClass("status-error status-unknown").addClass("status-ok");
        overallValidationMessage.text("The configuration passes all validations");
        messageContainer.hide();
    }
    else {
        overallValidationMessage.removeClass("status-ok status-unknown").addClass("status-error");
        overallValidationMessage.text("The configuration is not ready for evaluation:");

        for (let messageIndex = 0; messageIndex < validationData.validation_messages.length; messageIndex++) {
            const message = validationData.validation_messages[messageIndex];
            for (let line of message.split("\n")) {
                if (line == null || line === '') {
                    continue
                }

                const messageArea = document.createElement("div");
                messageArea.id = `validation-message-${messageIndex}`;
                messageArea.className = "validation-message";
                messageArea.textContent = line;

                messageContainer.append(messageArea);
            }
        }

        messageContainer.show();
    }
}

/**
 * Indicates whether the action results show an error
 *
 * @param {ActionParameters} actionData
 * @returns {boolean} Whether the action data indicated an error
 */
function actionErrored(actionData) {
    return hasAttr(actionData.data, "message")
        && actionData.data.message != null
        && actionData.data.message.length > 0
        && (
            actionData.event === 'error'
            || actionData.response_type === 'error'
            || actionData.type === 'error'
        )
}

async function showTemplatePopup(event) {
    window.DMOD.evaluation.client.getAllTemplates(
        null,
        async (response, socket) => {
            await showPopup(event, "template-search-popup");

            if (actionErrored(response)) {
                updateError(response.data.message);
                return
            }

            if (!("data" in response && "templates" in response.data)) {
                updateError("No template data was received when requested");
                return
            }

            if (window.DMOD.evaluation.templateTree == null) {
                initializeTemplateTree();
            }

            const data = response.data;

            window.DMOD.evaluation.templateTree.populate(
                data.templates,
                {ignoreParent: true},
                new TemplateObjectConstructor()
            );

            window.DMOD.evaluation.templateTree.render();
        }
    )
}

async function showTemplateApplicationPopup(event) {
    await showPopup(event, "template-application-popup");
}

async function copyTemplateToClipboard(event) {
    await closePopups(event);
    const codeView = DMOD.code.getCodeView("template-preview");
    const configuration = codeView.view.getValue();
    await navigator.clipboard.writeText(configuration);
}

async function copyTemplateNameToClipboard(event) {
    await closePopups(event);
    await navigator.clipboard.writeText($("#template-preview-label").text());
}

async function insertTemplate(event) {
    await closePopups(event);
    const preview = DMOD.code.getCodeView("template-preview");
    const configuration = preview.view.getValue();

    const editor = DMOD.code.getCodeView("editor");
    const editorDocument = editor.view.getDoc();
    const start = editorDocument.getCursor();
    const end = editorDocument.getCursor(false);

    editorDocument.replaceRange(configuration, start, end);

    // Attempt to reformat the document to make sure the tabs are right. It's ok if you can't
    try {
        let currentCode = editorDocument.getValue();
        let deserializedData = JSON.parse(currentCode);
        currentCode = JSON.stringify(deserializedData, null, 4);
        editorDocument.setValue(currentCode);
        editorDocument.setCursor(end);
    } catch (e) {
        // It's ok to ignore this error - a failure here just means that the code might look goofy
    }
}

async function loadTemplate(event) {
    const selectedID = window.DMOD.evaluation.templateTree.selectedValue;

    window.DMOD.evaluation.client.getTemplateById(
        selectedID,
        null,
        async (response, socket) => {
            if (actionErrored(response)) {
                updateError(response.data.message);
                return;
            }
            else if (!("data" in response)) {
                updateError("No data was received in a service response - a template could not be loaded.");
                return
            }

            const data = response.data;

            $("#template-description").text(data.description || "");
            $("#template-preview-label").text(data.name || "");

            if ("template" in data) {
                const preview = window.DMOD.code.getCodeView("template-preview");

                let template = data.template;

                if (typeof template === 'object') {
                    template = JSON.stringify(template, null, 4);
                }

                preview.view.setValue(template);
            }
            else {
                console.warn("No template found in request to get a specific template");
            }

            await pageChanged();
        }
    )
}

async function launchClient(event) {
    if (event) {
        event.preventDefault();
    }

    const onOpen = function () {
        const currentDate = new Date().toLocaleString();
        $("#connection-time").text(currentDate);
        $("#connected-edit-buttons").show();
        $("#disconnected-edit-buttons").hide();
    };

    const onError = function(response) {
        updateError(response?.data?.message || response);
    }

    const onClose = function(event) {
        closePopups(event);
        updateError("Disconnected from evaluation service");
        $("#connected-edit-buttons").hide();
        $("#disconnected-edit-buttons").show();
    }

    await getClient();

    if (!clientIsAvailable()) {
        const message = "Cannot access the code necessary to connect to the evaluation service";
        updateError(message);
        throw new Error(message);
    }

    let options = new window.DMOD.clients.LaunchClientOptions()
        .addOpenHandler(onOpen)
        .addSocketErrorHandler(onError)
        .addCloseHandler(onClose)
        .addMessageHandler(updateMessages)
        .addMessageHandler(updateDigest)
        .addMessageHandler(handleErrorMessage)
        .addClientErrorHandler(updateError)
        .setShouldReconnect(true);

    DMOD.evaluation.client = new window.DMOD.clients.LaunchClient(getWebSocketURL(LAUNCH_URL), options)
        .onGetSavedDefinition(loadPreexistingDefinition)
        .onSearch(renderDefinitions)
        .onLaunch(handleLaunchError)
        .onValidateConfiguration(showValidationMessages)
        .onSave((_) => closePopups())
        .on("location_scores", updateLocationScore);
}

/**
 * Check to see if the client is available within the code base
 * @returns {boolean}
 */
function clientIsAvailable() {
    return hasAttr(window.DMOD, 'clients') && hasAttr(window.DMOD.clients, "LaunchClient");
}

/**
 * Reach out to the server to load a client for the evaluation service
 * @param {number?} delay The number of milliseconds to wait when checking to see if the library has loaded
 * @returns {Promise<boolean>}
 */
async function getClient(delay) {
        if (clientIsAvailable()) {
            return true;
        }

        let socket = new WebSocket(getWebSocketURL(LAUNCH_URL));
        socket.onmessage = (response) => {
            const actionParameters = JSON.parse(response.data);

            if (actionErrored(actionParameters)) {
                const message = actionParameters.data?.message || "An error occurred";
                updateError(message);
                return;
            }

            if (actionParameters.event !== 'generate_library' && actionParameters.event !== 'connect') {
                console.error(
                    "Received a non-library related message through the socket seeking client code - " +
                    "all that should be arriving should be a generated library"
                );
                return;
            }

            if (actionParameters.event === 'generate_library') {
                attachCode(actionParameters.data.library);
            }
        }

        const connected = await waitForConnection(socket);

        if (!connected) {
            throw new Error("Could not establish a websocket connection through which to load a new client");
        }

        const payload = {
            "action_parameters": "generate_library"
        }

        socket.send(toJSON(payload));

        const maximumNumberOfTimesToWait = 10;
        let numberOfTimesWaited = 0;
        const minimumWaitTime = 500;

        if (delay == null || typeof delay !== "number") {
            delay = minimumWaitTime;
        }
        else if (delay < minimumWaitTime) {
            console.warn(
                `The amount of time given to wait for an attached client (${delay}ms) was too low; ` +
                `the minimum time (${minimumWaitTime}ms) will be used instead`
            );
            delay = minimumWaitTime;
        }

        while (!clientIsAvailable() && numberOfTimesWaited < maximumNumberOfTimesToWait) {
            await sleep(delay);
        }

        return clientIsAvailable();
}

/**
 * Called when a button used to close popups is clicked
 * @param {Event?} event
 */
async function closePopups(event) {
    if (event) {
        event.preventDefault();
    }
    $("#page-modal").hide();
    $(".popup").hide();
}

/**
 * Handler for when a user hits the save button for their evaluation instructions
 * @param {Event} event
 * @returns {Promise<void>}
 */
async function saveDefinition(event) {
    if (event) {
        event.preventDefault();
    }

    const author = $("#author").val();
    const name = $("#evaluation_name").val();
    const description = $("#description").val();
    const instructions = DMOD.code.getCode("editor");

    await showWaitingPopup(`Waiting to complete saving '${name}`);

    DMOD.evaluation.client.save(
        name,
        description,
        author,
        instructions
    );
}

/**
 * Show a popup that explains that an operation in ongoing
 * @param {string} reason Why the application is waiting
 */
async function showWaitingPopup(reason) {
    $("#waiting-for").text(reason);
    await showPopup(null, "waiting-popup");
}

/**
 * Reaches out to the evaluation service to look for any evaluation specifications that meet the given criteria
 * @param {Event} event
 */
async function filterDefinitions(event) {
    const search_arguments = {};
    // #1
    //implement the search where it will ask the server for definitions and register an action to render them
    const author = $("#search-by-author").val();

    if (author) {
        search_arguments.author = author.trim();
    }

    const name = $("#search-by-name").val();

    if (name) {
        search_arguments.name = name.trim();
    }

    const description = $("#search-by-description").val();

    if (description) {
        search_arguments.description = description;
    }

    DMOD.evaluation.client.search(search_arguments);
}

/**
 * Places found evaluation definitions into the table for user selection
 * @param {Event} event
 * @param {WebSocket} socket
 */
async function renderDefinitions(event, socket) {
    // #2
    //implement the rendering of definitions within the table named 'search-table'

    const searchErrorsElement = $("#search-errors");

    const data = typeof event.data == 'string' ? JSON.parse(event.data) : event.data;

    if (data.response_type === "error") {
        $("#search-error-message").text(data.message);
        searchErrorsElement.show();
        return;
    }

    searchErrorsElement.hide();

    const searchTableBody = document.getElementById("search-table-body");

    while (searchTableBody.firstChild) {
      searchTableBody.removeChild(searchTableBody.firstChild);
    }

    let dataToIterate;

    if (Array.isArray(data)) {
        dataToIterate = data;
    }
    else if ("data" in data && Array.isArray(data.data)) {
        dataToIterate = data.data;
    }
    else {
        console.warn("Could not find evaluation data to iterate through");
        dataToIterate = [];
    }

    for (const definition of dataToIterate) {
        let row = document.createElement("tr");
        row.id = `definition-${definition.identifier}`;
        row.classList.add("search-row");
        row.setAttribute("identifier", definition.identifier);
        row.onclick = selectDefinition

        let authorCell = document.createElement("td");
        authorCell.id = `${definition.identifier}-author`;
        authorCell.classList.add("author-cell");
        authorCell.classList.add("search-cell");
        authorCell.textContent = definition.author.trim();
        authorCell.setAttribute("identifier", definition.identifier);

        row.appendChild(authorCell);

        let nameCell = document.createElement("td");
        nameCell.id = `${definition.identifier}-name`;
        nameCell.classList.add("name-cell");
        nameCell.classList.add("search-cell");
        nameCell.textContent = definition.name.trim();
        nameCell.setAttribute("identifier", definition.identifier);

        row.appendChild(nameCell);

        let descriptionCell = document.createElement("td");
        descriptionCell.id = `${definition.identifier}-description`;
        descriptionCell.classList.add("description-cell");
        descriptionCell.classList.add("search-cell");
        descriptionCell.textContent = definition.description.trim();
        descriptionCell.setAttribute("identifier", definition.identifier);

        row.appendChild(descriptionCell);

        searchTableBody.appendChild(row);
    }

    // #4
    //NOTE: This should clear any selections
    $("#selected-definition").val(null);

    await pageChanged();
}

/**
 * Handler for when a user selects a preexisting evaluation definition
 * @param {Event} event
 */
function selectDefinition(event) {
    // #3
    //implement handler that will select the pk of the row that was clicked
    $(".search-row").removeClass("definition-selected");
    const identifier = event.target.getAttribute("identifier");

    const selectedDefinitionElements = $("#selected-definition");

    const selectSearchButton = $("#select-search-button");

    if (identifier === selectedDefinitionElements.val()){
        selectedDefinitionElements.val(null);
        selectSearchButton.button("disable");
        return;
    }
    selectedDefinitionElements.val(identifier);

    let row = event.target;

    if (event.target.tagName === "TD") {
        row = event.target.parentElement;
    }

    row.classList.add("definition-selected");
    selectSearchButton.button("enable");
}

/**
 * Handler for when it is time to load a preexisting definition into the editor
 * @param {Event} event
 * @returns {Promise<void>}
 */
async function selectPreexistingDefinition(event) {
    let identifier = $("#selected-definition").val();

    if (identifier) {
        DMOD.evaluation.client.getSavedDefinition(identifier);
    }
    else {
        $("#search-errors").show();
        $("#search-error-message").text("Cannot select a definition; there isn't one selected.")
    }

    await pageChanged();
}

/**
 * Show a specific popup
 * @param {Event} event
 * @param {string} popupID
 */
async function showPopup(event, popupID) {
    if (event) {
        event.preventDefault();
    }

    await closePopups(event);

    $(".popup").hide();

    $("#page-modal").show();
    $("#" + popupID).show();

    await pageChanged();
}

/**
 * Show the popup used to search for evaluation specifications
 * @param {Event} event
 */
async function showSearchPopup(event) {
    if (event) {
        event.preventDefault();
    }

    const filterCall = filterDefinitions(event);
    await showPopup(event, "search-popup");
    await filterCall;
}

/**
 * Show the popup that allows users to select what digest values to download
 * @param {Event} event
 */
async function showDigestPopup(event) {
    if (event) {
        event.preventDefault();
    }

    if (Object.keys(DMOD.evaluation.digest).length === 0) {
        updateError("There are no items in the digest to download.");
    }
    else {
        const uniqueEvents = Object.keys(DMOD.evaluation.digest);

        const fieldArea = document.getElementById("digest-event-selectors");

        while (fieldArea.firstChild) {
            fieldArea.removeChild(fieldArea.firstChild);
        }

        for (const uniqueEvent of uniqueEvents) {
            const checkbox = document.createElement("input");
            checkbox.id = uniqueEvent + "-event";
            checkbox.name = uniqueEvent;
            checkbox.type = "checkbox";
            checkbox.setAttribute("checked", "on");

            const label = document.createElement("label");
            label.textContent = uniqueEvent;
            label.for = uniqueEvent + "-event";

            const newLine = document.createElement("br");

            fieldArea.appendChild(checkbox);
            fieldArea.appendChild(label);
            fieldArea.appendChild(newLine);
        }

        await showPopup(event, "digest-modal");
    }
}


/**
 * Load a retrieved evaluation configuration into the editor
 *
 * @param {ActionParameters} event The event that triggered the load
 * @param {WebSocket} socket The configuration retrieved from the server
 */
async function loadPreexistingDefinition(event, socket) {
    if (!("data" in event)) {
        console.warn("Could not load a preexisting definition - no payload was provided");
        return;
    }

    if (actionErrored(event)) {
        await closePopups();
        const message = event.data?.message || "An error occurred when loading a preexisting project definition";
        updateError(message);
        return;
    }

    const responseData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

    const editorView = DMOD.code.getCodeView("editor");

    // The definition will be nested under the 'data' property of the response, so go ahead and pull that out
    let definition = responseData.definition;

    // The definition will most likely be an Object, but we can only load strings into the editor.
    // Convert the to a string and format it to make it easy to read in the editor
    if (typeof(definition) == 'object') {
        definition = toJSON(definition);
    }

    editorView.view.setValue(definition);
    $("#evaluation_id").val(responseData.name.trim());

    // Make sure that the editor view is showing
    await switchTabs(null, "edit-div");
}

/**
 * Gets a listing of options available for geometry and populates the selector with them
 **/
async function populateGeometrySelector() {
    const geometryOptions = await getServerData(GEOMETRY_URL);

    if (geometryOptions == null) {
        console.error("Options for geometry could not be loaded. Elements cannot be properly populated.");
        return;
    }

    const selector = document.getElementById("map-geometry-selector");

    for (let geometryOption of geometryOptions) {
        let option = document.createElement("option");
        option.text = geometryOption.name;
        option.value = geometryOption.value;
        selector.add(option);
    }
}

/**
 * Adds the selected geometry to the map. Any geometry that was already rendered will be replaced.
**/
async function addGeometry(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const selector = document.getElementById("map-geometry-selector");

    if (!GEOMETRY_URL.endsWith("/")){
        GEOMETRY_URL = GEOMETRY_URL + "/";
    }

    const url = GEOMETRY_URL + selector.value;

    const geometry = await getServerData(url);

    DMOD.evaluation.visualizationMap.clear();
    DMOD.evaluation.visualizationMap.plotGeoJSON(geometry);

    let locationScores = [];

    if (DMOD.evaluation.digest.hasOwnProperty("location_scores")) {
        locationScores = DMOD.evaluation.digest.location_scores;
    }

    for (let locationScore of locationScores) {
        updateLocationScore(locationScore);
    }
}

/**
 * Populate fields for editing with previous values and configure fields to update their values for later use
 */
function initializeFields() {
    const editorView = DMOD.code.getCodeView("editor");

    const author = sessionStorage.getItem("author");

    const authorFields = $("#author");

    // Set the value of the author field to the previous value if one was stored
    if (author) {
        authorFields.val(author);
    }

    // Try to find any previous code that was stored in the editor
    let code = sessionStorage.getItem("code");

    // Set the code in the editor to that of the previously stored value
    if (code) {
        editorView.view.setValue(code);
    }

    // Register handlers to save values to session on edit
    editorView.view.on("change", (_) => {
        const ev = DMOD.code.getCodeView("editor");
        sessionStorage.setItem("code", ev.view.getValue());
    });

    authorFields.on(
        "change",
        (_) => {
            sessionStorage.setItem("author", $("#author").val());
        }
    );
}

function initializeTemplateTree() {
    window.DMOD.evaluation.templateTree = new TreeView("template-tree", $("#template-search-tree"));
    window.DMOD.evaluation.templateTree.on(
        "select",
        async (event) => {
            if (window.DMOD.evaluation.templateTree.selectedValue != null) {
                await loadTemplate(event);
            }
            else {
                const preview = window.DMOD.code.getCodeView("template-preview");
                preview.view.setValue("");

                $("#template-description").text("");
                $("#template-preview-label").text("");
            }

            await pageChanged();
        }
    );
    window.DMOD.evaluation.templateTree.on(
        "select",
        async (event) => {
            if (window.DMOD.evaluation.templateTree.selectedValue != null) {
                $(".template-selected-button").show();
            }
            else {
                $(".template-selected-button").hide();
            }
            await pageChanged();
        }
    );
    window.DMOD.evaluation.templateTree.on(
        "select",
        pageChanged
    )
}

async function loadMetricDefinitions() {
    let metricDefinitionResponse = await fetch(METRICS_URL);

    if (metricDefinitionResponse.status >= 400) {
        console.error(`Could not load basic metric definitions; ${metricDefinitionResponse.statusText}`);
        return;
    }

    let receivedMetricDefinitions = await metricDefinitionResponse.json();

    /**
        The JSON should look like:
        {
            "metric1": {
                "details": "value"
            },
            "metric2": {
                "details": "value"
            }
        }
    */
    for (let [metricName, details] of Object.entries(receivedMetricDefinitions)) {
        DMOD.evaluation.metricDefinitions[metricName] = details;
    }
}

/**
 * Finds the color that corresponds to a given value based on the declared lowest and highest colors
 *
 * @param {int} value The value to find a color for
 * @return {string} The color that corresponds to the given value
 */
function scaleColor(value) {
    if (value > 1) {
        throw "Only values between 0 and 1 inclusive may be scaled. Received " + value;
    }

    const low = parseInt(lowestColor, 16);
    const high = parseInt(highestColor, 16);

    // @todo: This doesn't actually scale - something got lost in translation scaling from low-high red,
    //      low-high green, and low-high blue and the algorithm for it is hard to find. There is a good chance
    //      that the implicit minimum is black

    const [lowRed, lowGreen, lowBlue] = colorToArray(low);
    const [highRed, highGreen, highBlue] = colorToArray(high);

    const highScaler = 1 - value;
    const scaledRed = Math.round(highRed * value);
    const scaledGreen = Math.round(highGreen * value);
    const scaledBlue = Math.round(highBlue * value);

    let newColor = Number((scaledRed << 16) + (scaledGreen << 8) + scaledBlue).toString(16);

     while (newColor.length < 6) {
        newColor = "0" + newColor;
     }

     newColor = "#" + newColor;

     return newColor;
}

/*
 * Breaks down a 16-bit number into red, green, and blue values
 *
 * @param {Number} colorNumber A 16-bit number to break down into red, green, and blue values
 * @return {Array} An array of 3 values broken out of the colorNumber, the first being red, the second being green,
 *                 and the third being blue
 */
function colorToArray(colorNumber) {
    const red = colorNumber >> 16;
    const green = (colorNumber >> 8) % 256;
    const blue = colorNumber % 256;

    return [red, green, blue];
}

function assignEventHandlers() {
    $("#acknowledge-error-icon").on("click", () => {
        updateError();
    });

    $("#evaluation_id").on("change", syncNameChange);

    $("#search-button").on("click", showSearchPopup);

    $("#evaluation-save").on("click", (event) => {showPopup(event, 'save-dialog')});

    $("#reconnect-button").on("click", launchClient);

    $("#get-digest").on("click", showDigestPopup);

    $("#map-geometry-button").on("click", addGeometry);

    $("#save-definition").on("click", saveDefinition);

    $("#search-by-author").on("change", filterDefinitions);

    $("#search-by-name").on("change", filterDefinitions);

    $("#search-by-description").on("change", filterDefinitions);

    $("#select-search-button").on("click", selectPreexistingDefinition);

    $("#download-digest-button").on("click", getDigest);

    $("#evaluation-submit").click(submit_evaluation);

    $("#template-button").on("click", showTemplatePopup);

    $("#select-template-button").on("click", showTemplateApplicationPopup);

    $("#copy-template-button").on("click", copyTemplateToClipboard);

    $("#copy-template-name-button").on("click", copyTemplateNameToClipboard);

    $("#insert-template-button").on("click", insertTemplate);

    $(".close-button").on("click", closePopups);

    $("#validate-button").on(
        "click",
        async (event) => {
            const configuration = DMOD.code.getCode("editor");
            await showWaitingPopup("Validating Configuration...");
            DMOD.evaluation.client.validateConfiguration(
                configuration
            );
        }
    );
}

function attachTabChangedHandlers() {
    tabChangedHandlers['digest-div'] = [];

    tabChangedHandlers['digest-div'].push(
        event => {
            const digestEditor = DMOD.code.getEditor("digest");

            CodeMirror.commands.foldAll(digestEditor);
            digestEditor.foldCode({line:0, ch: 0}, null, "unfold");
        }
    )
}

widgetInitializers.push(
    () => {
        const tabElements = $("#tabs");
        tabElements.tabs({
            active: 0,
            activate: resizeTabs,
        });
        tabElements.tabs("refresh");
    }
);



widgetInitializers.push(
    () => $(".template-selected-button").hide()
)

widgetInitializers.push(initializeTemplateTree);

pageChangedHandlers.push(
    () => {
        let newHeight = $("#search-button").css("height");
        const evaluationIDInput = $("#evaluation_id");

        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("margin-top"));
        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("border-top-width"));
        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("padding-top"));
        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("padding-bottom"));
        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("border-bottom-width"));
        newHeight = subtractUnitStrings(newHeight, evaluationIDInput.css("margin-bottom"));

        evaluationIDInput.css("height", newHeight);
    }
);

pageChangedHandlers.push(DMOD.code.resizeCodeViews);

// Initialize the map when the page starts up
startupScripts.push(
    function () {
        DMOD.evaluation.visualizationMap = initializeActiveMap("map", mapOptions);
    }
);

resizeHandlers.push(resizeTabs);

startupScripts.push(
    async function() {
        assignEventHandlers();
        $(".error-box").hide();
        await showPopup(null, "connecting-modal");
        initializeFields();

        resizeTabs();

        // Connect to service
        await launchClient();

        await closePopups(null);
    }
);

// Add geometry options to the geometry selector when the page starts up
startupScripts.push(populateGeometrySelector);

// Record available metric definitions
startupScripts.push(loadMetricDefinitions);
startupScripts.push(attachTabChangedHandlers);
