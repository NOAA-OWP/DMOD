
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
        if (property.toLowerCase() != "name" && properties[property] != null && properties[property] != "" && typeof properties[property] != 'object') {
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
