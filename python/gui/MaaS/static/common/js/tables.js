/**
 * Ensure that a given string is a valid URL
 * @param {String} url The URL to format
 * @return {null|undefined|string}
 */
function toURL(url) {
    if (url == null || url === '' || typeof url != 'string') {
        return url;
    }

    let protocolMatcher = /^(s?ftp|https?|file|dns|geo|h323|imap|info|ldap|mailto|nfs|telnet|vnc|wss?|s3):\/\//g;
    if (!protocolMatcher.test(url)){
        url = `http://${protocolMatcher}`;
    }

    return url;
}

/**
 * Determines if a given string is a URL
 * @param {string} possibleURL
 */
function isURL(possibleURL) {
    if (possibleURL == null || possibleURL === '' || typeof possibleURL != 'string') {
        return false;
    }

    possibleURL = toURL(possibleURL);

    try {
        new URL(possibleURL);
        return true;
    }
    catch {
        return false;
    }
}

/**
 * Convert a string to an email address if possible
 * @param {String} address The address to ensure is formatted as "mailto://address"
 * @return {string}
 */
function toEmailAddress(address) {
    if (!isEmailAddress(address)) {
        return address;
    }

    return /^.+:\/\//g.test(address) ? address : `mailto://${address}`;
}

/**
 * Test whether a value could be an email address
 * @param {String} possibleEmailAddress A value that might be an email address
 * @return {Boolean}
 */
function isEmailAddress(possibleEmailAddress) {
    if (possibleEmailAddress == null || possibleEmailAddress === '' || typeof possibleEmailAddress != 'string') {
        return false;
    }

    const emailExpression = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/gi;

    return emailExpression.test(possibleEmailAddress);
}

/**
 * Check whether a character represents an upper case letter
 * @param {String} character
 * @return {Boolean}
 */
function characterIsUpperCaseLetter(character) {
    return typeof character === 'string' && /[A-Z]/g.test(character);
}

/**
 * Check whether a character represents a lower case letter
 * @param {String} character
 * @return {Boolean}
 */
function characterIsLowerCaseLetter(character) {
    return typeof character === 'string' && /[a-z]/g.test(character);
}

/**
 * Check whether a character represents whitespace
 * @param {string} character
 * @return {Boolean}
 */
function characterIsWhiteSpace(character) {
    return typeof character === 'string' && /[ \t\r\n]/i.test(character);
}

/**
 * Check whether a character is a number
 * @param character
 * @return {Boolean}
 */
function characterIsDigit(character) {
    return typeof character === 'string' && "0123456789".includes(character);
}

/**
 * Formats the given string into User friendly text
 * @param {string} string
 * @return {string}
 */
function cleanString(string) {
    if (string == null || string.length === 0) {
        return string;
    }

    string = string.trim();

    let stringParts = [];

    stringParts.push(string[0].toUpperCase());

    for (let letterIndex = 0; letterIndex < string.length - 1; letterIndex++) {
        const currentCharacter = string[letterIndex];
        const nextCharacter = string[letterIndex + 1];

        const currentCharacterIsWhitespace = characterIsWhiteSpace(currentCharacter);

        if (currentCharacterIsWhitespace) {
            stringParts.push(nextCharacter.toUpperCase());
            continue;
        }

        const nextCharacterIsWhiteSpace = characterIsWhiteSpace(nextCharacter);

        if (nextCharacterIsWhiteSpace) {
            stringParts.push(nextCharacter);
            continue;
        }

        const currentCharacterIsLowerCase = characterIsLowerCaseLetter(currentCharacter);
        const currentCharacterIsUpperCase = characterIsUpperCaseLetter(currentCharacter);
        const currentCharacterIsDigit = characterIsDigit(currentCharacter);
        const currentCharacterIsLetter = currentCharacterIsLowerCase || currentCharacterIsUpperCase;

        const nextCharacterIsLowerCase = characterIsLowerCaseLetter(nextCharacter);
        const nextCharacterIsUpperCase = characterIsUpperCaseLetter(nextCharacter);
        const nextCharacterIsDigit = characterIsDigit(nextCharacter);

        const nextCharacterIsLetter = nextCharacterIsLowerCase || nextCharacterIsUpperCase;

        if (currentCharacterIsLowerCase && nextCharacterIsUpperCase) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else if (currentCharacterIsLetter && nextCharacterIsDigit) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else if (currentCharacterIsDigit && nextCharacterIsLetter) {
            stringParts.push(" ");
            stringParts.push(nextCharacter.toUpperCase());
        }
        else {
            stringParts.push(nextCharacter.toLowerCase());
        }

    }

    return stringParts.join('').trim();
}

