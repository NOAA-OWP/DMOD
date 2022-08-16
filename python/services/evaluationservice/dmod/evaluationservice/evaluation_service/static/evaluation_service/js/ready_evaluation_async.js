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

    socket.send(JSON.stringify(arguments));

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
    alert("saveDefinition has not been implemented, yet.")
    closePopups(event);
}

function showPopup(event, popupID) {
    if (event) {
        event.preventDefault();
    }

    $(".popup").hide();

    $("#page-modal").show();
    $("#" + popupID).show();
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

    switchTabs(null, "edit-div");

    $("#evaluation-submit").click(submit_evaluation);

    // Connect to service
    connectToSocket();

    closePopups(null);
});