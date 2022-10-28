class CreateDatasetForm {
    constructor(parentDivId) {
        this.parentDivId = parentDivId;
        this.formElementId = this.parentDivId + "-form";
        this.formContentDivId = this.formElementId + "-div-universal-inputs";
        this.dynamicVarsDivId = this.formElementId + "-div-dynamic-inputs";

    }

    updateFormatChange(selection) {
        let dy_div = document.getElementById(this.dynamicVarsDivId);
        while (dy_div.firstChild){
            dy_div.removeChild(dy_div)
        }

        let addUploadSelection = false;
        if (selection == "NETCDF_FORCING_CANONICAL") {
            addUploadSelection = true;
        }

        if (addUploadSelection) {
            let upload_select_label = document.createElement('label');
            let selectId = this.parentDivId + '-inputs-upload';
            upload_select_label.appendChild(document.createTextNode('Data Files:'));
            upload_select_label.htmlFor = selectId
            dy_div.appendChild(upload_select_label);

            let upload_select = document.createElement('input');
            upload_select.type = 'file';
            upload_select.name = 'create-dataset-upload';
            upload_select.id = selectId
            upload_select.style.float = 'right';
            upload_select.style.textAlign = 'right';
            dy_div.appendChild(upload_select);
        }
    }

    dynamicInputUpdate(formInput, selection) {
        if (formInput.id == this.parentDivId + '-form-input-format') {
            this.updateFormatChange(selection);
        }
    }
}