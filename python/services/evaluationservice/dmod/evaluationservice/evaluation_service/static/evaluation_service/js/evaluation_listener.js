function clearOutput(event) {
    event.preventDefault();
    messageBox.setValue("");
};

function clearDigest(event) {
    event.preventDefault();
    digest.digest = [];
}

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

function getDigest(event) {
    event.preventDefault();

    var fileType = "application/json";
    var data = JSON.stringify(digest, getJSONReplacer(), getExpectedIndentSpaces());
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
}

function getWebSocketURL() {
    var websocket_route = $("#channel-url").val();
    var websocket_url = `ws://${window.location.host}${websocket_route}`;
    return websocket_url;
}

function connectToSocket(event) {
    if (event) {
        event.preventDefault();
    }

    try {
        socket = new WebSocket(getWebSocketURL());
    } catch (error) {
        messageBox.setValue(error.message);
        return;
    }
    socket.onopen = function (response) {
        var currentDate = new Date().toLocaleString();
        $("#connection-time").text(currentDate);
    };
    socket.onmessage = function (response) {
        var raw_data = JSON.parse(response.data);
        var data = JSON.stringify(raw_data, getJSONReplacer(), getExpectedIndentSpaces());
        var currentDate = new Date().toLocaleString();
        recordMessage(currentDate, raw_data);
        var newMessage = messageBox.getValue();
        newMessage += `\n//${Array(200).join("=")}\n\n// [${currentDate}]:\n\n${data}\n\n`
        messageBox.setValue(newMessage);
        messageBox.scrollIntoView(messageBox.lastLine());
        $("#last-updated").text(currentDate);
        var updateCount = Number($("#message-count").text()) + 1;
        $("#message-count").text(updateCount);
    };
};

function recordMessage(dateAndTime, message) {
    if ($("#record-messages").val() == "on") {
        message['time'] = dateAndTime;
        digest.digest.push(message);
    }
}

$(function(){
    var messageText = $("textarea#message-box")[0];

    messageBox = CodeMirror.fromTextArea(
        messageText,
        messageConfig
    );

    var area = document.querySelector("#message-area");
    var height = area.offsetHeight;

    messageBox.setSize(null, height);

    $("#connect-button").click(connectToSocket);
    $("#clear-digest").click(clearDigest);
    $("#get-digest").click(getDigest)

    $("#clear-button").click(clearOutput);
    $("#websocket-url-anchor").val(getWebSocketURL());
    $("#websocket-url-anchor").text(getWebSocketURL());

    connectToSocket(null);

    setInterval(function(){
        var indicator = $("#connection-status");

        if (socket == null) {
            indicator.css("color", "black");
            indicator.text("Disconnected");
            $("#connect-button").show();
        }
        else if (socket.readyState == WebSocket.CLOSED) {
            indicator.css("color", "red");
            indicator.text("Closed");
            $("#connect-button").show();
        }
        else if (socket.readyState == WebSocket.CLOSING) {
            indicator.css("color", "orange");
            indicator.text("Closing");
            $("#connect-button").hide();
        }
        else if (socket.readyState == WebSocket.CONNECTING) {
            indicator.css("color", "blue");
            indicator.text("Connecting");
            $("#connect-button").hide();
        }
        else {
            indicator.css("color", "green");
            indicator.text("Ready");
            $("#connect-button").hide();
        }
    }, 700);
});
