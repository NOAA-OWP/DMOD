import {updateObject} from "/static/js/utilities.js";
import {SelectorObjectConstructor, TreeViewNode} from "/static/js/widgets/tree.js";

/**
 * @typedef {Object} User
 * @property {string} first_name
 * @property {string} last_name
 * @property {string} username
 * @property {boolean} is_anonymous
 * @property {string} name
 */

/**
 * @typedef {object} Template
 * @property {string} name
 * @property {string} description
 * @property {number|string} id
 * @property {User} author
 */

export class TemplateObjectConstructor extends SelectorObjectConstructor {
    /**
     *
     * @param {TreeViewNode} element
     * @param {Template|string} key
     * @param {Template|Template[]} value
     * @param {Object<string, any>?} attributes
     * @returns {TreeViewNode}
     */
    addItem = (element, key, value, attributes) => {
        let listItem;

        if (Array.isArray(value)) {
            let copiedAttributes = Object.assign({}, attributes);
            let listItem = element.add(key, key, attributes);

            for (let [index, subValue] of Object.entries(value)) {
                copiedAttributes["path"] = index;
                this.addItem(listItem, index, subValue, copiedAttributes);
            }

            listItem.childType = 'array';
        }
        else if (typeof value === 'object') {
            try {
                listItem = element.add(value.name, value.id, attributes);
                listItem.childType = 'object';
            } catch (e) {
                throw new Error(
                    `Expected Template data was incorrectly formatted - received ${value}`, {cause: e}
                );
            }
        }

        return listItem;
    }
}

updateObject(
    window,
    {
        widgets: {
            tree: {
                constructors: {
                    TemplateObjectConstructor: TemplateObjectConstructor
                }
            }
        }
    }
);
