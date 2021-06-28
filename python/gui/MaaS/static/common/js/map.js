
const maxRows = 10;

var layerUrls = [];

var mymap = null;

var layerStyle = {
    color: "#555",
    weight: 5,
    fillColor: "#00ad79",
    fillOpacity: 0.6
};

var lineStyle = {
    color: "#0328fc",
    weight: 5,
    fillColor: "#0328fc",
    fillOpacity: 0.6
};

var selectedShapeStyle = {
    fillColor: "#fce803"
};

var selectedLineStyle = {
    weight: 10,
    color: "#ffc130"
}

var incidentalShapeStyle = {
    fillColor: "#3a34eb"
};

var incidentalLineStyle = {

};

var activeLayer = null;
var activeLayerName = null;
var loadedLayers = {};

var selectedFeatures = {};

// Features that were only selected because another feature was selected
var incidentalFeatures = {};

var selectedLayers = {};

startup_scripts.push(
    function(){
        mymap = L.map('mapid').setView(centerLine, zoom);

        L.tileLayer(mapUrl, {
                maxZoom: maxZoom,
                attribution: attribution,
                tileSize: 512,
                zoomOffset: -1
            }).addTo(mymap);
    }
);

function getLayers() {
    var layers = [];

    if (layerUrls != null && layerUrls.length > 0) {
        // Get geojson layers and place on map
        layerUrls.forEach(
            layerUrl => function(layerUrl){
                $.ajax(
                    {
                        url: layerUrl.replaceAll("&amp;", "&"),
                        type: 'GET',
                        async: false,
                        error: function(xhr,status,error) {
                            console.error(error);
                        },
                        success: function(result,status,xhr) {
                            layers.push(result);
                        }
                    }
                );
            }(layerUrl)
        );
    }
    return layers;
}

function getServerData(serverUrl) {
    var data = [];

    $.ajax(
        {
            url: serverUrl,
            type: 'GET',
            async: false,
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                data.push(result);
            }
        }
    );

    if (data.length == 0) {
        return null;
    }

    return data[0];
}

function layerCreation(geoJsonPoint, latlng) {
    var colorIndex = 0;

    return L.circleMarker(latlng);
}

function plotMapLayers(featureDocuments, map) {
    var layers = [];

    var addTooltip = function(feature, layer) {
        if ("id" in feature) {
            layer.bindTooltip(feature["id"]);
        }
        else if ("properties" in feature && "Name" in feature["properties"]) {
            layer.bindTooltip(feature['properties']['Name']);
        }
    }

    var buildProperties = function(feature, layer) {
        layer.bindPopup(propertiesToHTML(feature), {"maxWidth": 2000})
        addTooltip(feature, layer);
    };

    var addFeature = function(featureDocument) {
        var layer = L.geoJSON(
            featureDocument.features,
            {
                onEachFeature: buildProperties,
                style: function() {return layerStyle;},
                pointToLayer: layerCreation
            }
        ).addTo(map);
        layers.push(layer);
    }

    featureDocuments.forEach(featureDocument => addFeature(featureDocument));
    return layers;
}

function propertiesToHTML(geojson) {
    var properties = geojson.properties;
    var markup = "";
    if ("Name" in properties) {
        markup += "<h3>" + properties.Name + "</h3>";
    }
    else if ("id" in geojson) {
        markup += "<h3>" + geojson.id + "</h3>";
    }

    markup += "<table style='border-spacing: 8px'>";

    var propertyKeys = [];

    for (const property in properties) {
        var propertyIsNotName = property.toLowerCase() != "name";
        var propertyIsNotBlank = properties[property] != null && properties[property] != "";
        var propertyIsNotAnObject = typeof properties[property] != 'object';
        if (propertyIsNotName && propertyIsNotBlank && propertyIsNotAnObject) {
            propertyKeys.push(property);
        }
    }

    var columnCount = Math.ceil(propertyKeys.length / maxRows);
    var rowCount = Math.min(propertyKeys.length, maxRows);

    for(rowIndex = 0; rowIndex < rowCount; rowIndex++) {
        if (rowIndex % 2 == 0) {
            markup += "<tr class='even-feature-property-row'>";
        }
        else {
            markup += "<tr class='odd-feature-property-row'>";
        }

        for (columnIndex = 0; columnIndex < columnCount; columnIndex++) {
            var keyIndex = rowIndex * columnCount + columnIndex;

            if (keyIndex < propertyKeys.length) {
                var key = propertyKeys[keyIndex];

                markup += "<td id='feature-property-key'><b>" + key + ":</b></td>";
                markup += "<td id='feature-property-value'>" + properties[key] + "</td>";
            }
        }

        markup += "</tr>";
    }

    markup += "</table>";
    return markup;
}

function getSelectedShapeStyle(feature) {
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return selectedLineStyle;
    }

    return selectedShapeStyle;
}

function getShapeStyle(feature) {
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return lineStyle;
    }

    return layerStyle;
}

function getIncidentalStyle(feature) {
    var featureExists = feature != null && typeof feature != 'undefined';
    var featureType = feature.geometry.type.toLowerCase();

    if (featureExists && featureType.includes("linestring")) {
        return incidentalLineStyle;
    }

    return incidentalShapeStyle;
}

function formSelectionPane() {
    dataPane.update(selectedFeatures);
}

function layerClicked(event) {
    var layer = event.layer;
    var feature = layer.feature;
    console.log('clicked feature: '+ feature.id);

    if (feature.id in incidentalFeatures) {
        removeFeature(feature);
        removeIncidentalFeatures(feature.id);
    }
    else {
        // Add the selected feature to the list
        selectedLayers[feature.id] = layer;
        addFeature(feature.id, feature.id);
        addIncidentalFeatures(feature.id);
    }
}

