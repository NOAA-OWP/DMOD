import {getWebSocketURL, toJSON, downloadData} from "/static/js/utilities.js";

window.DMOD.evaluation = {
    socket: null,
    visualizationMap: null,
    eventHandlers: {
        save: [],
        error: [],
        info: []
    },
    digest: {},
    metricDefinitions: {}
}

function recordMessage(dateAndTime, message) {
    if ($("#record-messages").val() === "on") {
        const event = message['event'];
        if (!window.DMOD.evaluation.digest.hasOwnProperty(event)) {
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

function submit_evaluation(event) {
    if (event) {
        event.preventDefault();
    }

    let editorData = window.DMOD.code.getCodeView("editor");

    let parameters = {
        "action": "launch",
        "action_parameters": {
            "instructions": editorData.view.getValue(),
            "evaluation_name": document.getElementById("evaluation_id").value
        }
    };

    window.DMOD.evaluation.socket.send(toJSON(parameters));

    if (!editorData.view.getOption("readonly")) {
        editorData.view.setOption("readonly", true);
    }

    $(event.target).button("disable");

    $("#tabs").tabs("option", "active", 1);
}

function switchTabs(event, tabID) {
    $(".tab").hide();
    $("#" + tabID).show();

    DMOD.code.resizeCodeViews(tabID);
}

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

function syncNameChange(event) {
    $("#evaluation_name").val(event.target.value);
}

function updateError(message) {
    const errorBox = $("#general-error-box");

    if (message) {
        errorBox.show();
        document.getElementById("error-message").textContent = message;
    }
    else {
        errorBox.hide();
    }
}

function registerEvent(eventName, handler, callCount) {
    if (callCount == null || typeof(callCount) != 'number') {
        callCount = 1;
    }

    const registration = {
        "count": callCount,
        "handle": handler
    }

    if (eventName in DMOD.evaluation.eventHandlers) {
        DMOD.evaluation.eventHandlers[eventName].push(registration);
    }
    else {
        DMOD.evaluation.eventHandlers[eventName] = [registration];
    }
}

function updateLocation(event, message) {
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

function updateLocationTooltip(featureLayer, data) {
    if (featureLayer == null) {
        return;
    }

    const grade = getGradeLetter(data.scores.grade);
    const text = `${data.observed_location} vs ${data.predicted_location}: ${grade}`;

    featureLayer.bindTooltip(text);
}

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

    const popupOptions = {
        "maxWidth": "900px",
        "maxHeight": "500px"
    }

    featureLayer.bindPopup(
        wrapperDiv,
        popupOptions
    );
}

function addMapHandlers() {
    registerEvent(
        "location_scores",
        updateLocation
    );
}

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
                var stackError = new Error();
                console.warn(stackError.stack);
            }
            color = "#d12828";
    }

    if (color[0] !== "#") {
        color = `#${color}`;
    }

    return color;
}

function receivedSocketMessage(response) {
    const raw_data = JSON.parse(response.data);
    let event = "";

    if ("event" in raw_data) {
        event = raw_data.event;
    }

    let errored = raw_data.data
        && raw_data.data.message
        && (raw_data.event === "error" || raw_data.response_type === "error" || raw_data.type === "error");

    if (errored) {
        updateError(raw_data.data.message);
    }

    if (errored && raw_data.event === "launch") {
        $("#evaluation-submit").prop("disabled", false);
    }

    const data = toJSON(raw_data);
    let messageView = DMOD.code.getCodeView("messages");
    let digestView = DMOD.code.getCodeView("digest");

    if (messageView && messageView.view) {
        messageView = messageView.view;
        const currentDate = new Date().toLocaleString();
        recordMessage(currentDate, raw_data);
        let newMessage = messageView.getValue();
        newMessage += `\n//${Array(200).join("=")}\n\n// [${currentDate}]:\n\n${data}\n\n`

        messageView.setValue(newMessage);
        messageView.scrollIntoView(messageView.lastLine());
        $("#last-updated").text(currentDate);

        const messageCountField = $("#message-count");
        const updateCount = Number(messageCountField.text()) + 1;
        messageCountField.text(updateCount);
    }

    if (digestView && digestView.view) {
        let digestText = toJSON(DMOD.evaluation.digest);
        digestView.view.setValue(digestText);
    }

    if (event in DMOD.evaluation.eventHandlers) {
        const handlers = DMOD.evaluation.eventHandlers[event];
        for (const handler of handlers) {
            if (typeof(handler) == 'function') {
                handler(event, raw_data);
            }
            else {
                handler.count = handler.count - 1;
                handler.handle(event, raw_data);
            }
        }
    }
}

