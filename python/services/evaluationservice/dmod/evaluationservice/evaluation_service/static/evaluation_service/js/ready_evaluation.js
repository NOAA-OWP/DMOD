// global
var crosswalk = {};
let control_layers = {};
let active_control_layers = [];
let metrics = [];
var map_controls;
var layer;
let visualizationMap = null;

const digest = {
    digest: []
};

const metricDefinitions = {};

// Debug Flags - Set to true to stop upon execution

// Debug the 'UpdateCrosswalk' function
var debugUpdateCrosswalk = false;

// Debug the 'updateMapMetrics' function
var debugUpdateMapMetrics = true;

// Debug the 'showPopup' function
var debugShowPopup = false;

// Debug the 'showSearchPopup' function
var debugShowSearchPopup = false;

// Debug the 'debugLoadPreexistingDefinition' function
var debugLoadPreexistingDefinition = false;

// Debug the 'plotMapLayers' function
var debugPlotMapLayers = false;

// Debug the 'getShapeStyle' function
var debugShapeStyle = false;

// Debug the 'debugMapLoader' function
var debugMapLoad = false;

function recordMessage(dateAndTime, message) {
    if ($("#record-messages").val() == "on") {
        message['time'] = dateAndTime;
        digest.digest.push(message);
    }
}

function getDigestFileName() {
    var formatter = getDateFormatter();
    var channel = $("#channel-name").text();

    var filename = `Digest_for_${channel}_at_${formatter.format(new Date())}.json`
    // filename is now 'Digest_for_channel name_at_2022-06-15, 11:38 CDT.json'

    filename = filename.replaceAll(",", "");
    // filename is now 'Digest_for_channel name_at_2022-06-15 11:38 CDT.json'

    filename = filename.replaceAll(" ", "_");
    // filename is now 'Digest_for_channel_name_at_2022-06-15_11:38_CDT.json'

    filename = filename.replaceAll(":", ".");
    // filename is now 'Digest_for_channel_name_at_2022-06-15_11.38_CDT.json'

    return filename;
}

function getJSONReplacer() {
    return null;
}

function getExpectedIndentSpaces() {
    return 4;
}

function filterDigest() {
    let filteredDigest = [];
    let eventsToInclude = $("#digest-event-selectors input:checked").toArray().map((element) => {return element.name;});

    for (message of digest.digest) {
        if (message.event && eventsToInclude.includes(message.event)) {
            filteredDigest.push(message);
        }
    }

    return filteredDigest;
}

function getDigest(event) {
    if (event) {
        event.preventDefault();
    }

    var filteredDigest = filterDigest();

    if (filteredDigest.length == 0) {
        $("#digest-error-message").text("No messages in the digest match the given filter.");
        return;
    }

    var fileType = "application/json";

    var data = JSON.stringify(filteredDigest, getJSONReplacer(), getExpectedIndentSpaces());
    var file = new Blob([data], {type: fileType});
    var fileUrl = URL.createObjectURL(file);

    var fileAnchor = document.createElement("a");
    fileAnchor.href = fileUrl;
    fileAnchor.download = getDigestFileName();
    document.body.appendChild(fileAnchor);
    fileAnchor.click();

    setTimeout(function() {
        document.body.removeChild(fileAnchor);
        window.URL.revokeObjectURL(fileUrl);
    }, 0);

    closePopups();
}

function submit_evaluation(event) {
    if (event) {
        event.preventDefault();
    }

    var editorData = getCodeView("editor");

    var arguments = {
        "action": "launch",
        "action_parameters": {
            "instructions": editorData.view.getValue(),
            "evaluation_name": document.getElementById("evaluation_id").value
        }
    };

    socket.send(JSON.stringify(arguments), getJSONReplacer(), getExpectedIndentSpaces());

    if (!editorData.view.getOption("readonly")) {
        editorData.view.setOption("readonly", true);
    }

    event.target.disabled = true;

    $("#tabs").tabs("option", "active", 1);
}

function switchTabs(event, tabID) {
    $(".tab").hide();
    $("#" + tabID).show();

    codeViews.forEach((codeView) => {
        if (codeView.tab == tabID) {
            var area = document.getElementById(codeView.container);
            var height = area.offsetHeight;
            codeView.view.setSize(null, height);
        }
    });
}

