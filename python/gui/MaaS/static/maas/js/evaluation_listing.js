import {DMODTable} from "js/table/DMODTable.js";

async function loadListing() {
    if (Object.hasOwn(window, "DMOD")) {
        window.DMOD = {};
    }

    const listing = await fetch(LISTING_URL).then(response => response.json());
    window.DMOD.evaluationTable = new DMODTable(TABLE_NAME, listing);
}

startupScripts.push(loadListing);
