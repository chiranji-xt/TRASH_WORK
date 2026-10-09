import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import HeatmapLayer from "./HeatmapLayer";
import "leaflet/dist/leaflet.css";

export default function MapView({ detections }) {
  return (
    <div className="inv-card overflow-hidden p-2">
      <div className="h-[450px] w-full overflow-hidden rounded-xl">
        <MapContainer center={[19.076, 72.8777]} zoom={13} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <HeatmapLayer points={detections} />
          {detections.map((d, index) => (
            <Marker key={index} position={[d.lat, d.lon]}>
              <Popup>
                <b>Detection:</b> {d.type || "Waste"}
                <br />
                <b>Count:</b> {d.count || 1}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
