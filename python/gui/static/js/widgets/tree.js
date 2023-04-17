import {updateObject} from "/static/js/utilities.js";

const SELECTED_LIST_ITEM_CLASS = "selected-tree-view-node";

export class SelectorObjectConstructor {
    static _INSTANCE = null;

    /**
     *
     * @returns {SelectorObjectConstructor}
     */
    static get instance() {
        if (this._INSTANCE == null) {
            this._INSTANCE = new SelectorObjectConstructor();
        }

        return this._INSTANCE;
    }

    static construct = (identifier, parent, data, attributes) => {
        return this.instance.convert(identifier, parent, data, attributes);
    }

    convert = (identifier, parent, data, attributes) => {
        if (typeof data !== 'object' || Array.isArray(data)){
            throw new Error("Only objects may be converted to a Selector tree");
        }

        const tree = new TreeView(identifier, parent);

        for (let [key, value] of Object.entries(data)) {
            this.addItem(tree, key, value, attributes)
        }

        return tree;
    }

    populate = (tree, data, attributes) => {
        for (let [key, value] of Object.entries(data)) {
            this.addItem(tree, key, value, attributes)
        }

        return tree;
    }

    addItem = (element, key, value, attributes) => {
        let valueToAdd;

        if (typeof value === 'object') {
            valueToAdd = null;
        }
        else {
            valueToAdd = value;
        }

        let listItem = element.add(key, valueToAdd, attributes);

        if (Array.isArray(value)) {
            let copiedAttributes = Object.assign({}, attributes);

            for (let [index, subValue] of Object.entries(value)) {
                copiedAttributes["path"] = index;
                this.addItem(listItem, subValue, subValue, copiedAttributes);
            }

            listItem.childType = 'array';
        }
        else if (typeof valueToAdd === 'object') {
            for (let [subkey, subValue] of Object.entries(value)) {
                this.addItem(listItem, subkey, subValue, attributes);
            }

            listItem.childType = 'object';
        }

        return listItem;
    }
}

export class TreeViewNode {
    /**
     * The name for the element that will show up on the screen
     * @type {string}
     */
    #name;
    /**
     * The value that the list item represents. Usually maps to some sort of ID
     * @type {string|Number}
     */
    #value;
    /**
     * The data type of the child of this node, such as 'array' or 'object'
     * @type {string|null}
     */
    #childType = null;
    /**
     * An optional description for the item represented
     * @type {string|null}
     */
    #description;
    /**
     * Attributes for the list item that might be helpful but aren't the display name or value
     * @type {Object<string, any>}
     */
    #attributes = {};

    /**
     * Whether this element may be selected by the end user
     * @type {boolean}
     */
    #canSelect = true;

    /**
     * Handlers for events that may be invoked by outside entities
     * @type {Object<string, ((Event) => any)[]>}
     */
    #events = {};

    /**
     * Nested list items
     * @type {TreeViewNode[]}
     */
    #nestedItems = [];

    /**
     * The entity that owns this list item
     * @type {TreeViewNode|TreeView|null}
     */
    #owner = null;

    /**
     * The HTMLElement for this list item
     * @type {HTMLLIElement|null}
     */
    #element = null;

    /**
     * The HTMLElement that will contain all child elements
     * @type {HTMLUListElement|null}
     */
    #childContainer;

    /**
     * The name of this specific element on the path
     * @type {string}
     */
    #pathName;

    /**
     * A list of all class names that should appear on this list item's element
     * @type {string[]}
     */
    #classes = ["tree-view-node"];

