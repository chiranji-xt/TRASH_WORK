import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Correct working cluster library
import MarkerClusterGroup from "@changey/react-leaflet-markercluster";

// Required CSS
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { fetchAllReports, getImageUrl } from "../api/reportsApi";
import { useEffect, useState, useRef } from "react";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST } from "../utils/timezone";
import L from "leaflet";

// --- CUSTOM ICONS ---
const defaultIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Color map
const classColors = {
  Plastic: "blue",
  Organic: "green",
  Metal: "red",
  "E-Waste": "purple",
  Hazardous: "black",
  plastic: "blue",
  organic: "green",
  metal: "red",
  "e-waste": "purple",
  hazardous: "black",
};

// Helper: colored icon with larger size
function makeColoredIcon(color) {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${color}.png`,
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.4/images/marker-shadow.png",
    iconSize: [30, 48], // Slightly larger for visibility
    iconAnchor: [15, 48],
    popupAnchor: [1, -40],
    shadowSize: [48, 48]
  });
}

// --- SUB-COMPONENT FOR AUTO-FITTING BOUNDS ---
function MapBounds({ points }) {
  const map = useMap();
  const hasFit = useRef(false);

  useEffect(() => {
    if (points && points.length > 0) {
      const bounds = L.latLngBounds(points.map(p => [p.latitude, p.longitude]));
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
      }
    } else {
      map.setView([18.5204, 73.8567], 12);
    }
  }, [points, map]);

  return null;
}

export default function ClusteredMap() {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ total: 0, visible: 0, skipped: 0 });

  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await fetchAllReports();
      const rawCount = data?.length || 0;

      // Filter reports that have valid coordinates
      const validReports = (data || []).map(r => {
        const lat = r.latitude !== undefined ? Number(r.latitude) : Number(r.lat);
        const lon = r.longitude !== undefined ? Number(r.longitude) : Number(r.lon);
        return { ...r, latitude: lat, longitude: lon };
      }).filter(
        (r) =>
          !isNaN(r.latitude) &&
          !isNaN(r.longitude) &&
          r.latitude !== 0 &&
          r.longitude !== 0
      );

      setPoints(validReports);
      setStats({
        total: rawCount,
        visible: validReports.length,
        skipped: rawCount - validReports.length
      });

    } catch (err) {
      console.error("ClusteredMap: Failed to load reports:", err);
      setError("Failed to load reports. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
    const unsubscribe = eventBus.subscribe("new-report", () => {
      loadReports();
    });
    return () => unsubscribe();
  }, [refreshTick]);

  const getWasteClass = (report) => {
    return report.prediction || report.waste_class || report.predicted_class || report.class || "Plastic";
  };

  const getColor = (report) => {
    const wasteClass = getWasteClass(report);
    const lowerClass = wasteClass.toLowerCase();
    const validColor = Object.keys(classColors).find(key => key.toLowerCase() === lowerClass);
    return classColors[validColor] || "blue";
  };

  // Helper for location text
  const getLocationText = (p) => {
    if (p.location_name && p.location_name !== "Unknown") return p.location_name;
    if (p.locationName && p.locationName !== "Unknown") return p.locationName;
    return `${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}`;
  };

  if (loading && points.length === 0) {
    return (
      <div className="w-full h-full p-6 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full p-6 text-white">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 mb-4">
          <p className="text-red-400">{error}</p>
          <button onClick={loadReports} className="mt-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-6 text-white">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Clustered Map</h1>
        <div className="bg-gray-800 text-xs px-3 py-1 rounded border border-gray-700">
          Showing {stats.visible} of {stats.total} reports ({stats.skipped} hidden w/o location)
        </div>
      </div>

      {points.length === 0 && !loading && (
        <div className="bg-gray-800 rounded-lg p-4 mb-4 text-center text-gray-400">
          No reports with valid coordinates available. Showing default view (Pune).
        </div>
      )}

      <MapContainer
        center={[18.5204, 73.8567]}
        zoom={12}
        style={{ height: "80vh", width: "100%", borderRadius: "12px" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />

        <MapBounds points={points} />

        {/* Cluster Layer - Explicit Configuration */}
        <MarkerClusterGroup
          chunkedLoading={true}
          spiderfyOnMaxZoom={true}
          removeOutsideVisibleBounds={false}
          maxClusterRadius={40}
        >
          {points.map((p) => (
            <Marker
              key={p.id}
              position={[p.latitude, p.longitude]}
              icon={makeColoredIcon(getColor(p))}
            >
              <Popup className="custom-popup" minWidth={250}>
                <div className="text-gray-900 p-1">

                  {/* Image Preview */}
                  {p.boxed_image_path ? (
                    <div className="mb-2 w-full h-32 bg-gray-200 rounded overflow-hidden">
                      <b>Detected Image:</b> <br />
                      <img
                        src={getImageUrl(p.boxed_image_path)}
                        alt="Detection preview"
                        className="w-full h-full object-cover rounded border border-gray-400"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    </div>
                  ) : p.image_path ? (
                    <div className="mb-2 w-full h-32 bg-gray-200 rounded overflow-hidden">
                      <img
                        src={getImageUrl(p.image_path)}
                        alt="Report"
                        className="w-full h-full object-cover"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    </div>
                  ) : (
                    <div className="mb-2 w-full h-16 bg-gray-100 rounded flex items-center justify-center text-xs text-gray-400 border border-dashed border-gray-300">
                      No Image
                    </div>
                  )}

                  <div className="space-y-1">
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-sm uppercase text-gray-600">ID #{p.id}</span>
                      <span className="text-xs bg-gray-200 px-2 py-0.5 rounded-full text-gray-600 font-semibold">{getWasteClass(p)}</span>
                    </div>

                    <div className="text-sm">
                      <span className="font-semibold text-gray-700">Loc:</span> {getLocationText(p)}
                    </div>

                    <div className="text-xs text-gray-500">
                      {convertUTCtoIST(p.created_at || p.timestamp)}
                    </div>

                    {p.confidence && (
                      <div className="text-xs text-gray-500">
                        Confidence: <b>{(Number(p.confidence) * 100).toFixed(1)}%</b>
                      </div>
                    )}
                  </div>

                </div>
              </Popup>
            </Marker>
          ))}
        </MarkerClusterGroup>
      </MapContainer>
    </div>
  );
}
