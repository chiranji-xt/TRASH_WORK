import StatusBadge from "./StatusBadge";

const rows = [
  { id: 101, location: "Area D", className: "Metal", status: "Pending", timestamp: "2025-11-30" },
  { id: 102, location: "Area B", className: "Plastic", status: "Assigned", timestamp: "2025-11-28" },
  { id: 103, location: "Area C", className: "Organic", status: "Verified", timestamp: "2025-11-27" },
];

export default function DataTable() {
  return (
    <div className="inv-card overflow-hidden">
      <div className="flex items-center justify-between px-5 pb-3 pt-4">
        <h2 className="font-display text-[17px] font-semibold text-ink">Recent reports</h2>
        <button className="text-[13px] font-bold text-forest hover:underline">View all →</button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-y border-line bg-[#FAF8F1]">
              <th className="inv-table-head px-5 py-2.5">ID</th>
              <th className="inv-table-head px-5 py-2.5">Location</th>
              <th className="inv-table-head px-5 py-2.5">Class</th>
              <th className="inv-table-head px-5 py-2.5">Status</th>
              <th className="inv-table-head px-5 py-2.5">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/80">
            {rows.map((r) => (
              <tr key={r.id} className="inv-row">
                <td className="tnum px-5 py-2.5 font-mono text-xs font-bold text-ink">#{r.id}</td>
                <td className="px-5 py-2.5 text-[13px] text-ink-soft">{r.location}</td>
                <td className="px-5 py-2.5 text-[13px] text-ink-soft">{r.className}</td>
                <td className="px-5 py-2.5"><StatusBadge status={r.status} size="sm" /></td>
                <td className="tnum px-5 py-2.5 text-xs text-ink-mute">{r.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
