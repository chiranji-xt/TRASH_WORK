import { useState } from "react";
import { updateReportStatus } from "../api/reportsApi";
import { Icon, paths } from "./icons";

const pill = {
  pending: { bg: "#FDF3E0", tx: "#8A5A00", bd: "#EDD3A1" },
  cleaned: { bg: "#E7EFE7", tx: "#123D32", bd: "#BFD4C0" },
};

export default function UpdateStatusButton({ reportId, currentStatus, onUpdate }) {
  const [loading, setLoading] = useState(false);

  const handleChange = async (e) => {
    const newStatus = e.target.value;
    if (newStatus === currentStatus) return;

    setLoading(true);
    try {
      // Call API — endpoint, method and payload preserved
      await updateReportStatus(reportId, newStatus);
      if (onUpdate) onUpdate(newStatus);
    } catch (error) {
      console.error("Failed to update status", error);
      alert(`Failed to update status: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const key = String(currentStatus || "pending").toLowerCase();
  const c = pill[key] || { bg: "#EFF0EA", tx: "#45564F", bd: "#D5D9CF" };

  return (
    <span className="relative inline-flex items-center">
      <select
        value={currentStatus || "Pending"}
        onChange={handleChange}
        disabled={loading}
        aria-label={`Update status for report ${reportId}`}
        style={{ background: c.bg, color: c.tx, borderColor: c.bd }}
        className={`appearance-none rounded-md border py-1.5 pl-3 pr-8 text-xs font-bold outline-none transition focus:ring-2 focus:ring-forest/25 ${loading ? "cursor-wait opacity-60" : "cursor-pointer hover:brightness-[0.98]"}`}
      >
        {/* option values are the exact backend status strings — labels are display-only */}
        <option value="Pending">Pending cleanup</option>
        <option value="Cleaned">Cleaned</option>
      </select>
      <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 opacity-70">
        {loading ? (
          <span className="block h-3 w-3 animate-spin rounded-full border-b-2 border-current" />
        ) : (
          <Icon d={paths.chevron} size={13} />
        )}
      </span>
    </span>
  );
}
