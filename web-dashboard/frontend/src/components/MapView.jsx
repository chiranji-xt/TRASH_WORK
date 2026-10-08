import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import HeatmapLayer from "./HeatmapLayer";
import "leaflet/dist/leaflet.css";

export default function MapView({ detections }) {
  return (
    <MapContainer 
      center={[19.0760, 72.8777]}
      zoom={13}
      style={{ height: "450px", width: "100%" }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {/* Heatmap Layer */}
      <HeatmapLayer points={detections} />

      {/* Marker pins for each detection */}
      {detections.map((d, index) => (
        <Marker key={index} position={[d.lat, d.lon]}>
          <Popup>
            <b>Detection:</b> {d.type || "Waste"}<br />
            <b>Count:</b> {d.count || 1}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