function connectToSocket(event) {
    if (event) {
        event.preventDefault();
    }

    try {
        DMOD.evaluation.socket = new WebSocket(getWebSocketURL(LAUNCH_URL));
    } catch (error) {
        alert(error.message);
        updateError(error.message);
        return;
    }

    DMOD.evaluation.socket.onopen = function (response) {
        const currentDate = new Date().toLocaleString();
        $("#connection-time").text(currentDate);
        $("#connected-edit-buttons").show();
        $("#disconnected-edit-buttons").hide();
    };
    DMOD.evaluation.socket.onmessage = receivedSocketMessage;

    DMOD.evaluation.socket.onerror = function(response) {
        updateError(response.data);
    };

    DMOD.evaluation.socket.onclose = function(event) {
        $("#connected-edit-buttons").hide();
        $("#disconnected-edit-buttons").show();
    };
}

function closePopups(event) {
    if (event) {
        event.preventDefault();
    }
    $("#page-modal").hide();
    $(".popup").hide();
}

function saveDefinition(event) {
    if (event) {
        event.preventDefault();
    }
    const editView = DMOD.code.getCodeView("editor");

    if (editView == null) {
        throw "An editor could not be found from which to get instructions from."
    }

    const parameters = {
        "action": "save",
        "action_parameters": {
            "author": $("#author").val(),
            "name": $("#evaluation_name").val(),
            "description": $("#description").val(),
            "instructions": editView.view.getValue()
        }
    }

    const payload = toJSON(parameters);
    DMOD.evaluation.socket.send(payload);
    // Instead of closing the popup, tell it to close this popup and open a waiting popup. That popup should leave
    // when the next save event comes through.
    waitForEvent("save", `Waiting to complete saving '${parameters.action_parameters.name}'`)
}

function waitForEvent(eventName, why) {
    $("#waiting-for").text(why);
    showPopup(null, "waiting-popup");
    registerEvent(
        eventName,
        (data) => {
            closePopups();
            switchTabs("message-div");
        }
    );
}

function filterDefinitions(event) {
    let has_filter = false;
    const search_arguments = {};
    // #1
    //implement the search where it will ask the server for definitions and register an action to render them
    const author = $("#search-by-author").val();

    if (author) {
        search_arguments.author = author.trim();
        has_filter = true;
    }

    const name = $("#search-by-name").val();

    if (name) {
        search_arguments.name = name.trim();
        has_filter = true;
    }

    const description = $("#search-by-description").val();

    if (description) {
        search_arguments.description = description;
        has_filter = true;
    }

    const payload = {
        "action": "search"
    };

    if (has_filter) {
        payload.action_parameters = search_arguments;
    }

    DMOD.evaluation.socket.send(toJSON(payload));
}

function renderDefinitions(event, data) {
    // #2
    //implement the rendering of definitions within the table named 'search-table'

    const searchErrorsElement = $("#search-errors");
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

    for (const definition of data.data) {
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

        let lastModifiedCell = document.createElement("td");
        lastModifiedCell.id = `${definition.identifier}-last_modified`;
        lastModifiedCell.classList.add("last_modified-cell");
        lastModifiedCell.classList.add("search-cell");
        lastModifiedCell.textContent = definition.last_modified.trim();
        lastModifiedCell.setAttribute("identifier", definition.identifier);

        row.appendChild(lastModifiedCell);

        searchTableBody.appendChild(row);
    }

    // #4
    //NOTE: This should clear any selections
    $("#selected-definition").val(null);
}

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

function selectPreexistingDefinition(event) {
    // #5
    //implement handler that will query the socket for the definition and register a handler to insert it into the editor
    var identifier = $("#selected-definition").val();

    if (identifier) {
        const request = {
            "action": "get_saved_definition",
            "action_parameters": {
                "identifier": identifier
            }
        }
        DMOD.evaluation.socket.send(toJSON(request));
    }
    else {
        $("#search-errors").show();
        $("#search-error-message").text("Cannot select a definition; there isn't one selected.")
    }
}

function showPopup(event, popupID) {
    if (event) {
        event.preventDefault();
    }

    $(".popup").hide();

    $("#page-modal").show();
    $("#" + popupID).show();
}

function showSearchPopup(event) {
    if (event) {
        event.preventDefault();
    }

    filterDefinitions(event);
    showPopup(event, "search-popup");
}

function showDigestPopup(event) {
    if (event) {
        event.preventDefault();
    }

    if (DMOD.evaluation.digest.length === 0) {
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
            checkbox.setAttribute("checked", true);

            const label = document.createElement("label");
            label.textContent = uniqueEvent;
            label.for = uniqueEvent + "-event";

            const newLine = document.createElement("br");

            fieldArea.appendChild(checkbox);
            fieldArea.appendChild(label);
            fieldArea.appendChild(newLine);
        }

        showPopup(event, "digest-modal");
    }
}


/**
 * Load a retrieved evaluation configuration into the editor
 *
 * @param {Object} event The event that triggered the load
 * @param {Object} responseData The configuration retrieved from the server
 */