function resizeCodeView(codeViewName) {
    codeViews.forEach((codeView) => {
        if (codeView.tab == codeViewName) {
            var area = document.getElementById(codeView.container);
            var height = area.offsetHeight;
            codeView.view.setSize(null, height);
        }
    });
}

function tabActivated(event, {newTab, oldTab, newPanel, oldPanel}) {
    var newTabID = newPanel[0].id;
    resizeTabs();
}

function resizeTabContent(panel) {
    var headerSelector = `#${panel.id} .tab-header`;
    var contentSelector = `#${panel.id} .tab-content`;
    var footerSelector = `#${panel.id} .tab-footer`;

    var header = $(headerSelector)[0];
    var content = $(contentSelector)[0];
    var footer = $(footerSelector)[0];

    var newContentHeight = panel.offsetHeight - (panel.offsetTop + header.offsetHeight + footer.offsetHeight);

    content.style.height = `${newContentHeight}px`;
}

function resizePanel(panelIndex) {
    var tabInstance = $("#tabs").tabs("instance");
    var panel = tabInstance.panels[panelIndex];
    var tabsElement = tabInstance.element[0];

    var tabsElementTop = tabsElement.offsetTop;
    var tabsElementHeight = tabsElement.offsetHeight;

    panel.style.height = `${tabsElementHeight - tabsElementTop}px`;

    resizeTabContent(panel);

    var panelID = panel.id;

    resizeCodeView(panelID);

    var mapSelector = `#${panelID} #${visualizationMap.getContainer().id}`;

    if ($(mapSelector).length) {
        visualizationMap.updateSize();
    }
}

function resizeTabs() {
    var tabs = $("#tabs");
    tabs.height(tabs.parent().height());

    var activeTabNumber = $("#tabs").tabs("option", "active");

    resizePanel(activeTabNumber);
}

function toMapTab(event, tabID) {
    switchTabs(event, 'map-div');
    visualizationMap.updateSize();
}

function getCodeView(name) {
    for (const codeView of codeViews) {
        if (codeView.name == name) {
            return codeView;
        }
    }
}

function syncNameChange(event) {
    $("#evaluation_name").val(event.target.value);
}

function updateError(message) {
    var errorBox = $("#general-error-box");

    if (message) {
        errorBox.show();
        document.getElementById("error-message").textContent = message;
    }
    else {
        errorBox.hide();
    }
}

function getWebSocketURL() {
    var websocket_route = $("#channel-url").val();
    var websocket_url = `ws://${window.location.host}${LAUNCH_URL}`;
    return websocket_url;
}

function registerEvent(eventName, handler, callCount) {
    if (callCount == null || typeof(callCount) != 'number') {
        callCount = 1;
    }

    var registration = {
        "count": callCount,
        "handle": handler
    }

    if (eventName in eventHandlers) {
        eventHandlers[eventName].push(registration);
    }
    else {
        eventHandlers[eventName] = [registration];
    }
}

function updateCrosswalk(event, msg) {
    /*
    msg will look like:
    {
        "event": "crosswalk",
        "type": "send_message",
        "time": "2022-12-08 02:20:39 PM CST",
        "data": {
            "prediction_location": {
                "0": "cat-67",
                "1": "cat-27",
                "2": "cat-52"
            },
            "observation_location": {
                "0": "02146562",
                "1": "0214655255",
                "2": "0214657975"
            }
        }
    }
    */
    if (debugUpdateCrosswalk) {
        debugger;
    }
    const { data: {prediction_location, observation_location}} = msg
    for (var location_index in prediction_location) {
        const predictedLocation = prediction_location[location_index];
        const observedLocation = observation_location[location_index];
        crosswalk[predictedLocation] = observedLocation;
    }
}

