import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";

export default function HeatmapLayer({ points }) {
  const map = useMap();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const heatmapData = points.map((p) => [
      p.latitude ?? p.lat,
      p.longitude ?? p.lon,
      p.confidence || p.count || 0.8,
    ]);

    // Vivid thermal gradient (deep blue -> cyan -> green -> yellow -> orange -> red)
    // so even small clusters read clearly at any zoom.
    const heatLayer = L.heatLayer(heatmapData, {
      radius: 50,
      blur: 32,
      maxZoom: 18,
      minOpacity: 0.45,
      max: 3.0,
      gradient: {
        0.0: "#0d0887",
        0.2: "#3b4cc0",
        0.35: "#00c2d1",
        0.5: "#4ae54a",
        0.65: "#f5e61d",
        0.8: "#fb8d0d",
        1.0: "#e5484d",
      },
    }).addTo(map);

    return () => {
      map.removeLayer(heatLayer);   // ← removes old layer before adding new
    };
  }, [points, map]);

  return null;
}
