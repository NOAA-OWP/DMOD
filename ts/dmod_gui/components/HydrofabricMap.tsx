import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { LatLngTuple } from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Box,
  Button,
  Container,
  FormControl,
  InputLabel,
  ListSubheader,
  MenuItem,
  Select,
  SwipeableDrawer,
} from "@mui/material";
import useToggle from "../hooks/useToggle";
import { useEffect, useRef, useState } from "react";

export function styleSelectedCatchment(
  hucId: string | undefined,
  feature: Feature<Geometry, HucFeatureProperties> | undefined
): PathOptions {
  // band aid fix. needs to be changed later
  let opacity = 0.1;
  const featHucId = feature?.properties.hucId;
  if (featHucId !== undefined && hucId !== undefined) {
    if (featHucId === hucId.slice(0, featHucId.length)) {
      opacity = 0.4;
    }
  }

  const style: PathOptions = {
    color: "#3D624C",
    stroke: true,
    weight: 2,
    fillOpacity: opacity,
  };
  return style;
}

const US_CENTER: LatLngTuple = [39.83, -98.58];
const MAP_CENTER: LatLngTuple = [37.80771, -120.13666];

enum HydrofabricElement {
  Catchment = "Catchment",
  Flowpath = "Flowpath",
  Nexus = "Nexus",
}

export const HydrofabricMap = () => {
  const [drawerState, toggleDrawerState] = useToggle(true);
  const [mapData, setMapData] = useState(undefined);
  const [nexusData, setNexusData] = useState(undefined);
  const [selected, setSelected] = useState(() => new Set());
  const MAP_DATA_URL = "/catchment.geojson";
  const NEXUS_DATA_URL = "/nexus_data.geojson";

  useEffect(() => {
    const getMapData = async () => {
      const res = await fetch(MAP_DATA_URL);
      const data = await res.json();
      setMapData(data);

      const res2 = await fetch(NEXUS_DATA_URL);
      const data2 = await res2.json();
      setNexusData(data2);
    };
    getMapData();
  }, []);

  const addClicked = (el) => {
    setSelected((prev) => new Set(prev.add(el)));
  };

  const deleteClicked = (el) => {
    setSelected((prev) => new Set([...prev].filter((x) => x !== el)));
  };

  function handleClick(event: LeafletMouseEvent) {
    const id = event.propagatedFrom.feature.properties.id;

    if (selected.has(id)) {
      deleteClicked(id);
      return;
    }
    addClicked(id);
  }

  return (
    // SwipeableDrawer
    // Select Input use groups for HydrofabricElement
    // switch between catchment, flowpath, nexus

    <Container
      sx={{
        marginTop: "3em",
        justifyContent: "center",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* <FormControl sx={{ m: 1, minWidth: 120, maxWidth: 150 }}>
        <InputLabel htmlFor="grouped-select">Fabric</InputLabel>
        <Select defaultValue="" id="grouped-select" label="Grouping">
          {Object.values(HydrofabricElement).map((v, idx) => {
            return (
              <MenuItem key={idx} value={v}>
                {v}
              </MenuItem>
            );
          })}
        </Select>
      </FormControl> */}
      <MapContainer
        center={MAP_CENTER}
        zoom={7}
        scrollWheelZoom={false}
        style={{ height: 500, aspectRatio: "16/9" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {mapData && (
          <GeoJSON
            data={mapData}
            eventHandlers={{ click: handleClick }}
            style={(feature) => {
              return selected.has(feature?.properties.id)
                ? { fillOpacity: 0.8 }
                : { fillOpacity: 0.3 };
            }}
          />
        )}
        {/* {nexusData && (
          <GeoJSON data={nexusData} onEachFeature={(f) => console.log(f)} />
        )} */}
        {/* <LayersControl.Overlay name="Feature group">
        <FeatureGroup pathOptions={{ color: 'purple' }}>
          <Popup>Popup in FeatureGroup</Popup>
          <Circle center={[51.51, -0.06]} radius={200} />
          <Rectangle bounds={rectangle} />
        </FeatureGroup>
      </LayersControl.Overlay>
    </LayersControl>  */}
      </MapContainer>
    </Container>
  );
};

export default HydrofabricMap;
