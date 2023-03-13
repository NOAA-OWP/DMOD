import {Enumeration} from "../utilities.js";

export class DataTablesSelectionTarget extends Enumeration {
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


export class DataTableDomElement extends Enumeration {
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