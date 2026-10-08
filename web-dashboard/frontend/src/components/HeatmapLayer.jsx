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

    const heatLayer = L.heatLayer(heatmapData, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
    }).addTo(map);

    return () => {
      map.removeLayer(heatLayer);   // ← removes old layer before adding new
    };
  }, [points, map]);

  return null;
}