function addIncidentalFeatures(featureID) {
    $.ajax({
        url: "map/connections?id=" + featureID,
        type: 'GET',
        error: function(xhr,status,error) {
            console.error(error);
        },
        success: function(result,status,xhr) {
            incidentalFeatures[featureID] = [];

            for (feature of result['connected_locations']) {
                var featureLayers = Object.values(mymap._layers).filter(
                    layer => "feature" in layer && layer.feature.id == feature
                );

                if (featureLayers.length == 0) {
                    continue;
                }

                var featureLayer = featureLayers[0];
                var incidentalFeature = featureLayer.feature;

                // We want to color and select the feature if it wasn't manually clicked beforehand
                if (Object.keys(incidentalFeatures).indexOf(feature) < 0) {
                    featureLayer.setStyle(getIncidentalStyle(incidentalFeature));
                }

                // Reset the selection panel
                selectedLayers[feature] = featureLayer;
                selectedFeatures[feature] = feature;
                incidentalFeatures[featureID].push(feature);
            }

            formSelectionPane();
        }
    });
}

function removeIncidentalFeatures(featureID) {
    var featuresToRemove = incidentalFeatures[featureID].filter(feature => !(feature in incidentalFeatures));

    for (feature of featuresToRemove) {
        var layer = selectedLayers[feature];
        layer.setStyle(getShapeStyle(layer.feature))
        delete selectedFeatures[feature];
        delete selectedFeatures[feature];
    }

    delete incidentalFeatures[featureID];
    formSelectionPane();
}

function addFeature(descriptor, id) {
    selectedFeatures[id] = descriptor;
    selectedLayers[id].setStyle(getSelectedShapeStyle(selectedLayers[id].feature));
    formSelectionPane();
}

function removeFeature(feature) {
    selectedLayers[feature.id].setStyle(getShapeStyle(feature));

    delete selectedLayers[feature.id];
    delete selectedFeatures[feature.id];

    formSelectionPane();
}

function submitFeatures(event) {
    var featuresToConfigure = [];

    $("#value-list span.selected-value-label").each(function(index) {
        featuresToConfigure.push($(this).attr("value"));
    });

    if (featuresToConfigure.length == 0) {
        event.preventDefault();
        alert("Select a location to configure before continuing.");
        return;
    }

    var ids = featuresToConfigure.join("|");

    document.forms['location-selection-form']['feature-ids'].value = ids;
    document.forms['location-selection-form'].submit();
}

function getFabricNames() {
    var names = [];
    var fabricNames = getServerData("fabric/names");

    if (fabricNames != null) {
        names = fabricNames['fabric_names'];
    }

    return names;
}

function titleCase(str) {
    return str.replaceAll("_", " ").toLowerCase().split(' ').map(function(word) {
        return word.replace(word[0], word[0].toUpperCase());
    }).join(' ');
}

function loadFabricNames() {
    $.ajax(
        {
            url: "fabric/names",
            type: 'GET',
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                if (result != null) {
                    result['fabric_names'].forEach(function(name) {
                        $("#fabric-selector").append("<option value='" + name + "'>" + titleCase(name) + "</option>");
                    });
                    $("#fabric-selector option")[0].setAttribute("selected", "");
                    loadFabric();
                }
            }
        }
    );
}

function loadFabricTypes() {
    $.ajax(
        {
            url: "fabric/types",
            type: 'GET',
            error: function(xhr,status,error) {
                console.error(error);
            },
            success: function(result,status,xhr) {
                if (result != null) {
                    result['fabric_types'].forEach(function(name) {
                        $("#fabric-type-selector").append("<option value='" + name + "'>" + titleCase(name) + "</option>");
                    });
                    $("#fabric-type-selector option")[0].setAttribute("selected", "");
                    loadFabric();
                }
            }
        }
    );
}

function loadFabric(event) {
    var name = $("#fabric-selector").val();
    var type = $("#fabric-type-selector").val();

    $("input[name=fabric]").val(name);

    var addTooltip = function(feature, layer) {
        if ("id" in feature) {
            layer.bindTooltip(feature["id"]);
        }
        else if ("properties" in feature && "Name" in feature["properties"]) {
            layer.bindTooltip(feature['properties']['Name']);
        }
    }

    var buildProperties = function(feature, layer) {
        layer.bindPopup(propertiesToHTML(feature), {"maxWidth": 2000})
        addTooltip(feature, layer);
    };

    var addDocument = function(document) {
        var layer = L.geoJSON(
            document.features,
            {
                onEachFeature: buildProperties,
                style: getShapeStyle,
                pointToLayer: layerCreation
            }
        ).addTo(mymap);
        activeLayer = layer;

        //click popup
        activeLayer.on('click', layerClicked);

        mymap.fitBounds(activeLayer.getBounds());
    }
    var name_type = name+"|"+type;
    if (name && type &&  (name_type != activeLayerName || activeLayer == null)) {
        activeLayerName = name_type;

        if (activeLayer) {
            Object.values(selectedLayers).forEach(layer => removeFeature(layer.feature.id));
            activeLayer.remove();
        }

        if (name_type in loadedLayers) {
            addDocument(loadedLayers[name_type]);
        }
        else {
            var url = "fabric/" + name;
            $.ajax(
                {
                    url: url,
                    type: "GET",
                    data: {"fabric_type":type},
                    error: function(xhr, status, error) {
                        console.error(error);
                    },
                    success: function(result, status, xhr) {
                        if (result) {
                            loadedLayers[name_type] = result;
                            addDocument(result);
                        }
                    }
                }
            )
        }
    }
}