function updateMapMetrics(event, msg){
    /* msg will look like:
    {
        "event": "metric",
        "type": "send_message",
        "time": "2022-12-09 08:33:42 AM CST",
        "data": {
            "metric": "Pearson Correlation Coefficient",
            "description": "A measure of linear correlation between two sets of data",
            "weight": 18,
            "total": 36.99786170539468,
            "scores": {
                "total": 36.99786170539468,
                "grade": "1.00%",
                "scores": {
                    "p50_va": {
                        "value": 0.6851455871369385,
                        "scaled_value": 12.332620568464893,
                        "sample_size": 697,
                        "failed": false,
                        "weight": 1
                    },
                    "p75_va": {
                        "value": 0.6851455871369385,
                        "scaled_value": 12.332620568464893,
                        "sample_size": 697,
                        "failed": false,
                        "weight": 10
                    },
                    "p80_va": {
                        "value": 0.6851455871369385,
                        "scaled_value": 12.332620568464893,
                        "sample_size": 697,
                        "failed": false,
                        "weight": 5
                    }
                }
            },
            "metadata": {
                "observed_location": "0214657975",
                "predicted_location": "cat-52"
            }
        }
    }
    */
    if (debugUpdateMapMetrics) {
        debugger;
    }

    const { data: {metric}} = msg;

    // add map control for each metric type
    if (!Object.hasOwn(control_layers, metric)){
        const layer_stub = L.layerGroup([]);
        control_layers[metric] = layer_stub;
        if (map_controls !== undefined){
            map_controls.remove()
        }

        map_controls = L.control.layers({}, control_layers).addTo(visualizationMap.getMap());
    }
    metrics.push(msg)
}

function updateLocation(event, message) {
    var data = message.data;
    var predictedLocation = data.predicted_location;

    var feature = visualizationMap.getFeature(predictedLocation);

    if (feature) {
        var locationScore = data.scores.scaled_value;
        var grade = data.scores.grade;
        var gradeColor = getGradeColor(grade);
        var color = scaleColor(locationScore);

        feature.setStyle({
            "fillColor": gradeColor,
            "color": gradeColor,
        });

        updateLocationPopup(feature, data);
        updateLocationTooltip(feature, data);
    }
}

