import StatusBadge from "./StatusBadge";
import { getImageUrl } from "../api/reportsApi";
import { convertUTCtoIST } from "../utils/timezone";

import SecureImage from "./SecureImage";

export default function ReportModal({ report, onClose, loading }) {
    if (!report && !loading) return null;

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 animate-fade-in">
            <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-700">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
                        <h2 className="text-2xl font-bold text-white">Report Details</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-white text-3xl leading-none transition"
                            aria-label="Close"
                        >
                            &times;
                        </button>
                    </div>

                    {loading ? (
                        <div className="text-center py-12">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto mb-4"></div>
                            <p className="text-gray-300">Loading details...</p>
                        </div>
                    ) : report ? (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                                {/* Image Section */}
                                <div className="flex flex-col">
                                    <p className="text-gray-400 text-sm mb-2 font-medium">Evidence</p>
                                    {report.boxed_image_path ? (
                                        <div className="relative group mb-4">
                                            <p className="text-xs text-gray-500 mb-1">Detected Object:</p>
                                            <SecureImage
                                                src={report.boxed_image_path}
                                                alt="Detected Processed Image"
                                                className="w-full h-auto rounded-lg border border-green-500/50 shadow-md object-cover"
                                                onError={(e) => (e.target.style.display = "none")}
                                            />
                                        </div>
                                    ) : null}

                                    {report.image_path ? (
                                        <div className="relative group">
                                            {report.boxed_image_path && <p className="text-xs text-gray-500 mb-1">Original Image:</p>}
                                            <SecureImage
                                                src={report.image_path}
                                                alt="Report Evidence"
                                                className="w-full h-auto rounded-lg border border-gray-600 shadow-md object-cover transition duration-300 group-hover:scale-[1.02]"
                                                onError={(e) => {
                                                    // This might not be needed as SecureImage handles internal errors, but kept for fallback
                                                    console.log("SecureImage failed to load");
                                                }}
                                            />
                                        </div>
                                    ) : (
                                        <div className="w-full h-48 bg-gray-700 rounded-lg flex items-center justify-center border border-gray-600 border-dashed">
                                            <p className="text-gray-400 italic">No image available</p>
                                        </div>
                                    )}
                                </div>

                                {/* Details Section */}
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Report ID</p>
                                        <p className="text-white text-xl font-mono">#{report.id}</p>
                                    </div>

                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Status</p>
                                        <div className="mt-1">
                                            <StatusBadge status={report.status} />
                                        </div>
                                    </div>

                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Classification</p>
                                        <p className="text-white font-semibold text-lg">
                                            {report.waste_class || report.prediction || "Unclassified"}
                                        </p>
                                    </div>

                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Confidence</p>
                                        <div className="w-full bg-gray-700 rounded-full h-2.5 mt-2">
                                            <div
                                                className="bg-blue-500 h-2.5 rounded-full"
                                                style={{ width: `${(report.confidence || 0) * 100}%` }}
                                            ></div>
                                        </div>
                                        <p className="text-right text-xs text-gray-400 mt-1">
                                            {report.confidence ? `${(report.confidence * 100).toFixed(1)}%` : "N/A"}
                                        </p>
                                    </div>

                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Location</p>
                                        <p className="text-white text-md break-words">
                                            {report.location_name || report.locationName || (
                                                (report.lat && report.lon)
                                                    ? `${report.lat.toFixed(6)}, ${report.lon.toFixed(6)}`
                                                    : "Unknown Location"
                                            )}
                                        </p>
                                    </div>

                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wide">Timestamp</p>
                                        <p className="text-white">
                                            {convertUTCtoIST(report.created_at || report.timestamp)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-10">
                            <p className="text-gray-400">Report details not found.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
