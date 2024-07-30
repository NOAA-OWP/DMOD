import {isEmailAddress, isURL, safeGet, toEmailAddress, toProgrammaticName, toURL} from "../utilities.js";
import {DataTableDomElement} from "./TableEnumerations.js";


/**
 * Class used to define options for how to initialize and use data tables
 */
export class DataTableOptions {
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