function getLocationMetricColumnCount(metricCount) {
    if (metricCount == 1 || metricCount == null || metricCount <= 0) {
        return 1;
    }
    else if (metricCount == 2) {
        return 2;
    }
    else if (metricCount == 4) {
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

    var grade = getGradeLetter(data.scores.grade);
    var text = `${data.observed_location} vs ${data.predicted_location}: ${grade}`;

    featureLayer.bindTooltip(text);
}

function updateLocationPopup(featureLayer, data) {
    if (featureLayer == null) {
        return;
    }

    var wrapperDiv = document.createElement("div");
    wrapperDiv.classList.add("freature-result-wrapper");

    var content = document.createElement("fieldset");
    content.classList.add("feature-result-fields");

    wrapperDiv.appendChild(content);

    var legend = document.createElement("legend");
    legend.classList.add("feature-result-legend");

    legend.textContent = `${data.observed_location} vs ${data.predicted_location}`;

    content.appendChild(legend);

    var metrics = Object.entries(data.scores.scores);

    var columnCount = getLocationMetricColumnCount(metrics.length);

    var gridColumnTemplate = "";

    for (let i = 0; i < columnCount; i++) {
        gridColumnTemplate = gridColumnTemplate + "auto ";
    }

    content.style['grid-template-columns'] = gridColumnTemplate;

    for (let [metricName, metricData] of metrics) {
        var metricFieldSet = document.createElement("fieldset");
        metricFieldSet.classList.add("metric-result-fields");

        if (metricName in metricDefinitions) {
            metricFieldSet.setAttribute("title", metricDefinitions[metricName].description);
        }

        var metricLegend = document.createElement("legend");
        metricLegend.classList.add("metric-result-legend");

        metricLegend.textContent = metricName;

        metricFieldSet.appendChild(metricLegend);

        var metricGrade = (metricData.scaled_value / metricData.weight * 100.0).toFixed(2);
        var gradeMarkup = `<span class="metric-result-grade"><b>Grade</b>: ${metricGrade}%`;
        metricFieldSet.appendChild(htmlToElement(gradeMarkup));

        metricFieldSet.appendChild(document.createElement("br"));

        var weightMarkup = `<span class="metric-result-weight"><b>Weight</b>: ${metricData.weight}</span>`;
        metricFieldSet.appendChild(htmlToElement(weightMarkup));

        metricFieldSet.appendChild(document.createElement("br"));
        metricFieldSet.appendChild(document.createElement("hr"));

        var thresholdTable = document.createElement("table");
        thresholdTable.classList.add("metric-result-threshold-table");

        var headerRow = document.createElement("tr");
        headerRow.appendChild(document.createElement("th"));

        var gradeColumn = document.createElement("th");
        gradeColumn.classList.add("metric-result-grade-column");
        gradeColumn.classList.add("metric-result-grade-column-header");
        gradeColumn.textContent = "Grade";

        headerRow.appendChild(gradeColumn);

        var weightColumn = document.createElement("th");
        weightColumn.classList.add("metric-result-weight-column");
        weightColumn.classList.add("metric-result-weight-column-header");
        weightColumn.textContent = "Weight";

        headerRow.appendChild(weightColumn);

        thresholdTable.appendChild(headerRow);

        for (var entry of Object.values(metricData.thresholds)) {
            var thresholdEntryRow = document.createElement("tr");

            var thresholdNameCell = document.createElement("th");
            thresholdNameCell.classList.add("metric-result-threshold-name-cell");
            thresholdNameCell.textContent = entry.threshold;

            thresholdEntryRow.appendChild(thresholdNameCell);

            var thresholdGradeCell = document.createElement("td");
            thresholdGradeCell.classList.add("metric-result-grade-column");

            thresholdGradeCell.textContent = `${entry.grade.toFixed(2)}%`;

            thresholdEntryRow.appendChild(thresholdGradeCell);

            var thresholdWeightCell = document.createElement("td");
            thresholdWeightCell.classList.add("metric-result-weight-column");
            thresholdWeightCell.textContent = entry.weight;

            thresholdEntryRow.appendChild(thresholdWeightCell);

            thresholdTable.appendChild(thresholdEntryRow);
        }

        metricFieldSet.appendChild(thresholdTable);
        content.appendChild(metricFieldSet);
    }

    var finalGradeMarkup = `<h2 class="feature-result-grade">Grade: ${data.scores.grade.toFixed(2)}%</h2>`;
    wrapperDiv.appendChild(htmlToElement(finalGradeMarkup));

    var popupOptions = {
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
    var color = null;

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
            if (gradeLetter != 'F') {
                console.warn(`Defaulting to the color for F; ${gradeLetter} is not a valid letter grade.`);
                var stackError = new Error();
                console.warn(stackError.stack);
            }
            color = "d12828";
    }

    if (color[0] != "#") {
        color = `#${color}`;
    }

    return color;
}

function receivedSocketMessage(response) {
    var raw_data = JSON.parse(response.data);
    var event = "";

    if ("event" in raw_data) {
        event = raw_data.event;
    }

    var errored = raw_data.data
        && raw_data.data.message
        && (raw_data.event == "error" || raw_data.response_type == "error" || raw_data.type == "error");

    if (errored) {
        updateError(raw_data.data.message);
    }

    if (errored && raw_data.event == "launch") {
        $("#evaluation-submit").prop("disabled", false);
    }

    var data = JSON.stringify(raw_data, getJSONReplacer(), getExpectedIndentSpaces());
    messageView = getCodeView("messages");
    var digestView = getCodeView("digest");

    if (digestView && digestView.view) {
        var currentDigest = digestView.view.getValue();

        if (currentDigest.length > 0) {
            currentDigest += `\n${data}`;
        }
        else {
            currentDigest = data;
        }

        digestView.view.setValue(currentDigest);
    }

    if (messageView && messageView.view) {
        messageView = messageView.view;
        var currentDate = new Date().toLocaleString();
        recordMessage(currentDate, raw_data);
        var newMessage = messageView.getValue();
        newMessage += `\n//${Array(200).join("=")}\n\n// [${currentDate}]:\n\n${data}\n\n`

        messageView.setValue(newMessage);
        messageView.scrollIntoView(messageView.lastLine());
        $("#last-updated").text(currentDate);
        var updateCount = Number($("#message-count").text()) + 1;
        $("#message-count").text(updateCount);
    }

    if (event in eventHandlers) {
        var handlers = eventHandlers[event];
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
        socket = new WebSocket(getWebSocketURL());
    } catch (error) {
        alert(error.message);
        updateError(error.message);
        return;
    }

    socket.onopen = function (response) {
        var currentDate = new Date().toLocaleString();
        $("#connection-time").text(currentDate);
        $("#connected-edit-buttons").show();
        $("#disconnected-edit-buttons").hide();
    };
    socket.onmessage = receivedSocketMessage;

    socket.onerror = function(response) {
        updateError(response.data);
    };

    socket.onclose = function(event) {
        $("#connected-edit-buttons").hide();
        $("#disconnected-edit-buttons").show();
    };
};

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
    var editView = getCodeView("editor");

    if (editView == null) {
        throw "An editor could not be found from which to get instructions from."
    }

    var parameters = {
        "action": "save",
        "action_parameters": {
            "author": $("#author").val(),
            "name": $("#evaluation_name").val(),
            "description": $("#description").val(),
            "instructions": editView.view.getValue()
        }
    }

    payload = JSON.stringify(parameters, getJSONReplacer(), getExpectedIndentSpaces());
    socket.send(payload);
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
    var has_filter = false;
    var search_arguments = {};
    // #1
    //implement the search where it will ask the server for definitions and register an action to render them
    var author = $("#search-by-author").val();

    if (author) {
        search_arguments.author = author.trim();
        has_filter = true;
    }

    var name = $("#search-by-name").val();

    if (name) {
        search_arguments.name = name.trim();
        has_filter = true;
    }

    var description = $("#search-by-description").val();

    if (description) {
        search_arguments.description = description;
        has_filter = true;
    }

    var payload = {
        "action": "search"
    };

    if (has_filter) {
        payload.action_parameters = search_arguments;
    }

    socket.send(JSON.stringify(payload), getJSONReplacer(), getExpectedIndentSpaces());
}

