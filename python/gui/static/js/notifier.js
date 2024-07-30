import {getWebSocketURL} from "./utilities.js";

class Notifier {
    url;
    socket = null;
    dialog = null;
    maxConnectionAttempts = 5;
    connectionAttemptCount = 0;
    constructor(notifierUrl, dialogID) {
        if (notifierUrl) {
            this.url = getWebSocketURL(notifierUrl);

            if (!dialogID.startsWith("#")) {
                dialogID = "#" + dialogID;
            }

            if ($(dialogID).length === 0) {
                throw new Error(
                    `There are no HTML elements found with a selector of "${dialogID}". No notifier may be created.`
                );
            }

            this.dialog = $(dialogID).dialog({
                autoOpen: false,
                modal: true,
                buttons: {
                    Ok: () => {
                        this.dialog.dialog( "close" );
                    }
                }
            });

            this.connect();
        }
    }

    /**
     * Handler for when a socket has been correctly connected to
     * @param {MessageEvent} event
     */
    connectedToSocket = (event) => {
        this.connectionAttemptCount = 0;
    }

    /**
     * Handler for when a message has been received through the socket
     * @param {MessageEvent} event
     */
    receivedMessage = (event) => {
        let data = event.data;
        if (!data) {
            return;
        }
        data = JSON.parse(data);
        this.tellDialog(data.message);
    }

    errorEncountered = (event) => {
        let remainingAttempts = Math.max(this.maxConnectionAttempts - this.connectionAttemptCount, 0);
        let errorMessage = `An error was encountered with the notification web socket. ${remainingAttempts} connection attempts left.`;
        this.tellDialog(errorMessage, "error");
        this.connect();
    }

    connect = () => {
        if (this.connectionAttemptCount >= this.maxConnectionAttempts) {
            this.connectionAttemptCount = 0;
            return;
        }

        this.socket = new WebSocket(this.url);

        this.socket.addEventListener('message', this.receivedMessage);

        this.socket.addEventListener('open', this.connectedToSocket);

        this.socket.addEventListener('error', this.errorEncountered);

        this.connectionAttemptCount += 1;
    }

    isConnected = () => {
        return this.socket != null && this.socket.readyState <= 1;
    }

    isClosed = () => {
        return this.socket == null || this.socket.readyState > 1;
    }

    tellDialog = (message, level) => {
        if (level == null) {
            level = "info";
        }

        this.dialog.find(".notification-message").text(message);
        this.dialog.dialog("open");
    }
}


function startNotifiers() {
    if (!Object.keys(window.DMOD).includes("notifiers")) {
        window.DMOD.notifiers = {};
    }

    for (let notifier of NOTIFIERS) {
        window.DMOD.notifiers[notifier.id] = new Notifier(notifier.url, notifier.id);
    }
}

startupScripts.push(startNotifiers);
