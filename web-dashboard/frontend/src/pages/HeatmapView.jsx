import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import HeatmapLayer from "../components/HeatmapLayer";
import { fetchAllReports } from "../api/reportsApi";
import eventBus from "../data/eventBus";

import { useEffect, useState } from "react";
import { useRefresh } from "../context/RefreshContext.jsx";

export default function HeatmapView() {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setError(null);
      const data = await fetchAllReports();
      // Filter reports that have valid coordinates and format for heatmap
      const validReports = (data || [])
        .filter(
          (r) =>
            r.latitude != null &&
            r.longitude != null &&
            !isNaN(parseFloat(r.latitude)) &&
            !isNaN(parseFloat(r.longitude))
        )
        .map((r) => ({
          latitude: parseFloat(r.latitude),
          longitude: parseFloat(r.longitude),
          confidence: r.confidence || 0.8,
        }));
      setPoints(validReports);
    } catch (err) {
      console.error("Failed to load reports:", err);
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

    return () => {
      unsubscribe();
    };
  }, [refreshTick]);

  if (loading) {
    return (
      <div className="w-full h-full p-6 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading heatmap...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full p-6 text-white">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 mb-4">
          <p className="text-red-400">{error}</p>
          <button
            onClick={loadReports}
            className="mt-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-6 text-white">
      <h1 className="text-2xl font-bold mb-4">Heatmap View</h1>
      {points.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-4 mb-4 text-center text-gray-400">
          No reports with valid coordinates available
        </div>
      )}

      <MapContainer
        center={[18.5204, 73.8567]}
        zoom={12.5}
        style={{ height: "80vh", width: "100%", borderRadius: "12px" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />

        {/* Heatmap Component */}
        <HeatmapLayer points={points} />
      </MapContainer>
    </div>
  );
}
