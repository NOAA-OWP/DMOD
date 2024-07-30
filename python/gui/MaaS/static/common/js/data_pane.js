const DataPane = {
    create: function(elementID) {
        const id = elementID;
        const paneID = elementID + " #data-pane"
        var currentData = null;
        var submissionHandler = null;

        this.resizeWrapper(null, id);

        $(window).resize(
            function(event) {
                DataPane.resizeWrapper(event, id);
            }
        );

        const hidePane = function() {
            $(paneID).hide(500);
            $(id).removeClass("active-pane");
        }

        const showPane = function() {
            $(id).addClass("active-pane");
            $(paneID).show(500);
        }

        const clearContents = function() {
            $(paneID + " #value-list").empty();
        };

        const removeClickedValue = function(event) {
            var id = this.attributes.value.value;
            var feature = selectedLayers[id].feature
            removeFeature(feature);
        }

        const addValues = function(selectedValues) {
            var iteration = 0;
            for (const [description, value] of Object.entries(selectedValues)) {
                iteration++;
                var rowClass = "odd-row";
                if (iteration % 2 == 0) {
                    rowClass = "even-row";
                }
                var valueLine = `<div id="${value}" class="${rowClass} value-name-cell value-row" style="grid-row: ${iteration}; grid-column: 1;">`;
                valueLine += `<span value="${value}" class="selected-value-label">${description}</span>`;
                valueLine += "</div>";

                valueLine += `<div id="${value}-remover" class="${rowClass} value-row" style="grid-row: ${iteration}; grid-column: 2;">`;
                valueLine += `<span value="${value}" class="remove-button">❌</span>`;
                valueLine += "</div>";

                $(paneID + " #value-list").append(valueLine);
            }

            $(paneID + " .remove-button").on("click", removeClickedValue);

            if (iteration > 0) {
                showPane();
            }
            else {
                hidePane();
            }
        }


        $(id + " #pane-expander").click(function(event){$(paneID).toggle(500);});

        $(paneID + " #submit-values-button").click(function(event){
            event.preventDefault();

            if (submissionHandler != null) {
                submissionHandler(event);
            }
        });

        return {
            update: function(selectedValues) {
                currentData = selectedValues;
                clearContents();
                addValues(selectedValues);
            },
            getCurrentData: function() {
                var copy = {};
                return Object.assign(copy, currentData);
            },
            show: function() {
                showPane();
            },
            hide: function() {
                hidePane();
            },
            setOnSubmit: function(func) {
                submissionHandler = func;
            },
            getID: function() {
                return paneID;
            }
        };
    },
    resizeWrapper: function(event, id) {
        $(id).css("top", $("#content.pane")[0].offsetTop);
        $(id).css("right", $("#content.pane")[0].offsetLeft);
        $(id).height($("#content.pane").height());
    },
    titleCase: function(str) {
        return str.replaceAll("_", " ").toLowerCase().split(' ').map(function(word) {
            return word.replace(word[0], word[0].toUpperCase());
        }).join(' ');
    },
    instances: {
        _values: {},
        add: function(pane) {
            this._values[pane.getID()] = pane;
        },
        remove: function(name) {
            delete this._values[name];
        }
    }
};

function createDataPane(id) {
    var pane = DataPane.create(id);
    DataPane.instances.add(pane);
    return pane;
}