function loadPreexistingDefinition(event, responseData) {
    if (responseData.response_type === "error") {
        // @todo Record error to the popup
        return;
    }

    const editorView = DMOD.code.getCodeView("editor");

    // The definition will be nested under the 'data' property of the response, so go ahead and pull that out
    let definition = responseData.data.definition;

    // The definition will most likely be an Object, but we can only load strings into the editor.
    // Convert the to a string and format it to make it easy to read in the editor
    if (typeof(definition) == 'object') {
        definition = toJSON(definition);
    }

    editorView.view.setValue(definition);
    $("#evaluation_id").val(responseData.data.name.trim());
    closePopups(null);

    // Make sure that the editor view is showing
    switchTabs(null, "edit-div");
}


/**
 * Get data from the server
 *
 * @param {String} serverUrl The url to request data from
 * @return {Object} The data retrieved from the server. `null` will be returned if the request failed
 **/
function getServerData(serverUrl) {
    // Create an array to store possibly retrieved data
    // This is to be used as a catcher's mitt from the handler of the response
    const data = [];

    // @todo This might be a good candidate for the fetch API
    $.ajax(
        {
            url: serverUrl,
            type: 'GET',
            async: false,
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                // Push data from the server into the data array
                data.push(result);
            }
        }
    );

    // Return null if there was an error
    if (data.length === 0) {
        return null;
    }

    // There will be at most one item in the array, so return the first element
    return data[0];
}

/**
 * Gets a listing of options available for geometry and populates the selector with them
 **/
function populateGeometrySelector() {
    const geometryOptions = getServerData(GEOMETRY_URL);

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
function addGeometry(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const selector = document.getElementById("map-geometry-selector");

    if (!GEOMETRY_URL.endsWith("/")){
        GEOMETRY_URL = GEOMETRY_URL + "/";
    }

    const url = GEOMETRY_URL + selector.value;

    const geometry = getServerData(url);

    DMOD.evaluation.visualizationMap.clear();
    DMOD.evaluation.visualizationMap.plotGeoJSON(geometry);

    let locationScores = [];

    if (DMOD.evaluation.digest.hasOwnProperty("location_scores")) {
        locationScores = DMOD.evaluation.digest.location_scores;
    }

    for (let locationScore of locationScores) {
        updateLocation(null, locationScore);
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
    editorView.view.on("change", (event) => {
        const ev = DMOD.code.getCodeView("editor");
        sessionStorage.setItem("code", ev.view.getValue());
    });

    authorFields.on(
        "change",
        (event) => {
            sessionStorage.setItem("author", $("#author").val());
        }
    );
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
    for (var [metricName, details] of Object.entries(receivedMetricDefinitions)) {
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
 * Breaks down a 16 bit number into red, green, and blue values
 *
 * @param {Number} colorNumber A 16 bit number to break down into red, green, and blue values
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
        updateError(null);
    });

    $("#evaluation_id").on("change", syncNameChange);

    $("#search-button").on("click", showSearchPopup);

    $("#evaluation-save").on("click", (event) => {showPopup(event, 'save-dialog')});

    $("#reconnect-button").on("click", connectToSocket);

    $("#get-digest").on("click", showDigestPopup);

    $("#map-geometry-button").on("click", addGeometry);

    $("#save-definition").on("click", saveDefinition);

    $("#close-save-popup-button").on("click", closePopups);

    $("#close-waiting-button").on("click", closePopups);

    $("#search-by-author").on("change", filterDefinitions);

    $("#search-by-name").on("change", filterDefinitions);

    $("#search-by-description").on("change", filterDefinitions);

    $("#select-search-button").on("click", selectPreexistingDefinition);

    $("#close-search-button").on("click", closePopups);

    $("#download-digest-button").on("click", getDigest);

    $("#close-digest-popup-button").on("click", closePopups);
}

// Initialize the map when the page starts up
startupScripts.push(
    function () {
        DMOD.evaluation.visualizationMap = initializeActiveMap("map", mapOptions);
    }
);

startupScripts.push(
    function() {
        assignEventHandlers();
        $(".error-box").hide();
        showPopup(null, "connecting-modal");
        const tabElements = $("#tabs");
        tabElements.tabs({
            active: 0,
            activate: resizeTabs,
        });
        tabElements.tabs("refresh");
        initializeFields();
        //switchTabs(null, "edit-div");

        $("#evaluation-submit").click(submit_evaluation);

        resizeTabs();
        window.addEventListener("resize", resizeTabs);

        // Connect to service
        connectToSocket();

        // Register message handlers
        registerEvent(
            "search",
            renderDefinitions,
            -1
        );
        registerEvent(
            "get_saved_definition",
            loadPreexistingDefinition,
            -1
        );

        closePopups(null);
    }
);

// Add geometry options to the geometry selector when the page starts up
startupScripts.push(populateGeometrySelector);

// Add handlers to the map view when the page starts up
startupScripts.push(addMapHandlers);

// Record available metric definitions
startupScripts.push(loadMetricDefinitions);