    /**
     * Constructor
     *
     * @param {string} name
     * @param {string|Number|null} value
     * @param {Object<string, any>?} attributes
     */
    constructor(name, value, attributes) {
        const valueIsInvalid = !['number', 'string'].includes(typeof value) && value != null;
        if (typeof name !== 'string' || valueIsInvalid) {
            throw new Error(
                `Cannot create a new list item. A string for the name and either a string or a number for ` +
                `the value is required. Received a ${typeof name} and ${typeof value} instead`
            );
        }

        if (attributes != null && typeof attributes !== 'object') {
            throw new Error(
                `Cannot create a new list item. The given attributes must be null or an object but received ` +
                `${typeof attributes} instead`
            );
        }
        this.#name = name;
        this.#value = value;

        if (attributes != null && typeof attributes == "object") {
            this.#attributes = Object.assign(this.#attributes, attributes);
            this.#description = attributes.description;
        }

        if (Object.hasOwn(this.#attributes, "identifier")) {
            this.#pathName = this.#attributes.identifier.replaceAll(/[ +!`~#$%^&*()|\\/<>,.=\[\]{}]/g, "-")
        }
        else if (Object.hasOwn(this.#attributes, "path")) {
            this.#pathName = this.#attributes.path.replaceAll(/[ +!`~#$%^&*()|\\/<>,.=\[\]{}]/g, "-")
        }
        else {
            this.#pathName = name.replaceAll(/[ +!`~#$%^&*()|\\/<>,.=\[\]{}]/g, "-")
        }

        this.on("click", this.clicked);
    }

    get name() {
        return this.#name;
    }

    get description() {
        return this.#name;
    }

    get value() {
        if (this.#nestedItems.length > 0) {
            let children = this.#childType.toLowerCase() === 'object' ? {} : [];

            for (let child of this.#nestedItems) {
                if (child == null) {
                    continue;
                }

                if (Array.isArray(children)) {
                    children.push(child.value);
                }
                else {
                    children[child.name] = child.value;
                }
            }

            return children;
        }
        return this.#value;
    }

    get owner() {
        return this.#owner;
    }

    get path() {
        let parentPath = "";

        if (this.#owner != null) {
            parentPath = this.#owner.path;
        }

        return `${parentPath}/${this.#pathName}`;
    }

    get element() {
        return this.#element;
    }

    set childType(type) {
        if (typeof type != 'string') {
            throw new Error(`Cannot set the child type of a list item - the value must be a string, not a ${typeof type}`);
        }
        else if (!['array', 'object'].includes(type)) {
            throw new Error(`Cannot set the child type of a list item - "${type}" is not a valid type of child`);
        }

        this.#childType = type;
    }

    setOwner = (owner) => {
        if (owner instanceof TreeView || owner instanceof TreeViewNode) {
            this.#owner = owner;
        }
        else {
            throw new Error("The given item is not a valid owner for this list selector item");
        }
    }

    addEntryToTree = (listItem) => {
        this.#owner.addEntryToTree(listItem);
    }

    /**
     *
     * @param {string} name
     * @param {string|number|null} value
     * @param {Object<string, any>?} attributes
     */
    add = (name, value, attributes) => {
        const newListItem = new TreeViewNode(name, value, attributes);
        this.addNestedItem(newListItem);
        return newListItem;
    }

    addNestedItem = (listItem) => {
        if (listItem instanceof TreeViewNode) {
            listItem.setOwner(this);
            listItem.addClass("child-tree-view-node");
            this.#nestedItems.push(listItem);

            if (this.#element != null) {
                this.#renderChild(listItem);
            }

            this.addEntryToTree(listItem);

            if (this.#attributes.ignoreParent) {
                this.#canSelect = false;
                this.addClass("unselectable-tree-view-node");
            }
        }
        else {
            throw new Error(`${listItem} is not a ListSelectorItem and cannot be added.`);
        }
    }

    /**
     * Remove a nested item based off of its name
     * @param {string} name
     */
    removeNestedItem = (name) => {
        for (let index = 0; index < this.#nestedItems.length; index += 1) {
            if (this.#nestedItems[index].name === name) {
                this.#nestedItems.splice(index, 1);
                return;
            }
        }
    }

    /**
     * Remove all nested items that meet the given criteria
     * @param {(TreeViewNode) => boolean} predicate
     */
    removeNestedItems = (predicate) => {
        /**
         * Names of items that should be removed
         * @type {string[]}
         */
        const removalNames = [];

        this.#nestedItems.forEach(
            nestedItem => {
                if (predicate(nestedItem)) {
                    removalNames.push(nestedItem.name);
                }
            }
        )

        removalNames.forEach(name => this.removeNestedItem(name));
    }

    getAttribute = (name) => {
        if (Object.hasOwn(this.#attributes, name)) {
            return this.#attributes[name];
        }

        return null;
    }

    setAttribute = (name, value) => {
        this.#attributes[name] = value;
    }

    get attributes() {
        return Object.assign({}, this.#attributes);
    }

    /**
     * Adds an event handler
     *
     * @param {string} eventName The name of the event to bind the handler to
     * @param {(Event) => any} handler The function that will fire when the event is triggered
     * @param {Object?} thisElement An optional override for the 'this' element within the function
     */
    on = (eventName, handler, thisElement) => {
        if (thisElement != null) {
            handler.bind(thisElement);
        }

        if (!Object.hasOwn(this.#events, eventName)){
            this.#events[eventName] = [];
        }

        this.#events[eventName].push(handler);

        this.#applyEventHandlers();
    }

    /**
     * Remove all event handlers for a given event
     * @param {string} eventName
     */
    off = (eventName) => {
        this.#removeAllHandlers();
        if (Object.hasOwn(this.#events, eventName)) {
            this.#events[eventName] = [];
        }

        if (eventName === 'click') {
            this.on("click", this.clicked);
        }

        this.#applyEventHandlers();
    }

    /**
     * Convert the list item into an HTML element
     * @returns {HTMLLIElement}
     */
    render = () => {
        if (this.#childContainer != null) {
            this.#childContainer.remove();
            this.#childContainer = null;
        }

        if (this.#element != null) {
            this.#element.remove();
        }

        this.#element = document.createElement("li");
        this.#element.id = `${this.path}-selector-item`;

        let container;
        let keyTag;

        if (this.#nestedItems.length > 0) {
            container = document.createElement("details");
            this.#element.appendChild(container);
            keyTag = "summary";
        }
        else {
            container = this.#element;
            keyTag = "span";
        }

        const nameTag = document.createElement(keyTag);
        nameTag.id = this.path;
        nameTag.textContent = this.name;
        nameTag.className = "tree-view-node-name";

        if (typeof this.value !== 'object') {
            this.#element.setAttribute("value", this.value);
            nameTag.setAttribute("value", this.value);
        }

        container.appendChild(nameTag);

        this.#nestedItems.forEach(item => this.#renderChild(item, container));

        for (let [key, value] of Object.entries(this.#attributes)) {
            if (key !== 'value' && Array.isArray(value)) {
                this.#element.setAttribute(key, value.join(","));
            }
            else if (key !== 'value' && typeof value !== 'object') {
                this.#element.setAttribute(key, value);
            }
        }

        this.#updateClasses();
        this.#applyEventHandlers();

        return this.#element;
    }

    /**
     * Add an HTML element for nested items
     * @param {TreeViewNode} listItem
     * @param {HTMLElement?} container
     */
    #renderChild = (listItem, container) => {
        if (this.#childContainer == null) {
            this.addClass("tree-view-node-parent");
            this.#childContainer = document.createElement("ul");
            this.#childContainer.id = this.path + "-children";
            this.#childContainer.className = "tree-view-node-children";

            if (container != null) {
                container.appendChild(this.#childContainer);
            }
            else {
                this.#element.appendChild(this.#childContainer);
            }
        }

        this.#childContainer.appendChild(listItem.render())
    }

    #applyEventHandlers = () => {
        if (this.#element == null) {
            return;
        }

        this.#removeAllHandlers();

        for (let [eventName, handlers] of Object.entries(this.#events)) {
            for (let handler of handlers) {
                try {
                    this.#element.removeEventListener(eventName, handler);
                } catch {

                }
            }
            handlers.forEach(handler => this.#element.addEventListener(eventName, handler));
        }
    }

    #removeAllHandlers = () => {
        for (let [eventName, handlers] of Object.entries(this.#events)) {
            for (let handler of handlers) {
                try {
                    this.#element.removeEventListener(eventName, handler);
                } catch {
                    console.warn(`Could not remove a handler for the ${eventName} event`);
                }
            }
        }
    }

    addClass = (className) => {
        if (!this.#classes.includes(className)) {
            this.#classes.push(className);
            this.#updateClasses();
        }
    }

    removeClass = (className) => {
        if (this.#classes.includes(className)) {
            this.#classes.splice(this.#classes.indexOf(className), 1);

            this.#updateClasses();
        }
    }

    #updateClasses = () => {
        if (this.#element != null) {
            this.#element.className = this.#classes.join(" ");
        }
    }

    /**
     * Set the given list item as the selected value
     * @param {TreeViewNode?} listItem
     * @param {Event?} event
     */
    select = async (listItem, event) => {
        if (listItem == null) {
            listItem = this;
        }

        if (this === listItem && !this.#canSelect) {
            return;
        }

        await this.#owner.select(listItem, event);
    }

    setSelectedStyle = () => {
        this.addClass(SELECTED_LIST_ITEM_CLASS);
    }

    removeSelectedStyle = () => {
        this.removeClass(SELECTED_LIST_ITEM_CLASS);
    }

    /**
     * Trigger all handlers that have been registered to a given event
     *
     * Nothing will happen if no handlers have been registered to the given event
     *
     * @param {string} eventName The name of the event being triggered
     * @param {Event} event Input data that spurred the event
     */
    trigger = async (eventName, event) => {
        if (Object.hasOwn(this.#events, eventName)) {
            this.#events[eventName].forEach((handler) => handler(event));
            for (let handler of this.#events[eventName]) {
                let result = handler(event);

                while (result instanceof Promise) {
                    result = await result;
                }
            }
        }
    }

    /**
     * The base handler for the click event on the list item
     * @param event
     */
    clicked = async (event) => {
        event.stopPropagation();
        await this.select(this, event);
    }

    toString = () => {
        return `${this.name} => ${this.value}`;
    }
}

export class TreeView {
    /**
     * Form a ListSelector around a javascript object
     *
     * @param {string} identifier
     * @param {HTMLElement} parent
     * @param {Object<string, any>|string} data
     * @param {Object<string, any>?} attributes
     * @param {SelectorObjectConstructor?} constructor
     */
    static fromObject = (identifier, parent, data, attributes, constructor) => {
        if (typeof data === 'string') {
            data = JSON.parse(data);
        }

        if (constructor == null) {
            return SelectorObjectConstructor.construct(identifier, parent, data, attributes);
        }

        return constructor.convert(identifier, parent, data, attributes);
    }
    /**
     * The items within the list
     * @type {Object<string, TreeViewNode>}
     */
    #items = {};

    /**
     * The direct children of the root
     * @type {TreeViewNode[]}
     */
    #children = [];

    /**
     * The HTML element that serves as the parent of this list selector
     * @type {HTMLElement}
     */
    #parent;

    /**
     * The root element of the rendered tree
     * @type {HTMLUListElement|null}
     */
    #root = null;

    /**
     * The item that has been selected
     * @type {TreeViewNode}
     */
    #selectedItem = null;

    /**
     * The central DOM id for this selector
     * @type {string}
     */
    #identifier;

    /**
     * Event handlers that may be registered
     * @type {Object<string, ((Event) => any)[]>}
     */
    #events = {};

    /**
     *
     * @param {string} identifier
     * @param {HTMLElement|Object} parent
     */
    constructor(identifier, parent) {
        if (/[ +=:><?\/\\()\[\]{}"';,.@#`~$%^&*|]/g.test(identifier)) {
            throw new Error(
                `"${identifier}" is not a valid identifier for a list selector. It must be a valid HTML element ID`
            );
        }

        if (!(parent instanceof HTMLElement) && Object.hasOwn(parent, 0)) {
            parent = parent[0];
        }

        if (!(parent instanceof HTMLElement)) {
            throw new Error("A parent DOM element is required when building a List Selector");
        }

        this.#parent = parent;
        this.#identifier = identifier;
    }

    get path() {
        return this.#identifier;
    }

    get selectedValue() {
        if (this.#selectedItem == null) {
            return null;
        }

        return this.#selectedItem.value;
    }

    get selectedItem() {
        return this.#selectedItem;
    }

    clear = () => {
        for (let childName of Object.keys(this.#items)) {
            delete this.#items[childName];
        }

        while (this.#children.length > 0) {
            this.#children.pop();
        }

        this.#selectedItem = null;
    }

    /**
     * Populate this tree with new data
     *
     * @param {Object<string, any>} data
     * @param {Object<string, any>?} attributes
     * @param {SelectorObjectConstructor?} constructor
     * @returns {TreeView}
     */
    populate = (data, attributes, constructor) => {
        this.clear();

        if (constructor == null) {
            return SelectorObjectConstructor.instance.populate(this, data, attributes);
        }
        else {
            return constructor.populate(this, data, attributes);
        }
    }

    /**
     * Find all list items that match the given path
     * @param {string} path A search string that should match the path of one or more children
     * @returns {TreeViewNode[]}
     */
    find = (path) => {
        let searchPath = path.replaceAll("\/", "\\/");
        searchPath = searchPath.replaceAll("*", "(?<=(^|\\/))[a-zA-Z_0-9-](?=(\\/|$))");
        let searchPattern = new RegExp(searchPath, 'g');

        /**
         * Children whose path matches the one given
         * @type {TreeViewNode[]}
         */
        const matchingChildren = [];

        for (let [childPath, listItem] of Object.entries(this.#items)) {
            if (searchPattern.test(childPath)) {
                matchingChildren.push(listItem);
            }
        }

        return matchingChildren;
    }

    /**
     * Gets the values of all found items
     * @param {string} path
     * @returns {any[]}
     */
    findValues = (path) => {
        const items = this.find(path);

        const foundValues = [];

        for (let item of items) {
            if (item != null) {
                foundValues.push(item.value);
            }
        }

        return foundValues;
    }

    /**
     * Finds all HTML elements that match the given path
     * @param {string} path
     * @returns {(HTMLLIElement)[]}
     */
    getElements = (path) => {
        let matchingElements = this.find(path).map(listItem => listItem.element);
        matchingElements.filter(element => element != null);
        return matchingElements;
    }

    /**
     * Adds a list item from the collection
     * @param {TreeViewNode} listItem
     */
    addItem = (listItem) => {
        if (listItem == null || !(listItem instanceof TreeViewNode)) {
            throw new Error(`${listItem} is not a ListSelectorItem and cannot be added.`);
        }

        if (this.#children.some(item => item.name === listItem.name)){
            throw new Error(`This set of list items already contains "${listItem.toString()}"`);
        }

        listItem.setOwner(this);
        this.#children.push(listItem);
        this.#items[listItem.path] = listItem;

        if (this.#root != null) {
            this.#root.appendChild(listItem.render());
        }

        return listItem;
    }

    /**
     * Add a new list item
     *
     * @param {string} name
     * @param {string|Number} value
     * @param {Object<string, any>?} attributes
     */
    add = (name, value, attributes) => {
        return this.addItem(new TreeViewNode(name, value, attributes));
    }

    addEntryToTree = (listItem) => {
        this.#items[listItem.path] = listItem;
    }

    /**
     *
     * @param {TreeViewNode} listItem
     * @param {Event} event
     */
    select = async (listItem, event) => {
        if (listItem == null) {
            throw new Error("Cannot select a nonexistent list item");
        }
        else if (!Object.hasOwn(this.#items, listItem.path)) {
            throw new Error(`Cannot select the "${listItem.toString()}" item; it cannot be found within the tree`);
        }

        if (this.#selectedItem != null) {
            this.#selectedItem.removeSelectedStyle();
        }

        if (this.#selectedItem != null && this.#selectedItem.path === listItem.path) {
            this.#selectedItem = null;
        }
        else {
            this.#selectedItem = listItem;
        }

        if (this.#selectedItem != null) {
            this.#selectedItem.setSelectedStyle();
        }

        await this.trigger("select", event);
    }

    render = () => {
        if (this.#root != null) {
            this.#root.remove();
        }

        if (document.getElementById(this.#identifier) != null) {
            throw new Error(
                `There is already an item at #${this.#identifier} in the DOM. The list selector cannot be created`
            );
        }

        this.#root = document.createElement("ul");
        this.#root.id = this.#identifier;
        this.#root.className = "tree-view";

        for (let child of this.#children) {
            this.#root.appendChild(child.render());
        }

        this.#parent.appendChild(this.#root);
        return this.#root;
    }

    on = (eventName, handler, thisElement) => {
        if (!Object.hasOwn(this.#events, eventName)) {
            this.#events[eventName] = [];
        }

        if (thisElement != null) {
            handler.bind(thisElement);
        }

        this.#events[eventName].push(handler);
    }

    off = (eventName) => {
        if (!Object.hasOwn(this.#events, eventName)) {
            delete this.#events[eventName];
            this.#events[eventName] = [];
        }
    }

    trigger = async (eventName, event) => {
        if (Object.hasOwn(this.#events, eventName)) {
            for (let handler of this.#events[eventName]) {
                let result = handler(event);
                while (result instanceof Promise) {
                    result = await result;
                }
            }
        }
    }

    /**
     * Convert this tree into a JSON object
     * @param {boolean?} toJSONString Whether the generated object should be returned as a JSON string instead of an object
     * @returns {Object<string, any>|string}
     */
    toJSON = (toJSONString) => {
        if (toJSONString == null) {
            toJSONString = false;
        }

        const finalObject = {};

        for (let child of this.#children) {
            finalObject[child.name] = child.value;
        }

        if (toJSONString) {
            return JSON.stringify(finalObject, null, 4);
        }

        return finalObject;
    }
}

updateObject(
    window,
    {
        widgets: {
            tree: {
                TreeView: TreeView,
                constructors: {
                    SelectorObjectConstructor: SelectorObjectConstructor
                }
            }
        }
    }
);