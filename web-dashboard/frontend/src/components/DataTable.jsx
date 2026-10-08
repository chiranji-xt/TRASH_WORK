const rows = [
  {
    id: 101,
    location: "Area D",
    className: "Metal",
    status: "Pending",
    timestamp: "2025-11-30",
  },
  {
    id: 102,
    location: "Area B",
    className: "Plastic",
    status: "Assigned",
    timestamp: "2025-11-28",
  },
  {
    id: 103,
    location: "Area C",
    className: "Organic",
    status: "Verified",
    timestamp: "2025-11-27",
  },
];

const statusStyles = {
  Pending: "bg-yellow-100 text-yellow-800",
  Assigned: "bg-blue-100 text-blue-800",
  Verified: "bg-emerald-100 text-emerald-800",
};

export default function DataTable() {
  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <h2 className="text-sm font-semibold">Recent reports</h2>
        <button className="text-xs text-blue-600 hover:underline">
          View all
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-y border-black/5 bg-white/60">
              <th className="px-5 py-2 font-medium text-gray-500">ID</th>
              <th className="px-5 py-2 font-medium text-gray-500">Location</th>
              <th className="px-5 py-2 font-medium text-gray-500">Class</th>
              <th className="px-5 py-2 font-medium text-gray-500">Status</th>
              <th className="px-5 py-2 font-medium text-gray-500">
                Timestamp
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr
                key={r.id}
                className={
                  idx % 2 === 0
                    ? "bg-white/70"
                    : "bg-white/40 hover:bg-white/80"
                }
              >
                <td className="px-5 py-2 text-xs">{r.id}</td>
                <td className="px-5 py-2 text-xs">{r.location}</td>
                <td className="px-5 py-2 text-xs">{r.className}</td>
                <td className="px-5 py-2 text-xs">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium ${
                      statusStyles[r.status] || "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="px-5 py-2 text-xs text-gray-500">
                  {r.timestamp}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
