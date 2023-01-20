class DatasetOverviewTableRow {
    constructor(parentTableId, serializedDataset, detailsOnClickFunc, filesOnClickFunc, downloadOnClickFunc,
                uploadOnClickFunc, deleteOnClickFunc) {
        this.parentTableId = parentTableId;
        this.serializedDataset = serializedDataset;

        this.rowClassName = "mgr-tbl-content";

        this.detailsOnClickFunc = detailsOnClickFunc;
        this.filesOnClickFunc = filesOnClickFunc;
        this.downloadOnClickFunc = downloadOnClickFunc;
        this.uploadOnClickFunc = uploadOnClickFunc;
        this.deleteOnClickFunc = deleteOnClickFunc;

        this.row = document.getElementById(this.rowId);
    }

    get datasetName() {
        return this.serializedDataset["name"];
    }

    get category() {
        return this.serializedDataset["data_category"];
    }

    get rowId() {
        return this.parentTableId + "-row-" + this.datasetName;
    }

    get parentTable() {
        return document.getElementById(this.parentTableId);
    }

    _createLinks(is_anchor, text, onClickFunc) {
        let cell = document.createElement('th');
        let content;
        if (is_anchor) {
            content = document.createElement('a');
            content.href = "javascript:void(0);";
        }
        else {
            content = document.createElement('button');
        }

        const ds_name = this.datasetName;

        let onclick;
        switch (text) {
            case 'Details':
                onclick = this.detailsOnClickFunc;
                break;
            case 'Files':
                onclick = this.filesOnClickFunc;
                break;
            case 'Download':
                onclick = this.downloadOnClickFunc;
                break;
            case 'Upload Files':
                onclick = this.uploadOnClickFunc;
                break;
            case 'Delete':
                onclick = this.deleteOnClickFunc;
                break;
        }

        content.onclick = function() { onclick(ds_name); };
        content.appendChild(document.createTextNode(text));
        cell.appendChild(content);
        this.row.appendChild(cell);
    }

    build() {
        if (this.row != null) {
            this.row.remove();
        }
        this.row = document.createElement('tr');
        this.row.id = this.rowId;
        this.row.className = this.rowClassName;

        let colCell = document.createElement('th');
        colCell.appendChild(document.createTextNode(this.datasetName));
        this.row.appendChild(colCell);

        colCell = document.createElement('th');
        colCell.appendChild(document.createTextNode(this.category));
        this.row.appendChild(colCell);

        this._createLinks(true, "Details", this.datasetName, this.detailsOnClickFunc);
        this._createLinks(true, "Files", this.datasetName, this.filesOnClickFunc);
        this._createLinks(true, "Download", this.datasetName, this.downloadOnClickFunc);
        // TODO: put this back in later
        //this._createLinks(true, "Upload Files", this.datasetName, this.uploadOnClickFunc);
        this._createLinks(true, "Delete", this.datasetName, this.deleteOnClickFunc);
    }
}

class DatasetOverviewTable {
    constructor(parentDivId, tableClass, detailsOnClickFunc, filesOnClickFunc, downloadOnClickFunc,
                uploadOnClickFunc, deleteOnClickFunc) {
        this.parentDivId = parentDivId;
        this.tableClass = tableClass;
        this.tableId = this.parentDivId + "-overview-table";

        this.detailsOnClickFunc = detailsOnClickFunc;
        this.filesOnClickFunc = filesOnClickFunc;
        this.downloadOnClickFunc = downloadOnClickFunc;
        this.uploadOnClickFunc = uploadOnClickFunc;
        this.deleteOnClickFunc = deleteOnClickFunc;

        this.table = document.getElementById(this.tableId);
    }

    get parentDiv() {
        return document.getElementById(this.parentDivId);
    }

    get tableHeader() {
        let thead = document.createElement('thead');
        let header = document.createElement('tr');
        thead.appendChild(header);

        let colCell = document.createElement('th');
        colCell.className = "mgr-tbl-dataset-header";
        colCell.appendChild(document.createTextNode('Dataset Name'));
        header.appendChild(colCell);

        colCell = document.createElement('th');
        colCell.className = "mgr-tbl-category-header";
        colCell.appendChild(document.createTextNode('Category'));
        header.appendChild(colCell);

        header.appendChild(document.createElement('th'));

        colCell = document.createElement('th');
        colCell.appendChild(document.createTextNode('Actions'));
        header.appendChild(colCell);

        header.appendChild(document.createElement('th'));
        header.appendChild(document.createElement('th'));

        return thead;
    }

    buildAndAddRow(serializedDataset) {
        let row = new DatasetOverviewTableRow(this.tableId, serializedDataset, this.detailsOnClickFunc,
            this.filesOnClickFunc, this.downloadOnClickFunc, this.uploadOnClickFunc, this.deleteOnClickFunc);
        row.build();
        this.table.appendChild(row.row);
    }

    buildTable(contentResponse) {
        if (this.table != null) {
            this.table.remove();
        }
        this.table = document.createElement('table');
        this.table.id = this.tableId;
        this.table.className = this.tableClass;

        this.table.appendChild(this.tableHeader);

        for (const ds_name in contentResponse["datasets"]) {
            this.buildAndAddRow(contentResponse["datasets"][ds_name]);
        }

        this.parentDiv.appendChild(this.table);
    }
}