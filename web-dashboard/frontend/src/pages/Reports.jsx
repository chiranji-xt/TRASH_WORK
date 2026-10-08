import { useEffect, useState } from "react";
import { fetchAllReports, fetchReportsByStatus, fetchReportById, getImageUrl } from "../api/reportsApi";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST } from "../utils/timezone";
import ReportModal from "../components/ReportModal";
import UpdateStatusButton from "../components/UpdateStatusButton";

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Filter state
  const [currentFilter, setCurrentFilter] = useState("all");

  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setLoading(true); // Show loading state when switching filters
      setError(null);

      let data;
      if (currentFilter === "all") {
        data = await fetchAllReports();
      } else {
        // Capitalize for API: "pending" -> "Pending"
        // Actually api might handle case, but let's be safe if backend expects Title Case
        const statusParam = currentFilter.charAt(0).toUpperCase() + currentFilter.slice(1);
        data = await fetchReportsByStatus(statusParam);
      }

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
  }, [refreshTick, currentFilter]); // Reload when filter changes

  const handleUpdateStatus = (id, newStatus) => {
    // Optimistically update local state
    setReports(prev => prev.map(r =>
      r.id === id ? { ...r, status: newStatus } : r
    ));
    eventBus.publish("report-updated", { id, status: newStatus });
  };

  const handleViewReport = async (report) => {
    setLoadingDetail(true);
    setShowModal(true);
    setSelectedReport(report);

    try {
      const freshReport = await fetchReportById(report.id);
      setSelectedReport(freshReport);
    } catch (err) {
      console.error("Failed to load report details:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Helper to safely get location string
  const getLocationString = (r) => {
    if (r.location_name) return r.location_name;
    if (r.locationName) return r.locationName;
    if (r.latitude && r.longitude) return `${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}`;
    if (r.lat && r.lon) return `${Number(r.lat).toFixed(4)}, ${Number(r.lon).toFixed(4)}`;
    return "N/A";
  };

  const filters = [
    { id: 'all', label: 'All Reports' },
    { id: 'pending', label: 'Pending' },
    { id: 'cleaned', label: 'Cleaned' },
  ];

  return (
    <div className="p-6 text-white w-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        <h1 className="text-3xl font-bold">Submitted Reports</h1>

        {/* Filter Buttons */}
        <div className="flex flex-wrap gap-2 bg-gray-800 p-1 rounded-lg border border-gray-700">
          {filters.map(f => (
            <button
              key={f.id}
              onClick={() => setCurrentFilter(f.id)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${currentFilter === f.id
                ? "bg-blue-600 text-white shadow"
                : "text-gray-400 hover:text-white hover:bg-gray-700"
                }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 mb-4 flex justify-between items-center">
          <p className="text-red-400">{error}</p>
          <button
            onClick={loadReports}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-sm rounded transition"
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="p-6 text-white w-full flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
            <p>Loading reports...</p>
          </div>
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-gray-800 rounded-lg p-12 text-center border border-gray-700">
          <p className="text-gray-400 text-lg">No reports found{currentFilter !== 'all' ? ` for "${currentFilter}"` : '.'}</p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg shadow-xl overflow-hidden border border-gray-700">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-900 text-gray-400 uppercase text-xs">
                <tr>
                  <th className="p-4 w-16">ID</th>
                  <th className="p-4 w-24">Image</th>
                  <th className="p-4">Location</th>
                  <th className="p-4">Class</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-center">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-700">
                {reports.map(r => (
                  <tr key={r.id} className="hover:bg-gray-750 transition duration-150">
                    <td className="p-4 font-mono text-gray-300">#{r.id}</td>

                    {/* Thumbnail Image */}
                    <td className="p-4">
                      <div className="w-12 h-12 bg-gray-700 rounded overflow-hidden border border-gray-600">
                        {r.boxed_image_path ? (
                          <img
                            src={getImageUrl(r.boxed_image_path)}
                            alt="Boxed"
                            className="w-full h-full object-cover"
                            loading="lazy"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        ) : r.image_path ? (
                          <img
                            src={getImageUrl(r.image_path)}
                            alt="Thumb"
                            className="w-full h-full object-cover"
                            loading="lazy"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xs text-gray-500">
                            N/A
                          </div>
                        )}
                      </div>
                    </td>

                    <td className="p-4 font-medium text-white max-w-xs truncate" title={getLocationString(r)}>
                      {getLocationString(r)}
                    </td>

                    <td className="p-4">
                      {r.waste_class || r.prediction || "Unknown"}
                    </td>

                    <td className="p-4 text-gray-300 whitespace-nowrap">
                      {convertUTCtoIST(r.created_at || r.timestamp)}
                    </td>

                    <td className="p-4">
                      <UpdateStatusButton
                        reportId={r.id}
                        currentStatus={r.status}
                        onUpdate={(newStatus) => handleUpdateStatus(r.id, newStatus)}
                      />
                    </td>

                    <td className="p-4 text-center">
                      <button
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded shadow transition"
                        onClick={() => handleViewReport(r)}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reusable Modal Component */}
      {showModal && (
        <ReportModal
          report={selectedReport}
          loading={loadingDetail}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
