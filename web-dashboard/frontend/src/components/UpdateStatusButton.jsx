import { useState } from "react";
import { updateReportStatus } from "../api/reportsApi";
import { Icon, paths } from "./icons";

const pill = {
  pending: { bg: "#FDF3E0", tx: "#8A5A00", bd: "#EDD3A1" },
  cleaned: { bg: "#E7EFE7", tx: "#123D32", bd: "#BFD4C0" },
};

export default function UpdateStatusButton({ reportId, currentStatus, onUpdate }) {
  const [loading, setLoading] = useState(false);
  const [askReason, setAskReason] = useState(false);
  const [pendingStatus, setPendingStatus] = useState(null);
  const [reason, setReason] = useState("");

  const doUpdate = async (newStatus, why) => {
    setLoading(true);
    try {
      // Call API — endpoint, method and payload preserved (+ reason for cleaned)
      await updateReportStatus(reportId, newStatus, why);
      if (onUpdate) onUpdate(newStatus);
    } catch (error) {
      console.error("Failed to update status", error);
      alert(`Failed to update status: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = async (e) => {
    const newStatus = e.target.value;
    if (newStatus === currentStatus) return;
    // Marking cleaned is an audited admin override — the backend requires
    // a reason. Verification (case dossier) remains the preferred path.
    if (String(newStatus).toLowerCase() === "cleaned") {
      setPendingStatus(newStatus);
      setReason("");
      setAskReason(true);
      return;
    }
    await doUpdate(newStatus, null);
  };

  const confirmCleaned = async () => {
    if (reason.trim() === "") return;
    setAskReason(false);
    await doUpdate(pendingStatus, reason.trim());
    setPendingStatus(null);
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

      {askReason && (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-forest-deep/55 p-4 backdrop-blur-sm"
          onClick={() => setAskReason(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Confirm cleaned status"
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-line bg-white p-5 shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="metalabel">Admin override</p>
            <h3 className="font-display mt-1 text-[18px] font-semibold text-ink">
              Mark report #{reportId} cleaned?
            </h3>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">
              Direct edits bypass verification and are audit-logged. Prefer closing
              through the case dossier when possible.
            </p>
            <label className="mt-3 block text-xs font-bold text-ink-soft" htmlFor={`clean-reason-${reportId}`}>
              Reason (required)
            </label>
            <textarea
              id={`clean-reason-${reportId}`}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              autoFocus
              placeholder="e.g. Crew confirmed cleared on revisit"
              className="mt-1.5 w-full rounded-lg border border-line bg-white px-3 py-2 text-[13px] text-ink outline-none focus:border-forest/50"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setAskReason(false)}
                className="rounded-lg border border-line px-3.5 py-2 text-[13px] font-bold text-ink-soft hover:bg-[#FAF8F1]"
              >
                Cancel
              </button>
              <button
                onClick={confirmCleaned}
                disabled={reason.trim() === ""}
                className="rounded-lg bg-forest-deep px-3.5 py-2 text-[13px] font-bold text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Confirm cleaned
              </button>
            </div>
          </div>
        </div>
      )}
    </span>
  );
}
