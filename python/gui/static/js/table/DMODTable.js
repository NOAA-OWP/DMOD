import {
    cleanString,
    toProgrammaticName,
    safeGet
} from "../utilities.js";

import {DataTableOptions} from "./DataTableOptions.js";


/**
 * A wrapper class for the DataTables object that keeps track of contained data and provides a reduced interface
 * for interaction
 */
export class DMODTable {
    /**
     * Specifications for what columns to draw within the table
     * @type {{data: string, title: string, searchable: Boolean, orderable: Boolean, className: string}[]}
     */
    #columns = [];
    /**
     * Data to render within the table
     * @type {Object[]}
     */
    #internalData;

    /**
     * Options detailing how the table should behave
     * @type {DataTableOptions}
     */
    #tableOptions;

    /**
     * The CSS Selector styled ID for where the table element should be
     * @type {string}
     */
    #domID;

    /**
     * The actual HTML Element for where the table lies in the DOM
     * @type {HTMLTableElement}
     */
    #tableElement;

    /**
     * The parent of the table element
     * @type {HTMLElement}
     */
    #parentElement;

    /**
     * The DataTables object governing the behavior of the table
     *
     * @see The {@link https://datatables.net/reference/index|documentation} for more details
     *
     * @type {
     *      {
     *          clear: function,
     *          draw: function,
     *          destroy: function,
     *          containers: function,
     *          on: function,
     *          rows: {add: function}
     *      }
     *  }
     */
    #dataTable;

    /**
     * Forms a column object used to tell the DataTables library what to use for a column
     *
     * @param {String} key The name of the column
     * @param {String} dataField The field on incoming objects that holds data for the cell
     * @param {Object?} columnOptions Options for specialized behavior within the column
     * @return {{data, orderable: boolean, className: String, title: string, searchable: boolean}}
     */
    #createColumn(key, dataField, columnOptions) {
        if (columnOptions == null) {
            columnOptions = {};
        }
        const columnDefinition = {
            data: dataField,
            title: cleanString(key),
            className: toProgrammaticName(key),
            orderable: false,
            searchable: false
        };

        if (Object.keys(columnOptions).includes("searchable")) {
            if (Array.isArray(columnOptions.searchable) && columnOptions.searchable.includes(key)) {
                columnDefinition.searchable = true;
            }
            else if (!Array.isArray(columnOptions.searchable)) {
                columnDefinition.searchable = Boolean(columnOptions.searchable);
            }
        }

        if (Object.keys(columnOptions).includes("orderable")) {
            if (Array.isArray(columnOptions.orderable) && columnOptions.orderable.includes(key)) {
                columnDefinition.orderable = true;
            }
            else if (!Array.isArray(columnOptions.orderable)) {
                columnDefinition.orderable = Boolean(columnOptions.orderable);
            }
        }

        if (Object.keys(columnOptions).includes("render") && columnOptions.render != null){
            columnDefinition.render = columnOptions.render;
        }

