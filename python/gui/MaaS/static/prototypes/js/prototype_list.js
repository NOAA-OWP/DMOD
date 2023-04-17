import {TreeView, TreeViewNode} from "/static/js/widgets/tree.js";
window.DMOD.prototyping = {
    /**
     * @type {TreeView|null}
     */
    tree: null
}
const PROTOTYPE_DATA = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": [
        "a",
        "b",
        "c"
    ],
    "five": {
        "candy": 55.50,
        "bananas": 6,
        "pork chop": 9.89
    }
}

const addItem = (element, key, value, attributes) => {
    let valueToAdd;

    if (typeof value === 'object') {
        valueToAdd = null;
    }
    else {
        valueToAdd = value;
    }

    let listItem = element.add(key, valueToAdd, attributes);

    if (Array.isArray(value)) {
        for (let [index, subvalue] of Object.entries(value)) {
            addItem(listItem, subvalue, subvalue, {path: index});
        }
    }
    else if (typeof valueToAdd === 'object') {
        for (let [subkey, subvalue] of Object.entries(value)) {
            addItem(listItem, subkey, subvalue);
        }
    }
}

const createTree = () => {
    window.DMOD.prototyping.tree = TreeView.fromObject(
        LIST_NAME,
        $("#content"),
        PROTOTYPE_DATA,
        {ignoreParent: true}
    );

    let root = window.DMOD.prototyping.tree.render();
}

startupScripts.push(createTree);