function renderDefinitions(event, data) {
    // #2
    //implement the rendering of definitions within the table named 'search-table'

    if (data.response_type == "error") {
        $("#search-error-message").text(data.message);
        $("#search-errors").show();
        return;
    }

    $("#search-errors").hide();

    var searchTableBody = document.getElementById("search-table-body");

    while (searchTableBody.firstChild) {
      searchTableBody.removeChild(searchTableBody.firstChild);
    }

    for (const definition of data.data) {
        var row = document.createElement("tr");
        row.id = `definition-${definition.identifier}`;
        row.classList.add("search-row");
        row.setAttribute("identifier", definition.identifier);
        row.onclick = selectDefinition

        var authorCell = document.createElement("td");
        authorCell.id = `${definition.identifier}-author`;
        authorCell.classList.add("author-cell");
        authorCell.classList.add("search-cell");
        authorCell.textContent = definition.author.trim();
        authorCell.setAttribute("identifier", definition.identifier);

        row.appendChild(authorCell);

        var nameCell = document.createElement("td");
        nameCell.id = `${definition.identifier}-name`;
        nameCell.classList.add("name-cell");
        nameCell.classList.add("search-cell");
        nameCell.textContent = definition.name.trim();
        nameCell.setAttribute("identifier", definition.identifier);

        row.appendChild(nameCell);

        var descriptionCell = document.createElement("td");
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
}

function selectDefinition(event) {
    // #3
    //implement handler that will select the pk of the row that was clicked
    $(".search-row").removeClass("definition-selected");
    var identifier = event.target.getAttribute("identifier");

    if (identifier == $("#selected-definition").val()){
        $("#selected-definition").val(null);
        document.getElementById("select-search-button").disabled = true;
        return;
    }
    $("#selected-definition").val(identifier);

    var row = event.target;

    if (event.target.tagName == "TD") {
        row = event.target.parentElement;
    }

    row.classList.add("definition-selected");
    document.getElementById("select-search-button").disabled = false;
}

function selectPreexistingDefinition(event) {
    // #5
    //implement handler that will query the socket for the definition and register a handler to insert it into the editor
    var identifier = $("#selected-definition").val();

    if (identifier) {
        request = {
            "action": "get_saved_definition",
            "action_parameters": {
                "identifier": identifier
            }
        }
        socket.send(JSON.stringify(request), getJSONReplacer(), getExpectedIndentSpaces());
    }
    else {
        $("#search-errors").show();
        $("#search-error-message").text("Cannot select a definition; there isn't one selected.")
    }
}

function showPopup(event, popupID) {
    if (debugShowPopup) {
        debugger;
    }
    if (event) {
        event.preventDefault();
    }

    $(".popup").hide();

    $("#page-modal").show();
    $("#" + popupID).show();
}

function showSearchPopup(event) {
    if (debugShowSearchPopup) {
        debugger;
    }
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

    if (digest.digest.length == 0) {
        updateError("There are no items in the digest to download.");
    }
    else {
        var uniqueEvents = [];

        for (const message of digest.digest) {
            if (!uniqueEvents.includes(message.event)) {
                uniqueEvents.push(message.event);
            }
        }

        var fieldArea = document.getElementById("digest-event-selectors");

        while (fieldArea.firstChild) {
            fieldArea.removeChild(fieldArea.firstChild);
        }

        for (const uniqueEvent of uniqueEvents) {
            var checkbox = document.createElement("input");
            checkbox.id = uniqueEvent + "-event";
            checkbox.name = uniqueEvent;
            checkbox.type = "checkbox";
            checkbox.setAttribute("checked", true);

            var label = document.createElement("label");
            label.textContent = uniqueEvent;
            label.for = uniqueEvent + "-event";

            var newLine = document.createElement("br");

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
    if (debugLoadPreexistingDefinition) {
        debugger;
    }

    if (responseData.response_type == "error") {
        // @todo Record error to the popup
        return;
    }

    var editorView = getCodeView("editor");

    // The definition will be nested under the 'data' property of the response, so go ahead and pull that out
    var definition = responseData.data.definition;

    // The definition will most likely be an Object, but we can only load strings into the editor.
    // Convert the to a string and format it to make it easy to read in the editor
    if (typeof(definition) == 'object') {
        definition = JSON.stringify(definition, getJSONReplacer(), getExpectedIndentSpaces());
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
 * @param {String} The url to request data from
 * @return {Object} The data retrieved from the server. `null` will be returned if the request failed
 **/
function getServerData(serverUrl) {
    // Create an array to store possibly retrieved data
    // This is to be used as a catcher's mitt from the handler of the response
    var data = [];

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
    if (data.length == 0) {
        return null;
    }

    // There will be at most one item in the array, so return the first element
    return data[0];
}

/**
 * Gets a listing of options available for geometry and populates the selector with them
 **/
function populateGeometrySelector() {
    var geometryOptions = getServerData(geometryEndpoint);
    var selector = document.getElementById("map-geometry-selector");

    for (var geometryOption of geometryOptions) {
        var option = document.createElement("option");
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

    var selector = document.getElementById("map-geometry-selector");

    if (!geometryEndpoint.endsWith("/")){
        geometryEndpoint = geometryEndpoint + "/";
    }

    var url = geometryEndpoint + selector.value;

    var geometry = getServerData(url);

    visualizationMap.clear();
    visualizationMap.plotGeoJSON(geometry);

    var locationScores = digest.digest.filter(entry => entry.event == "location_scores");

    for (let locationScore of locationScores) {
        updateLocation(null, locationScore);
    }
}

/**
 * Get appropriate styling for a geojson shape
 *
 * @param {Object} feature The feature to inspect
 * @return {Object} Styling information for the feature. Will use specific line styling if the feature is a line
 **/
function getShapeStyle(feature) {
    if (debugShapeStyle) {
        debugger;
    }
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return lineStyle;
    }

    return layerStyle;
}

/**
 * Populate fields for editing with previous values and configure fields to update their values for later use
 */
function initializeFields() {
    var editorView = getCodeView("editor");

    var author = sessionStorage.getItem("author");

    // Set the value of the author field to the previous value if one was stored
    if (author) {
        $("#author").val(author);
    }

    // Try to find any previous code that was stored in the editor
    var code = sessionStorage.getItem("code");

    // Set the code in the editor to that of the previously stored value
    if (code) {
        editorView.view.setValue(code);
    }

    // Register handlers to save values to session on edit
    editorView.view.on("change", (event) => {
        var ev = getCodeView("editor");
        sessionStorage.setItem("code", ev.view.getValue());
    });

    $("#author").on(
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
        metricDefinitions[metricName] = details;
    }
}

function extract_metric_fields(data){
    const location = data.metadata.predicted_location
    const observed_location = data.metadata.observed_location
    const metric = data.metric
    const aggregated_value = data.total
    const grade = data.scores.grade
    const threshold_values = Object.entries(data.scores.scores).map(([key, value]) => ({threshold: key, value: value.value}))
    return {location, metric, grade, value: aggregated_value, threshold_values, observed_location}
}

function groupby_metric(data){

    // ...variable is an unpacking operation, like *args or **kwargs
    return data.filter(item => item.event == "metric")
                            .map(({data}) => extract_metric_fields(data))
                            .reduce((grouped_by_metric, item) => ({
                                ...grouped_by_metric,
                                [item.metric]: [...(grouped_by_metric[item.metric] || []), item]
                            }), {});
}

// build map of {location-id: popup text} for a list of selected metrics
function build_popup_map(selected_metrics, grouped_metrics){
    return selected_metrics.reduce((ids, metric) => {
        const records = grouped_metrics[metric]
        const reduced = records.reduce((metric_records, record) => {
            let current_text = "";
            let location_text = `Prediction Location: ${record.location}<br>`
            let observed_location_text = `Observation Location: ${record.observed_location}<br>`

            // check if metrics already added for location
            if (Object.hasOwn(ids, record.location)){
                current_text = `${ids[record.location]}<br>`
                location_text = ""
                observed_location_text= ""
            }

            const popup_text = `${location_text}${observed_location_text}${current_text}Metric: ${record.metric}<br>Grade: ${record.grade}`

            // ...variable is an unpacking operation, like *args or **kwargs
            return {...metric_records, [record.location]: popup_text}
        }, {})


        // ...variable is an unpacking operation, like *args or **kwargs
        return {...ids, ...reduced}
    }, {})
}

function update_popups(map, layer_group, popup_map){
    layer_group.eachLayer(l => {
        const feature_id = l.feature.id
        l.bindPopup(popup_map[feature_id])
        l.addTo(map)
    })
}

function loadGeometry(name) {
    var crosswalk = getServerData("crosswalk/"+name);

    var addTooltip = function(feature, layer) {
        if ("id" in feature) {
            layer.bindTooltip(feature["id"]);
        }
        else if ("properties" in feature && "Name" in feature["properties"]) {
            layer.bindTooltip(feature['properties']['Name']);
        }
    }

    var buildProperties = function(feature, layer) {
        layer.bindPopup(propertiesToHTML(feature, crosswalk), {"maxWidth": 2000})
        addTooltip(feature, layer);
    };

    var addDocument = function(document) {
        var layer = L.geoJSON(
            document,
            {
                onEachFeature: buildProperties,
                style: getShapeStyle,
                pointToLayer: layerCreation
            }
        ).addTo(visualizationMap);
    }

    addDocument(crosswalk)

    var url = "fabric/" + name;
    $.ajax(
        {
            url: url,
            type: "GET",
            data: {
                "fabric": name
            },
            error: function(xhr, status, error) {
                console.error(error);
            },
            success: function(result, status, xhr) {
                if (result) {
                    addDocument(result);
                }
            }
        }
    );
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

    var newColor = Number((scaledRed << 16) + (scaledGreen << 8) + scaledBlue).toString(16);

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

// Initialize the map when the page starts up
startupScripts.push(
    function () {
        visualizationMap = initializeActiveMap("map", mapOptions);
    }
);

startupScripts.push(
    function() {
        $(".error-box").hide();
        showPopup(null, "connecting-modal");
        codeViews.forEach((codeView) => {
            var editorArea = $("textarea" + codeView.textarea)[0];
            codeView.view = CodeMirror.fromTextArea(
                editorArea,
                codeView.config
            );
        });
        $("#tabs").tabs({
            active: 0,
            activate: tabActivated,
        });
        $("#tabs").tabs("refresh");
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