        return columnDefinition;
    }

    /**
     * Removes the current DataTables instance and all of its artifacts to make way for a new one
     */
    #clearTable() {
        if (this.#dataTable != null) {
            this.#dataTable.clear();
            this.#dataTable.draw();
            this.#dataTable.destroy();

            // It would be ideal to remove dynamic classes here, but there isn't currently a good way to
            // identify the original classes vs the new ones

            $(`${this.#domID} > *`).remove();
        }
    }

    /**
     * Update the size of the table to make sure that it fits snugly within its container
     */
    resizeTable() {
        const container = $(this.#dataTable.containers()[0]);

        let nonContentHeights = 0;
        let nonContentElement;

        // Add together the sizes of everything that don't immediately surround the table data
        for (nonContentElement of container.find("> div[class!='dataTables_scroll']")) {
            nonContentHeights += nonContentElement.offsetHeight;
        }

        // Add together the sizes of everything surrounding the table data (header, footer) that isn't the rows/columns
        for (nonContentElement of container.find("> div.dataTables_scroll > :not(div.dataTables_scrollBody)")) {
            nonContentHeights += nonContentElement.offsetHeight;
        }

        const parent = container.parent();

        const paddingTop = parent.css("padding-top");
        const paddingBottom = parent.css("padding-bottom");

        const paddingTopValue = paddingTop.match(/(?<value>^\d+)(?<unit>\S+$)/);

        if (paddingTopValue != null) {
            nonContentHeights += Number(paddingTopValue.groups.value);
        }

        const paddingBottomValue = paddingBottom.match(/(?<value>^\d+)(?<unit>\S+$)/);

        if (paddingBottomValue != null) {
            nonContentHeights += Number(paddingBottomValue.groups.value);
        }

        const tableHeight = parent.height() - nonContentHeights;

        container.find("div.dataTables_scrollBody").height(tableHeight);

        if (Object.keys(this.#tableOptions).includes('useSearchBuilder') && this.#tableOptions.useSearchBuilder) {
            $("button.dtsb-button").on("click.dtsb", this.resizeTable);
        }
    }

    /**
     * Render the table on the screen
     * @param {{data: string, title: string, searchable: Boolean, orderable: Boolean, className: string}[]?} columnData The columns to show
     * @param {Object[]?} tableData The raw data to load into the table
     */
    #drawTable(columnData, tableData) {
        let tableColumns = columnData ? safeGet(columnData) : safeGet(this.#columns);
        tableColumns = tableColumns == null ? [] : safeGet(tableColumns);

        let data = tableData ? safeGet(tableData) : safeGet(this.#internalData);

        // Insert 'No Data' values for when no data is passed. Rendering will break otherwise
        if (data == null || data.length === 0) {
            data = [{data: "No Data"}];
            tableColumns = [{data: "data"}];
        }
        else if (tableColumns.length === 0) {
            for (let element of data) {
                for (let key of Object.keys(element)) {
                    if (tableColumns.filter(existingColumn => existingColumn.data === key).length === 0) {
                        const columnDefinition = this.#createColumn(key, key, this.#tableOptions);

                        tableColumns.push(columnDefinition);
                        this.#columns.push(columnDefinition);
                    }
                }
            }
        }

        for (let element of data) {
            for (let columnDefinition of tableColumns) {
                if (!Object.keys(element).includes(columnDefinition.data)) {
                    element[columnDefinition.data] = null;
                }
            }
        }

        let creationArguments = {
            data: data,
            columns: tableColumns,
            ...this.#tableOptions
        };

        if (Object.keys(this.#tableOptions).includes("useSearchBuilder") && this.#tableOptions.useSearchBuilder) {
            creationArguments.language = {
                "searchBuilder": {
                    "title": "Filter"
                }
            }
        }

        this.#clearTable();

        this.#dataTable = $(this.#domID).DataTable(creationArguments);

        if (Object.keys(this.#tableOptions).includes("onSelect")) {
            this.#dataTable.on("select", this.#tableOptions.onSelect);
        }

        if (Object.keys(this.#tableOptions).includes("onDeselect")) {
            this.#dataTable.on("deselect", this.#tableOptions.onDeselect);
        }

        // If the SearchBuilder is used, make sure to attach the resize function to the click events for it.
        // Clicking the add buttons will cause the table to shift, so it will need to resize
        if (Object.keys(this.#tableOptions).includes('useSearchBuilder') && this.#tableOptions.useSearchBuilder) {
            $(".dtsb-button").on("click.dtsb", this.resizeTable);
        }
    }

    /**
     * Delete a row from the table
     * @param {String} identifier The id of the row to remove
     */
    deleteRow(identifier) {
        throw new Error('deleteRow has not been implemented yet.');
    }


    /**
     * Add a column to the table if it isn't present
     * @param {String} dataField The field in any objects that should bear this column's data
     * @param {String} columnName The name for this column
     * @param {Boolean} shouldRender Whether the new column should be immediately rendered
     */
    #addColumn(dataField, columnName, shouldRender) {
        if (this.#columns.filter(column => column.data === dataField).length > 0) {
            return;
        }

        if (shouldRender == null) {
            shouldRender = true;
        }

        let newColumn = this.#createColumn(columnName, dataField, this.#tableOptions);
        this.#columns.push(newColumn);

        if (shouldRender) {
            this.#drawTable();
        }
    }

    /**
     * Adds an object to the table as a row
     * @param rowObject The object containing data to add to the table
     * @param updateTable Whether to redraw the table once data has been added
     */
    #addRowObject(rowObject, updateTable) {
        if (updateTable == null) {
            updateTable = false;
        }

        if (rowObject == null) {
            return;
        }

        for (let key of Object.keys(rowObject)) {
            let matchingColumns = this.#columns.filter(value => value.data === key);

            if (matchingColumns.length > 1) {
                continue;
            }

            updateTable = true;
            this.#addColumn(key, cleanString(key), false);
        }

        this.#columns.forEach(function(value, index, array){
            if (!Object.keys(rowObject).includes(value.data)) {
                rowObject[value.data] = null;
            }
        });

        this.#internalData.push(rowObject);

        if (updateTable) {
            this.#drawTable();
        }
        else {
            this.#dataTable.rows.add(rowObject);
        }
    }

    /**
     * Add a series of objects to the table
     * @param {Object[]} rowArray A series of objects bearing data to add to the table
     */
    #addRowArray(rowArray) {
        let objectEntries = rowArray.filter(element => typeof element === 'object');

        if (objectEntries.length !== rowArray.length) {
            throw new Error(
                `If any objects are in an array to add to a row all elements need to be objects. ` +
                `Only ${objectEntries.length} out of ${rowArray.length} entries were objects.`
            );
        }
        else if (objectEntries.length > 0) {
            for (let entry of objectEntries) {
                this.#addRowObject(entry, false);
            }

            table.draw();
        }
    }

    /**
     * Add a new row to the table
     * @param {Object|Object[]} entry Either an object containing row values or an array of objects containing row values
     */
    addRow(entry) {
        if (Array.isArray(entry)) {
            this.#addRowArray(entry);
        }
        else if (typeof entry === 'object') {
            this.#addRowObject(entry);
        }
        else {
            throw new Error(`${typeof entry} is not a valid input when adding rows to a table.`);
        }
    }

    constructor(elementID, inputData, options) {
        if (!Object.keys($.fn).includes("DataTable")) {
            throw new Error(
                "Table cannot be constructed - the 'DataTables' library cannot be found. " +
                "Make sure it has been imported through a <script> tag."
            );
        }

        if (inputData == null) {
            inputData = [];
        }

        if (!(Array.isArray(inputData))) {
            throw new Error("The 'data' parameter for a new table must be an array of objects, but that was not the case.");
        }

        if (inputData.filter(element => typeof element != 'object').length > 0) {
            throw new Error(
                "A new table cannot be formed - that data passed in must be an array of objects and that was not the case"
            );
        }

        this.#internalData = safeGet(inputData);
        this.#tableOptions = options instanceof DataTableOptions ? options : new DataTableOptions(options);
        this.#domID = elementID[0] === "#" ? elementID : `#${elementID}`;

        const matchingElements = $(this.#domID);

        if (matchingElements.length === 0) {
            throw new Error(`There are no elements by the name of ${domID}; a dynamic table cannot be created`);
        }

        /**
         * The element at the root of the table
         * @type {Element}
         */
        let rootElement = matchingElements[0];

        // If the element that the table should be created over isn't a table, create a new table element directly
        // underneath it and give it a dynamic name
        if (rootElement.tagName.toUpperCase() !== "TABLE") {
            // Create a new element
            const newTable = document.createElement("table");

            const currentTables = $('[id^="dynamic-table-"]');
            this.#domID = `dynamic-table-${currentTables.length + 1}`
            newTable.id = this.#domID;
            newTable.width = "100%";

            rootElement = newTable;
        }

        this.#tableElement = rootElement;
        this.#parentElement = this.#tableElement.parentElement;

        this.#drawTable();
    }
}
