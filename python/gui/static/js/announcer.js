import {DataTableOptions} from "./table/DataTableOptions.js";
import {DMODTable} from "./table/DMODTable.js";
import {getWebSocketURL} from "./utilities.js";

const ANNOUNCEMENT_SOCKET_NAME = "announcer";
const SENT_MESSAGE_TABLE_NAME = "sent_message_table";

function getAnnouncementSocketVariable() {
    if (!Object.keys(window).includes("DMOD")) {
        window.DMOD = {};
    }

    if (!Object.keys(window.DMOD).includes(ANNOUNCEMENT_SOCKET_NAME)) {
        window.DMOD[ANNOUNCEMENT_SOCKET_NAME] = null;
    }

    return window.DMOD[ANNOUNCEMENT_SOCKET_NAME];
}

function setAnnouncementSocketVariable(socket) {
    if (!Object.keys(window).includes("DMOD")) {
        window.DMOD = {};
    }

    window.DMOD[ANNOUNCEMENT_SOCKET_NAME] = socket;
}

function getSentMessageTable() {
    if (!Object.keys(window).includes("DMOD")) {
        window.DMOD = {};
    }

    if (!Object.keys(window.DMOD).includes(SENT_MESSAGE_TABLE_NAME)) {
        window.DMOD[SENT_MESSAGE_TABLE_NAME] = null;
    }

    return window.DMOD[SENT_MESSAGE_TABLE_NAME];
}

function setSentMessageTable(table) {
    if (!Object.keys(window).includes("DMOD")) {
        window.DMOD = {};
    }

    window.DMOD[SENT_MESSAGE_TABLE_NAME] = table;
}

function hasOpenedConnection() {
    const socket = getAnnouncementSocketVariable();
    return socket != null && socket.readyState > 0;
}

function hasActiveConnection() {
    const socket = getAnnouncementSocketVariable();
    return socket != null && socket.readyState === 1;
}

async function connectToSocket() {
    if (hasActiveConnection()) {
        return true;
    }

    let url = getWebSocketURL(ANNOUNCER_URL);

    let attemptCount = 0;
    const attemptLimit = 5;
    const waitDelay = 100;

    setAnnouncementSocketVariable(new WebSocket(url));

    while (!hasActiveConnection() && attemptCount < attemptLimit) {
        attemptCount += 1;
        setAnnouncementSocketVariable(new WebSocket(url));
        let connected = await waitForConnection();

        if (!connected) {
            await sleep(waitDelay);
        }
    }

    return hasActiveConnection();
}

async function waitForConnection() {
    const waitLimit = 5;
    let waitCount = 0;
    let waitDelay = 100;

    while (!hasOpenedConnection() && waitCount < waitLimit) {
        await sleep(waitDelay);
        waitCount += 1;
    }

    return hasOpenedConnection();
}

async function sendData(event) {
    const data = codeViews[0].view.getValue().trim();

    if (data == null || data.length === 0) {
        return;
    }

    const connected = await connectToSocket();

    if (connected) {
        let sent = false;
        const sendTime = formatDate();

        try {
            getAnnouncementSocketVariable().send(data);
            sent = true;
        }
        catch (e) {
            console.error(`Could not send message to server because: ${e}`);
        }

        if (sent) {
            const sentRecord = {
                "sent": sendTime,
                "message": data
            };

            if (getSentMessageTable() == null) {
                createTable([sentRecord]);
            }
            else {
                getSentMessageTable().addRow(sentRecord);
            }
        }
    }
    else {
        console.error(`Could not get connection to send message through`);
    }
}

/**
 * Instantiate the table that holds records for sent messages
 * @param {{sent: string, message: string}[]?} initialRecords
 */
function createTable(initialRecords) {
    if (getSentMessageTable() == null) {
        let options = new DataTableOptions()
        options.searchable = false;
        options.useSearchBuilder = false;

        const table = new DMODTable(SENT_TABLE_NAME, initialRecords, options);
        setSentMessageTable(table);
    }
}

function registerOnClick() {
    $("#send-announcement-button").on("click", sendData);
}

function resizeAnnouncerScreen() {
    const wrapper = $("#content > fieldset");
    const parent = wrapper.parent();
    let height = parent.height();

    const marginTop = parent.css("margin-top");

    if (marginTop) {
        const amountTop = marginTop.match(/^\d+/g);
        if (amountTop) {
            height -= Number(amountTop[0]);
        }
    }

    const marginBottom = parent.css("margin-bottom");

    if (marginBottom) {
        const amountBottom = marginBottom.match(/^\d+/g);

        if (amountBottom) {
            height -= Number(amountBottom[0]);
        }
    }

    wrapper.height(height);
    window.DMOD.code.resizeCodeViews();
}

startupScripts.push(registerOnClick);
startupScripts.push(connectToSocket);
startupScripts.push(createTable);
resizeHandlers.push(resizeAnnouncerScreen);