/**
 * Formats a string into
 * @param string
 * @return {String}
 */
function toProgrammaticName(string){
    return string.replaceAll(
        /[` !@#$%^&*()+=\[\]{};':"\\|,.<>\/?~]/g,
        "_"
    ).replace(/_+/g, "_")
    .replaceAll(/ +/g, "-");
}

function cssSizeToPixels(amount, unit, parent) {
    let convertedAmount = Number(amount);

    switch (unit.toLowerCase()) {
        case "em":
            break;
        case "%":
            break
        case "pt":
            break;
        default:
    }

    return convertedAmount;
}

/**
 * Retrieve a safe to use copy of the given value.
 *
 * Simple values like 'stuff' are safe to assign, but values like ['one', 'two', 'three'] aren't since later use
 * may mutate the earlier copy
 *
 * @example
 *      >>> let x = "stuff";
 *      >>> let y = ["one", "two", "three"];
 *      >>> let x2 = safeGet(x);
 *      >>> let y2 = safeGet(y);
 *      >>> x2 = x2 + "!";
 *      >>> y2.push(1);
 *      >>> console.log(x);
 *      stuff
 *      >>> console.log(x2);
 *      stuff!
 *      >>> console.log(y);
 *      ["one", "two", "three"]
 *      >>> console.log(y2);
 *      ["one", "two", "three", 1]
 *      >>> y.push(8);
 *      >>> console.log(y);
 *      ["one", "two", "three", 8]
 *      >>> console.log(y2);
 *      ["one", "two", "three", 1]
 *
 * @template T
 * @param {T} value
 * @return {T}
 */
function safeGet(value) {
    if (value == null) {
        return null;
    }
    else if (Array.isArray(value)) {
        return value.map(x => safeGet(x));
    }
    else if (value.isPrototypeOf(Object)) {
        let copiedObject = {};

        for (let [key, entry] of Object.entries(value)) {
            copiedObject[key] = safeGet(entry);
        }

        value = copiedObject;
    }

    return value;
}

class Enumeration {
    static get values() {
        const ownedProperties = Object.getOwnPropertyDescriptors(this);
        const entryPerProperty = Object.entries(ownedProperties);
        const propertyGetters = entryPerProperty.filter(
            ([name, entity]) => name !== 'values' && Object.hasOwn(entity, 'get') && typeof entity.get === 'function'
        );
        return propertyGetters.flatMap(([name, entity]) => this[name]);
    }

    static has(value) {
        return this.values.includes(value);
    }
}

class DataTableSelectStyle extends Enumeration {
    static get API() {
        return "api";
    }

    static get SINGLE() {
        return "single";
    }

    static get MULTIPLE() {
        return "multi";
    }

    static get OS() {
        return "os";
    }

    static get SHIFT_MULTIPLE() {
        return "multi+shift";
    }
}


class DataTablesSelectionTarget extends Enumeration {
    static get ROW() {
        return "row";
    }

    static get COLUMN() {
        return "column";
    }

    static get CELL() {
        return "cell";
    }
}


class DataTableDomElement extends Enumeration {
    /**
     * @return {string} The length changing input control for a DataTable
     */
    static get LENGTH() {
        return "l";
    }

    /**
     * @return {string} The filter input control
     */
    static get FILTER_INPUT() {
        return "f";
    }

    /**
     * @return {string} The table itself
     */
    static get TABLE() {
        return "t";
    }

    /**
     * @return {string} The information summary
     */
    static get INFORMATION() {
        return "i";
    }

    /**
     * @return {string} The input used to move through pages
     */
    static get PAGINATION_CONTROL() {
        return "p";
    }

    /**
     * @return {string} The display used to show that data is processing
     */
    static get PROCESSING_DISPLAY() {
        return "r";
    }

    /**
     * @return {string} The input used to reorder columns
     */
    static get COLUMN_REORDER_CONTROL() {
        return "R";
    }

    /**
     * @return {string} The scroller plugin
     */
    static get SCROLLER() {
        return "S";
    }

    /**
     * @return {string} The advanced search input
     */
    static get SEARCH_BUILDER() {
        return "Q";
    }
}


/**
 * Class used to define options for how to initialize and use data tables
 */
class DataTableOptions {
    /**
     * Whether to enable paging (show entries across multiple 'pages' rather than one massive table)
     * @type {boolean}
     */
    paging = false;

    /**
     * Whether to enable specialized scrolling functionality
     * @type {boolean}
     */
    #scroller = false;

    get scroller() {
        return this.#scroller;
    }

    set scroller(shouldUse) {
        if (shouldUse && !this.dom.includes(DataTableDomElement.SCROLLER)) {
            let tableElementIndex = this.dom.indexOf(DataTableDomElement.TABLE);

            if (tableElementIndex === this.dom.length -1) {
                this.dom = this.dom + DataTableDomElement.SCROLLER;
            }
            else {
                const preScrollerLineup = this.dom.slice(0, tableElementIndex + 1);
                const postScrollerLineup = this.dom.slice(tableElementIndex + 1);
                this.dom = `${preScrollerLineup}${DataTableDomElement.SCROLLER}${postScrollerLineup}`;
            }
        }
        else if (!shouldUse) {
            this.dom = this.dom.replace(DataTableDomElement.SCROLLER, "");
        }

        this.#scroller = shouldUse;
    }

    /**
     * Enable vertical scrolling. Vertical scrolling will constrain the DataTable to the given height,
     * and enable scrolling for any data which overflows the current viewport. This can be used as an alternative to
     * paging to display a lot of data in a small area (although paging and scrolling can both be enabled at the same
     * time if desired).
     *
     * The value given here can be any CSS unit, or a number (in which case it will be treated as a pixel measurement)
     * and is applied to the table body (i.e. it does not take into account the header or footer height directly).
     * @type {string}
     */
    scrollY = '';

    /**
     * Whether to allow horizontal scrolling
     * @type {boolean}
     */
    scrollX = true;

    /**
     * Allow the table to reduce in height when a limited number of rows are shown.
     * @type {boolean}
     */
    scrollCollapse = false;

    /**
     * Enable or disable automatic column width calculation
     * @type {boolean}
     */
    autoWidth = true;

    /**
     * This option allows DataTables to create the nodes (rows and cells in the table body) only when they are
     * needed for a draw.
     * @type {boolean}
     */
    deferRender = true;

    /**
     * When this option is enabled, Datatables will show information about the table including information about
     * filtered data if that action is being performed
     * @type {boolean}
     */
    info = false;

    /**
     * Whether columns should be searchable
     * @type {boolean|String[]}
     */
    searchable = true;

    /**
     * Whether a user should be able to sort data by the ascending or descending values
     * @type {boolean|String[]}
     */
    orderable = true;

    /**
     * Function describing how numbers should be shown on the screen
     * @returns {string}
     */
    formatNumber = () => ",";

    /**
     * When ordering is enabled (ordering), by default DataTables allows users to sort multiple columns by shift
     * clicking upon the header cell for each column.
     * @type {boolean}
     */
    orderMulti = true;

    /**
     * This option provides the ability to enable and configure ColReorder for DataTables. In its simplest form as the
     * boolean true it will enable ColReorder with the default configuration options
     * @type {boolean|Object}
     */
    #colReorder = false;

    get colReorder() {
        return this.#colReorder
    }

    set colReorder(shouldUse) {
        if (shouldUse && !this.dom.includes(DataTableDomElement.COLUMN_REORDER_CONTROL)) {
            let tableElementIndex = this.dom.indexOf("t");

            if (tableElementIndex === 0) {
                this.dom = DataTableDomElement.COLUMN_REORDER_CONTROL + this.dom;
            }
            else {
                const preReorderLineUp = this.dom.slice(0, tableElementIndex);
                const postReorderLineUp = this.dom.slice(tableElementIndex);
                this.dom = `${preReorderLineUp}${DataTableDomElement.COLUMN_REORDER_CONTROL}${postReorderLineUp}`;
            }
        }
        else if (!shouldUse) {
            this.dom = this.dom.replace(DataTableDomElement.COLUMN_REORDER_CONTROL, "");
        }

        this.#colReorder = shouldUse;
    }
    fixedColumns;
    fixedHeader = true;
    responsive = true;

    set useSearchBuilder(shouldUse) {
        if (shouldUse && !this.dom.includes(DataTableDomElement.SEARCH_BUILDER)) {
            this.dom = DataTableDomElement.SEARCH_BUILDER + this.dom;
        }
        else if (!shouldUse) {
            this.dom = this.dom.replace(DataTableDomElement.SEARCH_BUILDER, "");
        }
        //this.useSearchBuilder = shouldUse;
    }

    get useSearchBuilder() {
        return this.dom.includes(DataTableDomElement.SEARCH_BUILDER);
    }

    /**
     * Define the table control elements to appear on the page and in what order.
     *
     * l - [l]ength changing input control
     * f - [f]iltering input
     * t - The [t]able!
     * i - Table [i]nformation summary
     * p - [p]agination control
     * r - p[r]ocessing display element
     * R - Col[R]eorder
     * S - [S]croller
     * Q - SearchBuilder ([Q]uery builder)
     *
     * @type {string}
     */
    dom = DataTableDomElement.LENGTH +
        DataTableDomElement.PROCESSING_DISPLAY +
        DataTableDomElement.TABLE +
        DataTableDomElement.INFORMATION +
        DataTableDomElement.PAGINATION_CONTROL;

    /**
     * This option can be used to configure the Select extension for DataTables during the initialisation of a DataTable.
     *
     * Options when configuring via object are:
     * @example
     *  {
     *      info?: boolean,
     *      blurable?: boolean,
     *      className?: string,
     *      style?: ("api"|"single"|"multi"|"os"|"multi+shift"),
     *      selector?: string,
     *      items?: ('row'|'column'|'cell')
     *  }
     *
     *      info: Enable / disable the display for item selection information in the table summary
     *      blurable: Indicate if the selected items will be removed when clicking outside the table
     *      className: Set the css class name that will be applied to selected items
     *      style: Set the selection style for end user interaction with the table
     *      selector: Set the element css selector used for mouse event capture to select items
     *      items: Set which table items to select (rows, columns or cells)
     *
     *  Available Selection styles:
     *      api - Selection can only be performed via the API
     *      single - Only a single item can be selected, any other selected items will be automatically deselected when a new item is selected
     *      multi - Multiple items can be selected. Selection is performed by simply clicking on the items to be selected
     *      os - Operating System (OS) style selection. This is the most comprehensive option and provides complex behaviours such as ctrl/cmd clicking to select / deselect individual items, shift clicking to select ranges and an unmodified click to select a single item.
     *      multi+shift - a hybrid between the os style and multi, allowing easy multi-row selection without immediate de-selection when clicking on a row.
     *
     * @type {
     *  boolean |
     *  string |
     *  {
     *      info?: boolean,
     *      blurable?: boolean,
     *      className?: string,
     *      style?: ("api"|"single"|"multi"|"os"|"multi+shift"),
     *      selector?: string,
     *      items?: ('row'|'column'|'cell')
     *  }
     * }
     */
    select = false;

    /**
     * Function that is called when items are selected on the table
     *
     * @param {Object}                  event       jQuery event object
     * @param {Object}                  dataTable   DataTables API instance
     * @param {"row"|"column"|"cell"}   itemType    Items being selected. This can be row, column or cell
     * @param {Array}                   indexes     The DataTables' indexes of the selected items
     */
    onSelect = function(event, dataTable, itemType, indexes) {};

    /**
     * Function that is called when items are deselected on the table
     *
     * @param {Object}                  event       jQuery event object
     * @param {Object}                  dataTable   DataTables API instance
     * @param {"row"|"column"|"cell"}   itemType    Items being selected. This can be row, column or cell
     * @param {Array}                   indexes     The DataTables' indexes of the selected items
     */
    onDeselect = function(event, dataTable, itemType, indexes) {};

    search = {
        regex: true,
        caseInsensitive: true
    };

    /**
     * Function used to tell DataTables how to render data within cells in a column
     * @param {null|undefined|String} data The raw data for the cell
     * @param {String} type What triggered the rendering. Options are: 'filter', 'display', 'type', 'sort', undefined
     * @param {Object} row All data for each column within the row
     * @param {{row: Number, co: Number, settings: object}} meta basic metadata for the cell being drawn
     * @return {String} What HTML should appear within a table cell's `td` element
     */
    render = function(data, type, row, meta){
        let tag = isEmailAddress(data) || isURL(data) ? "a" : "span";

        let classes = [
            `row_${meta.row}`,
            `column_${meta.col}`,
            toProgrammaticName(meta.settings.aoColumns[meta.col].title)
        ];

        let attributes = {
            "row": meta.row,
            "column": meta.col,
            "coordinates": `${meta.row},${meta.col}`,
            "columnName": meta.settings.aoColumns[meta.col].title
        }

        if (isEmailAddress(data)) {
            attributes.href = toEmailAddress(data);
            attributes.target = '_blank';
        }
        else if (isURL(data)) {
            attributes.href = toURL(data);
            attributes.target = '_blank';
        }

        if (data == null) {
            data = "";
        }

        classes = classes.join(" ");
        attributes = Object.keys(attributes).map(key => `${key}="${attributes[key]}"`).join(" ");

        return `<${tag} ${attributes} class="${classes}">${data}</${tag}>`;
    };

    constructor(options) {
        if (typeof options === 'object' && Object.keys(options).length > 0) {
            this.paging = Object.keys(options).includes("paging") ? safeGet(options.paging) : this.paging;
            this.scroller= Object.keys(options).includes("scroller") ? safeGet(options.scroller) : this.scroller;
            this.scrollY= Object.keys(options).includes("scrollY") ? safeGet(options.scrollY) : this.scrollY;
            this.scrollX= Object.keys(options).includes("scrollX") ? safeGet(options.scrollX) : this.scrollX;
            this.scrollCollapse = Object.keys(options).includes("scrollCollapse") ? safeGet(options.scrollCollapse) : this.scrollCollapse;
            this.autoWidth = Object.keys(options).includes("autoWidth") ? safeGet(options.autoWidth) : this.autoWidth;
            this.deferRender = Object.keys(options).includes("deferRender") ? safeGet(options.deferRender) : this.deferRender;
            this.info = Object.keys(options).includes("info") ? safeGet(options.info) : this.info;
            this.searchable = Object.keys(options).includes("searchable") ? safeGet(options.searchable) : this.searchable;
            this.orderable = Object.keys(options).includes("orderable") ? safeGet(options.orderable) : this.orderable;
            this.formatNumber = Object.keys(options).includes("formatNumber") ? safeGet(options.formatNumber) : this.formatNumber;
            this.orderMulti = Object.keys(options).includes("orderMulti") ? safeGet(options.orderMulti) : this.orderMulti;
            this.colReorder = Object.keys(options).includes("colReorder") ? safeGet(options.colReorder) : this.colReorder;
            this.fixedColumns = Object.keys(options).includes("fixedColumns") ? safeGet(options.fixedColumns) : this.fixedColumns;
            this.fixedHeader = Object.keys(options).includes("fixedHeader") ? safeGet(options.fixedHeader) : this.fixedHeader;

            if (Object.keys(options).includes("dom") && typeof options.dom === 'string') {
                if (!options.dom.includes(DataTableDomElement.TABLE)) {
                    throw new Error(
                        `Cannot create options for a new DataTable - ` +
                        `the location for the table was not defined in the customized 'dom'. Received "${options.dom}"`
                    );
                }
            }
            else if (Object.keys(options).includes("dom") && options.dom != null && typeof options.dom !== 'string'){
                console.warning(
                    `Received invalid definition for DataTable dom element (${options.dom}). ` +
                    `Required type is 'string', but received '${typeof options.dom}'`
                );
            }

            this.dom = Object.keys(options).includes("dom") ? safeGet(options.dom) : this.dom;

            if (Object.keys(options).includes("useSearchBuilder")) {
                this.useSearchBuilder = safeGet(options.useSearchBuilder);
            }

            this.render = Object.keys(options).includes("render") ? safeGet(options.render) : this.render;

            this.select = Object.keys(options).includes("select") ? safeGet(options.select) : this.select;
            this.search = Object.keys(options).includes("search") ? safeGet(options.search) : this.search;
            this.onSelect = Object.keys(options).includes("onSelect") ? safeGet(options.onSelect) : this.onSelect;

            if (Object.keys(options).includes("onDeselect")) {
                this.onDeselect = safeGet(options.onDeselect);
            }
        }

        if (this.dom == null || typeof this.dom != 'string' || !this.dom.includes('t')) {
            throw new Error(`The defined 'dom' string must include 't'. ${this.dom} received instead.`);
        }
    }
}

/**
 * A wrapper class for the DataTables object that keeps track of contained data and provides a reduced interface
 * for interaction
 */
class DMODTable {

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
