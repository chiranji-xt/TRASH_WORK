import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet.heat";
import { useEffect } from "react";

// ------------------------------------------
// 1️⃣ TEMP Dummy Data (replace with backend API later)
// ------------------------------------------
const detections = Array.from({ length: 60 }, () => [
  12.97 + Math.random() * 0.02,  // latitude jitter
  77.59 + Math.random() * 0.02   // longitude jitter
]);

// ------------------------------------------
// 2️⃣ Heatmap Component
// ------------------------------------------
function HeatmapLayer({ points }) {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    const heatLayer = window.L.heatLayer(points, {
      radius: 45,
      blur: 25,
      maxZoom: 17,
      max: 2.0,          // stronger intensity
      minOpacity: 0.5,   // keeps weak heat visible
      gradient: {
        0.0: "rgba(0,0,255,0)",
        0.3: "rgba(255,255,0,0.7)",   // yellow
        0.6: "rgba(255,165,0,0.9)",   // orange
        1.0: "rgba(255,0,0,1)"        // red
      },
    });

    heatLayer.addTo(map);
    return () => map.removeLayer(heatLayer);
  }, [map, points]);

  return null;
}

// ------------------------------------------
// 3️⃣ Main Map View Page
// ------------------------------------------
export default function Map() {
  return (
    <div className="w-full h-full p-6">
      <h1 className="text-2xl font-bold mb-4">Live Report Map</h1>

      <MapContainer
        center={[12.9716, 77.5946]}
        zoom={13}
        style={{ height: "75vh", width: "100%", borderRadius: "14px" }}
      >
        {/* Background Map */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap contributors"
        />

        {/* 🔥 Heatmap */}
        <HeatmapLayer points={detections} />

        {/* Optional red markers (clickable) */}
        {detections.map((pos, idx) => (
          <CircleMarker
            key={idx}
            center={pos}
            radius={6}
            color="red"
            fillColor="red"
            fillOpacity={0.6}
          >
            <Popup>
              <strong>Detection #{idx + 1}</strong>
              <br />
              Lat: {pos[0].toFixed(5)}
              <br />
              Lon: {pos[1].toFixed(5)}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
