import { MapContainer, TileLayer } from "react-leaflet";
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
import { useRef } from "react";

const US_CENTER: LatLngTuple = [39.83, -98.58];

enum HydrofabricElement {
  Catchment = "Catchment",
  Flowpath = "Flowpath",
  Nexus = "Nexus",
}

export const HydrofabricMap = () => {
  const [drawerState, toggleDrawerState] = useToggle(true);

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
      <FormControl sx={{ m: 1, minWidth: 120, maxWidth: 150 }}>
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
      </FormControl>
      <MapContainer
        center={US_CENTER}
        zoom={5}
        scrollWheelZoom={false}
        style={{ height: 500, aspectRatio: "16/9" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
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
