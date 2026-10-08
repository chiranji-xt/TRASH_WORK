import { useEffect, useState } from "react";
import { fetchAllReports, getImageUrl } from "../api/reportsApi";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST, getISTDateKey } from "../utils/timezone";
import StatusBadge from "../components/StatusBadge";

export default function DashboardHome() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setError(null);
      const data = await fetchAllReports();
      setReports(data || []);
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
    return () => unsubscribe();
  }, [refreshTick]);

  // Helper to safely get location string
  const getLocationString = (r) => {
    if (r.location_name && r.location_name !== "Unknown") return r.location_name;
    if (r.locationName && r.locationName !== "Unknown") return r.locationName;
    if (r.latitude && r.longitude) return `${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}`;
    if (r.lat && r.lon) return `${Number(r.lat).toFixed(4)}, ${Number(r.lon).toFixed(4)}`;
    return "N/A";
  };

  const total = reports.length;
  const pending = reports.filter(r => r.status === "pending" || r.status === "Pending").length;
  // We removed "Verified" workflow, so let's track Cleaned specifically
  const cleaned = reports.filter(r => r.status === "cleaned" || r.status === "Cleaned").length;

  // Calculate cleaned today
  const today = new Date().toISOString().slice(0, 10);
  const cleanedToday = reports.filter(r => {
    const reportDateKey = getISTDateKey(r.created_at || r.timestamp);
    return (r.status === "cleaned" || r.status === "Cleaned") && reportDateKey === today;
  }).length;

  const recent = [...reports]
    .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))
    .slice(0, 5);

  if (loading) {
    return (
      <div className="w-full text-white flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading reports...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full text-white">
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
    <div className="w-full text-white">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard title="Total Reports" value={total} />
        <StatCard title="Pending" value={pending} />
        <StatCard title="Cleaned Today" value={cleanedToday} />
      </div>

      {/* Recent Reports */}
      <h2 className="text-xl font-semibold mb-3">Last 5 Reports</h2>
      {recent.length === 0 ? (
        <div className="bg-gray-800 rounded-lg p-8 text-center text-gray-400">
          No reports available
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="p-3 text-left w-16">ID</th>
                <th className="p-3 text-left w-20">Image</th>
                <th className="p-3 text-left">Location</th>
                <th className="p-3 text-left">Class</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {recent.map(r => (
                <tr key={r.id} className="border-b border-gray-700 hover:bg-gray-750">
                  <td className="p-3 font-mono text-gray-400">#{r.id}</td>

                  {/* Image Column */}
                  <td className="p-3">
                    <div className="w-10 h-10 bg-gray-700 rounded overflow-hidden border border-gray-600">
                      {r.boxed_image_path ? (
                        <img
                          src={getImageUrl(r.boxed_image_path)}
                          alt="Boxed"
                          className="w-full h-full object-cover"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      ) : r.image_path ? (
                        <img
                          src={getImageUrl(r.image_path)}
                          alt="Thumb"
                          className="w-full h-full object-cover"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-[10px] text-gray-500">
                          N/A
                        </div>
                      )}
                    </div>
                  </td>

                  <td className="p-3">{getLocationString(r)}</td>
                  <td className="p-3">{r.waste_class || r.prediction || r.predicted_class || r.class || "N/A"}</td>
                  <td className="p-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="p-3 text-sm text-gray-400">
                    {convertUTCtoIST(r.created_at || r.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="p-4 bg-gray-800 shadow rounded-lg text-center border border-gray-700">
      <h3 className="text-sm font-medium text-gray-400 mb-2 whitespace-nowrap">{title}</h3>
      <p className="text-3xl font-bold text-white">{value}</p>
    </div>
  );
}
