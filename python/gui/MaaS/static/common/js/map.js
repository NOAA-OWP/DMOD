
const maxRows = 10;

var layerUrls = [];
var mymap = null;
var layerStyle = {};

const colorCycle = [
    "#5db4e4",
    "#e69f25",
    "#079f72",
    "#f1e444",
    "#cc79a8",
    "#d35f27",
    "#0773b2",
    "#000"
];

var selectedFeatures = {};
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

        var layers = getLayers();

        plotMapLayers(layers, mymap);
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

function getLayer(layerUrl) {
    var layers = [];

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

    return layers;
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

function getSelectedShapeStyle() {
    return {
        fillColor: "#fce803",
    };
}

function getShapeStyle() {
    return {
        color: "#555",
        weight: 5,
        fillColor: "#00ad79",
        fillOpacity: 0.6
    };
}

function formSelectionPane() {
    dataPane.update(selectedFeatures);
}

function layerClicked(event) {
    var layer = event.target;
    var feature = layer.feature;
    console.log('clicked feature: '+ feature.id);

    if (feature.id in selectedFeatures) {
        removeFeature(feature.id);
    }
    else {
        // Add the selected feature to the list
        selectedLayers[feature.id] = layer;
        addFeature(feature.id, feature.id);
    }
}

function addFeature(descriptor, id) {
    selectedFeatures[id] = descriptor;
    selectedLayers[id].setStyle(getSelectedShapeStyle());
    formSelectionPane();
}

function removeFeature(id) {
    selectedLayers[id].setStyle(getShapeStyle());

    delete selectedLayers[id];
    delete selectedFeatures[id];

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

$(function() {

    function onLayerCreation(feature, layer) {
        var popupContent = propertiesToHTML(feature)

        //hover popup
        layer.bindTooltip(popupContent, {closeButton: false, offset: L.point(0, -20)});

        //click popup
        layer.on('click', layerClicked);
    }

    var catchment_layer = L.geoJSON(
        catchments,
        {
            style: getShapeStyle(),
            onEachFeature: onLayerCreation
        }
    );

    catchment_layer.addTo(mymap);
    mymap.fitBounds(catchment_layer.getBounds());
});
