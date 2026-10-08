import React from 'react';

const statusColors = {
    pending: "bg-red-900/40 text-red-500 border-red-800",
    verified: "bg-blue-900/40 text-blue-500 border-blue-800",
    assigned: "bg-orange-900/40 text-orange-500 border-orange-800",
    cleaned: "bg-green-900/40 text-green-500 border-green-800",
    default: "bg-gray-800 text-gray-400 border-gray-700"
};

const labels = {
    pending: "Pending",
    verified: "Verified",
    assigned: "Assigned",
    cleaned: "Cleaned"
};

const icons = {
    pending: "⏳",
    verified: "🔍",
    assigned: "👷",
    cleaned: "✓"
};

export default function StatusBadge({ status }) {
    const normalizedStatus = (status || "pending").toLowerCase();
    const colorClass = statusColors[normalizedStatus] || statusColors.default;
    const label = labels[normalizedStatus] || status;
    const icon = icons[normalizedStatus] || "•";

    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${colorClass}`}>
            <span>{icon}</span>
            {label}
        </span>
    );
}
