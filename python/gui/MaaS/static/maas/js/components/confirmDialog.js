class ConfirmDialog {
    constructor(parentDivName, id, styleClass, onConfirmFunc) {
        this.parentDivName = parentDivName;
        this.id = id;
        this.styleClass = styleClass;
        this.onConfirmFunc = onConfirmFunc;
        
        this.outer_div = null;
        this.content_div = null;
    }
    
    get parentDiv() {
        return document.getElementById(this.parentDivName);
    }
}

class ConfirmDeleteDatasetDialog extends ConfirmDialog {
    constructor(dataset_name, parentDivName, id, styleClass, onConfirmFunc) {
        super(parentDivName, id, styleClass, onConfirmFunc);
        this.dataset_name = dataset_name;
        this.buttons_div = null;
    }
    
    _style_outer_div() {
        this.outer_div.style.position = 'fixed';
        this.outer_div.style.zIndex = '1';
        this.outer_div.style.left = '35%';
        this.outer_div.style.top = '5%';
        this.outer_div.style.width = '25%';
        this.outer_div.style.height = '25%';
        this.outer_div.style.overflow = 'clip';
        this.outer_div.style.backgroundColor = '#B7B5B5FF';
        this.outer_div.style.border = '1px solid #888';
        this.outer_div.style.padding = '15px';
        //this.outer_div.style.paddingTop = '0px';
        this.outer_div.style.margin = '15% auto';
    }
    
    _init_outer_div() {
        if (this.outer_div == null) {
            this.outer_div = document.createElement('div');
            this.outer_div.id = this.id;
            this.outer_div.class = this.styleClass;
            this._style_outer_div();
            this.parentDiv.appendChild(this.outer_div);
        }
    }
    
    _init_content() {
        if (this.content_div == null) {
            this.content_div = document.createElement('div');
            this.content_div.style.height = '70%';
            //this.content_div.style.overflow = 'fixed';
            this.content_div.style.padding = '10px';
            this.content_div.appendChild(document.createTextNode("This will permanently delete dataset: "));
            this.content_div.appendChild(document.createElement('br'));
            this.content_div.appendChild(document.createElement('br'));
            this.content_div.appendChild(document.createTextNode(this.dataset_name));
            this.content_div.appendChild(document.createElement('br'));
            this.content_div.appendChild(document.createElement('br'));
            this.content_div.appendChild(document.createTextNode("Proceed?"));

            if (this.outer_div == null) {
                this._init_outer_div();
            }
            this.outer_div.appendChild(this.content_div);
        }
    }

    _init_buttons() {
        if (this.buttons_div == null) {
            this.buttons_div = document.createElement('div');
            this.outer_div.appendChild(this.buttons_div);
            this.buttons_div.style.padding = '10px';

            let cancel_button = document.createElement('button');
            cancel_button.onclick = () => {
                this.remove();
            };
            cancel_button.textContent = "Cancel";
            cancel_button.style.marginRight = '10px';
            this.buttons_div.appendChild(cancel_button);

            let confirm_button = document.createElement('button');
            confirm_button.onclick = this.onConfirmFunc;
            confirm_button.textContent = "Confirm";
            this.buttons_div.appendChild(confirm_button);
        }
    }

    append() {
        this._init_outer_div();
        this._init_content();
        this._init_buttons();
    }
    
    remove() {
        this.buttons_div.remove();
        this.buttons_div = null;

        this.content_div.remove();
        this.content_div = null;
        
        this.outer_div.remove();
        this.outer_div = null;
    }
    
}