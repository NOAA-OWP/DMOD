var startup_scripts = [];
var crosswalk = {};

function getDateFormatter() {
    var channel = $("#channel-name").text();
    var formatterOptions = {
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    };

    // Base formatter rules based on Canada since it'll yield values in the right order and characters
    // e.g. YYYY-DD-MM where en-us is DD/MM/YYYY
    var formatter = new Intl.DateTimeFormat('en-ca', formatterOptions);

    return formatter;
};

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

    switchTabs(event, "message-div");
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

function updateCrosswalk(event, data) {
/*
data will look like:
{
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
*/
    for (var location_index in data.prediction_location) {
        var predictedLocation = data.prediction_location[location_index];
        var observedLocation = data.observation_location[location_index];
        crosswalk[predictedLocation] = observedLocation;
    }
}

function addMapHandlers() {
    registerEvent(
        "crosswalk",
        updateCrosswalk
    );
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
    };
    socket.onmessage = function (response) {
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
    };
    socket.onerror = function(response) {
        updateError(response.data);
    }
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

        var lastModifiedCell = document.createElement("td");
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

function loadPreexistingDefinition(event, responseData) {
    debugger;

    if (responseData.response_type == "error") {
        // Record error to the popup
        return;
    }
    var editorView = getCodeView("editor");

    var definition = responseData.data.definition;

    if (typeof(definition) == 'object') {
        definition = JSON.stringify(definition, getJSONReplacer(), getExpectedIndentSpaces());
    }

    editorView.view.setValue(definition);
    $("#evaluation_id").val(responseData.data.name.trim());
    closePopups(null);
    switchTabs(null, "edit-div");
}



function getServerData(serverUrl) {
    var data = [];

    $.ajax(
        {
            url: serverUrl,
            type: 'GET',
            async: false,
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                data.push(result);
            }
        }
    );

    if (data.length == 0) {
        return null;
    }

    return data[0];
}

function layerCreation(geoJsonPoint, latlng) {
    var colorIndex = 0;

    return L.circleMarker(latlng);
}

function plotMapLayers(featureDocuments, map) {
    var layers = [];

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

    var addFeature = function(featureDocument) {
        var layer = L.geoJSON(
            featureDocument.features,
            {
                onEachFeature: buildProperties,
                style: function() {return layerStyle;},
                pointToLayer: layerCreation
            }
        ).addTo(map);
        layers.push(layer);
    }

    featureDocuments.forEach(featureDocument => addFeature(featureDocument));
    return layers;
}

function propertiesToHTML(geojson, xwalk) {
    var properties = geojson.properties;
    var markup = "";
    if ("Name" in properties) {
        markup += "<h3>" + properties.Name + "</h3>";
    }
    else if ("id" in geojson) {
        markup += "<h3>" + geojson.id + "</h3>";
    }

    if (geojson.id in xwalk) {
        var cross_walk = xwalk[geojson.id];
        if ("COMID" in cross_walk) {
            var comids = cross_walk['COMID'];
            markup += "<h4>COMID</h4>";
            markup += "<ul>";
            for (comid of comids) {
                markup += "<li>" + comid + "</li>";
            }
            markup += "</ul>";
        }
    }

    markup += "<table style='border-spacing: 8px'>";

    var propertyKeys = [];

    for (const property in properties) {
        var propertyIsNotName = property.toLowerCase() != "name";
        var propertyIsNotBlank = properties[property] != null && properties[property] != "";
        var propertyIsNotAnObject = typeof properties[property] != 'object';
        if (propertyIsNotName && propertyIsNotBlank && propertyIsNotAnObject) {
            propertyKeys.push(property);
        }
    }

    var columnCount = Math.ceil(propertyKeys.length / maxRows);
    var rowCount = Math.min(propertyKeys.length, maxRows);

    for(rowIndex = 0; rowIndex < rowCount; rowIndex++) {
        if (rowIndex % 2 == 0) {
            markup += "<tr class='even-feature-property-row'>";
        }
        else {
            markup += "<tr class='odd-feature-property-row'>";
        }

        for (columnIndex = 0; columnIndex < columnCount; columnIndex++) {
            var keyIndex = rowIndex * columnCount + columnIndex;

            if (keyIndex < propertyKeys.length) {
                var key = propertyKeys[keyIndex];

                markup += "<td id='feature-property-key'><b>" + key + ":</b></td>";
                markup += "<td id='feature-property-value'>" + properties[key] + "</td>";
            }
        }

        markup += "</tr>";
    }

    markup += "</table>";
    return markup;
}

function getSelectedShapeStyle(feature) {
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return selectedLineStyle;
    }

    return selectedShapeStyle;
}

function getShapeStyle(feature) {
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return lineStyle;
    }

    return layerStyle;
}

function initializeFields() {
    var editorView = getCodeView("editor");

    var author = sessionStorage.getItem("author");

    if (author) {
        $("#author").val(author);
    }

    var code = sessionStorage.getItem("code");

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
            document.features,
            {
                onEachFeature: buildProperties,
                style: getShapeStyle,
                pointToLayer: layerCreation
            }
        ).addTo(visualizationMap);

        visualizationMap.fitBounds(layer.getBounds());
    }

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

$(function(){
    $(".error-box").hide();
    showPopup(null, "connecting-modal");
    codeViews.forEach((codeView) => {
        var editorArea = $("textarea" + codeView.textarea)[0];
        codeView.view = CodeMirror.fromTextArea(
            editorArea,
            codeView.config
        );
    });

    initializeFields();
    switchTabs(null, "edit-div");

    $("#evaluation-submit").click(submit_evaluation);

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
    startup_scripts.forEach(script => script());
});