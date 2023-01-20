/**
 * Create an Object that controls a newly rendered map
 *
 * @param {String} elementID The ID of the element to render the map on
 * @param {Object} options Optional options used to render the map
 * @return {Object} An object containing functions to call to manipulate the map
 **/
function initializeActiveMap(elementID, options) {
    // Initialize the leaflet map and expose functions for manipulating it

    // The leaflet map object
    let internalMap = L.map(elementID);

    // The layer that will contain loaded geometry
    let geometryGroup = L.featureGroup();
    geometryGroup.addTo(internalMap);

    // A binding between location names and layers for easy access
    let layerCatalog = {};

    // A mapping between the name of a location and an object containing pertinent information about it
    let featureDetails = {};

    let mostRecentLayer = geometryGroup;

    if (options == null) {
        options = {};
    }

    let maxRows = 10;

    if ("maxRows" in options) {
        maxRows = options.maxRows;
    }

    // Default to coordinates over mid-America, then reassign to the configured value if it's been passed
    var centerLine = [37.0902, -95.7129];

    if ("centerLine" in options) {
        centerLine = options.centerLine;
    }

    // Default to a zoom level of six, then reassign the configured value if its there
    var zoom = 6;
    if ("zoom" in options) {
        zoom = options.zoom;
    }

    // Set the view of the map to the correct location
    internalMap.setView(centerLine, zoom);

    // Default the name of the map to the ID of the element where it's rendered, then reassign to the configured if
    // it's there
    let name = elementID;

    if ("name" in options) {
        name = options.name;
    }

    let attribution = 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';;
    if ("attribution" in options) {
        attribution = options.attribution;
    }

    let mapUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

    if ("mapUrl" in options) {
        mapUrl = options.mapUrl;
    }

    let maxZoom = 18;

    if ("maxZoom" in options) {
        maxZoom = options.maxZoom;
    }

    // Add the tiles to show the basemap
    var tileLayer = L.tileLayer(
        mapUrl,
        {
            maxZoom: maxZoom,
            attribution: attribution
        }
    );

    tileLayer.addTo(internalMap)

    /**
     * Add an event handler to the map itself
     *
     * @param {String} eventName The name of the event to handle
     * @param {function|String|Array} handler Either a function to call when the event is fired,
     *                                        the name of the function to call when the event is fired,
     *                                        or an array of functions to call when the event is fired
     **/
    const _attachEventHandler = (eventName, handler) => {
        // Add each handler to the event if an array is passed
        if (Array.isArray(handler)){
            // Call this function for each handler. This will work for nested lists
            handler.forEach(handler => _attachEventHandler(eventName, handler))
        }
        else if (typeof handler === 'function') {
            internalMap.on(eventName, handler);
        }
        else if (typeof handler === 'string') {
            // Call a window scoped function if a String is passed
            if (handler in window) {
                internalMap.on(eventName, window[handler]);
            }
            else {
                console.error(
                    'Cannot add "' + handler + '" as an event handler for the map named "' + name +
                    '"; there is no such function in the scope of the window'
                )
            }
        }
    };

    // Add everything in 'on' as an event handler
    if ("on" in options) {
        /*
            These should be formatted like:

            {
                "click": [(event) => ..., "clickMap", ...],
                "overlayadd": (event) => ...,
                "overlayremove": "removeOverlay"
            }

            In that it should be key value pairs from event name to either:
                - Function definition
                - function name
                - array of function definitions or names of functions

            window[function name](event) should be able to handle functions by name
        */
        Object.entries(options.on).forEach(([eventName, handler]) => _attachEventHandler(eventName, handler));
    }

    const _getGlobalFeatureBounds = () => {
        return geometryGroup.getBounds();
    };

    const _setMostRecentLayer = (layer) => {
        mostRecentLayer = layer;
    };

    /**
     * Clear the geometry and layer catalog. Layer details are not cleared in order to keep any sort of necessary
     * information in case the geometry is just refreshed or similar shapes are added later
     **/
    const _clearFeatures = () => {
        geometryGroup.clearLayers();
        Object.keys(layerCatalog).forEach(key => delete layerCatalog[key]);
    };

    /**
     * Add details about a location that should be rendered with it
     *
     * @param {String} name The name of the location
     * @param {Object} details key-value pairs describing details to attach to the location
     */
    const _addDetails = (name, details) => {
        if (typeof details != 'object') {
            throw "Can't add details - the passed value must be an object"
        }

        if (!(name in featureDetails)) {
            featureDetails[name] = {};
        }

        Object.entries(details).forEach(([key, value]) => featureDetails[name][key] = value);

        if (name in layerCatalog) {
            var layer = layerCatalog[name];

            var newPopupMarkup = _buildPopup(layer);

            layer.unbindPopup();
            layer.bindPopup(newPopupMarkup);
        }
    };

    const _getFeatureName = (layer) => {
        if (layer == null || !("feature" in layer)) {
            return null;
        }

        var name = null;

        // Try to find a name for the feature - it should be given underneath the feature object as 'id'
        if ("id" in layer.feature) {
            name = layer.feature.id;
        }
        else if ("properties" in layer.feature) {
            // If no feature level id was given, try to pick off a name from its properties
            var properties = layer.feature.properties;

            // Default to the 'name' property if it's present - this will generally be more human friendly
            if ("name" in properties) {
                name = properties.name;
            }
            else if ("id" in properties) {
                name = properties.id;
            }
        }

        return name;
    }

    const _buildPopup = (layer) => {
        var name = _getFeatureName(layer);

        // @todo Change markup creation from string creation to element creation
        var markup = "";

        if (name) {
            markup += "<h3>" + name + "</h3>\n";

            if (name in featureDetails) {
                var details = featureDetails[name];

                // Create an updated version of the name that may be used as an ID
                //    Replace any whitespace, colons, brackets, braces, or parenthesis with '_'
                var cleanName = name.replace(/[\W:\(\)\{\}]/g, "_");

                // Reduce the number of duplicated '_' characters
                cleanName = cleanName.replace(/__/g, "");
                var tableID = `active-map-${cleanName}-table`;
                markup += `<table class="active-map-popup-table" id="${tableID}-table">\n`

                var keysToRender = [];

                for (const [detailKey, detailValue] in Object.entries(details)) {
                    var propertyIsNotName = detailValue != name;
                    var propertyIsNotBlank = detailValue != null && detailValue != "";
                    var propertyIsNotAnObject = typeof detailValue != 'object';
                    if (propertyIsNotName && propertyIsNotBlank && propertyIsNotAnObject) {
                        keysToRender.push(detailKey);
                    }
                }

                var detailCount = keysToRender.length;

                var columnCount = Math.ceil(detailCount / maxRows);
                var rowCount = Math.min(detailCount, maxRows);

                for(var rowIndex = 0; rowIndex < rowCount; rowIndex++) {
                    if (rowIndex % 2 == 0) {
                        markup += "<tr class='even-active-map-table-row'>\n";
                    }
                    else {
                        markup += "<tr class='odd-active-map-table-row'>\n";
                    }

                    for (columnIndex = 0; columnIndex < columnCount; columnIndex++) {
                        var keyIndex = rowIndex * columnCount + columnIndex;

                        if (keyIndex < keysToRender.length) {
                            var key = keysToRender[keyIndex];

                            markup += "<td id='active-map-table-key'><b>" + key + ":</b></td>\n";
                            markup += "<td id='active-map-table-value'>" + details[key] + "</td>\n";
                        }
                    }

                    markup += "</tr>\n";
                }

                markup += "</table>";
            }
        }
        else {
            markup += "<h3>Unknown Location</h3>";
        }

        return markup;
    }

    /**
     * Add passed leaflet layer to the map
     *
     * @param {Layer} geometry Layer to add to the internal map
     **/
    const _addGeometry = (geometry) => {
        var name = _getFeatureName(geometry)

        // Remove the geometry if it's already present. There is nothing saying that these two are the same
        if (name && name in layerCatalog) {
            geometryGroup.removeLayer(layerCatalog[name]);
        }

        // Add the layer to the map
        geometryGroup.addLayer(geometry);

        var popupMarkup = _buildPopup(geometry);

        if (popupMarkup) {
            geometry.bindPopup(popupMarkup);
        }

        // Attach the layer to the layer catalog so it may be found by its name later on
        if (name) {
            layerCatalog[name] = geometry;
            geometry.bindTooltip(name);
        }
        else {
            console.warn("No name could be found for the layer being added. It may not be found by name.");
        }
    };

    // Return an object containing functions that will allow the internal map to be manipulated
    return {
        /**
         * Add an event handler to the map
         *
         * @param {String} eventName The name of the event to handle
         * @param {function|String|Array} handler Either a function to call when the event is fired,
         *                                        the name of the function to call when the event is fired,
         *                                        or an array of functions to call when the event is fired
         **/
        "on": function(eventName, handler) {
            _attachEventHandler(eventName, handler);
        },
        /**
         * Try to get a layer based on its name
         *
         * @param {String} identifier The name of the layer/feature being retrieved
         * @return {Layer} The leaflet layer containing the requested feature. null if the feature is not found
         **/
        "getFeature": (identifier) => {
            if (identifier in layerCatalog) {
                return layerCatalog[identifier];
            }
            return null;
        },
        /**
         * Update the size of the map and its contents to ensure everything is rendered properly
         **/
        "updateSize": () => {
            internalMap.invalidateSize();
            if (geometryGroup.getLayers().length > 0) {
                internalMap.fitBounds(geometryGroup.getBounds());
            }
        },
        /**
         * Get a reference to the internal map
         *
         * ONLY USE FOR DIAGNOSTIC OR DEVELOPMENTAL PURPOSES
         *
         * @return {Leaflet} The map
         **/
        "getMap": () => {
            console.warn(
                "'getMap' called on an active_map; " +
                "it is recommended to update the active_map to reveal the requested functionality"
            );
            return internalMap;
        },
        "addDetails": _addDetails,
        "clear": _clearFeatures,
        "getBounds": _getGlobalFeatureBounds,
        /**
         * Add the contents of a GeoJSON document to the map
         *
         * @param {Object} geoJSON The GeoJSON object to add
         **/
        "plotGeoJSON": (geoJSON) => {
            // Create a new layer group containing all the geometries described in the document as gray
            // shapes to be styled later
            let geojsonLayer = L.geoJSON(
                geoJSON,
                {
                    "style": function(feature) {
                        return {
                            "color": "#999999"
                        }
                    }
                }
            );

            // Add each layer individually so they are added to the correct group and have their names linked
            geojsonLayer.eachLayer(_addGeometry);

            // Reposition the map to feature the new locations
            internalMap.fitBounds(geojsonLayer.getBounds());
        },
        "getContainer": () => {
            return internalMap.getContainer();
        }
    }
}