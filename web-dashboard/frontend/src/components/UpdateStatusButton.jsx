import React, { useState } from 'react';
import { updateReportStatus } from '../api/reportsApi';

export default function UpdateStatusButton({ reportId, currentStatus, onUpdate }) {
    const [loading, setLoading] = useState(false);

    const handleChange = async (e) => {
        const newStatus = e.target.value;
        if (newStatus === currentStatus) return;

        setLoading(true);
        try {
            // Call API
            await updateReportStatus(reportId, newStatus);

            // Notify parent
            if (onUpdate) {
                onUpdate(newStatus);
            }
        } catch (error) {
            console.error("Failed to update status", error);
            alert(`Failed to update status: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const statusColors = {
        pending: "bg-red-900/40 text-red-500 border-red-800 focus:ring-red-500",
        verified: "bg-blue-900/40 text-blue-500 border-blue-800 focus:ring-blue-500",
        assigned: "bg-orange-900/40 text-orange-500 border-orange-800 focus:ring-orange-500",
        cleaned: "bg-green-900/40 text-green-500 border-green-800 focus:ring-green-500",
    };

    const normalizedStatus = (currentStatus || "pending").toLowerCase();
    const colorClass = statusColors[normalizedStatus] || "bg-gray-800 text-gray-400 border-gray-700";

    return (
        <div className="relative inline-block">
            <select
                value={currentStatus || "Pending"}
                onChange={handleChange}
                disabled={loading}
                className={`appearance-none px-3 py-1 pr-8 rounded-full text-xs font-semibold cursor-pointer border focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-gray-900 transition-all duration-200 ${colorClass} ${loading ? 'opacity-50 cursor-wait' : ''}`}
            >
                <option value="Pending">Pending</option>
                <option value="Cleaned">Cleaned</option>
            </select>

            {/* Chevron Icon */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                {loading ? (
                    <div className="animate-spin h-3 w-3 border-b-2 border-current rounded-full"></div>
                ) : (
                    <svg className="w-3 h-3 text-current opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                )}
            </div>
        </div>
    );
}
