/* Civic status pills. Real workflow statuses (pending cleanup / cleaned)
   plus legacy values, mapped to display labels only. */
const styles = {
  pending: { bg: "#FDF3E0", tx: "#8A5A00", bd: "#EDD3A1", dot: "#F2B84B", label: "Pending cleanup" },
  assigned: { bg: "#EAF1F8", tx: "#2B5F8A", bd: "#C3D6E8", dot: "#2F7FD1", label: "Assigned" },
  "in progress": { bg: "#E6F4F1", tx: "#1F6E66", bd: "#BFE0D8", dot: "#3AA8A0", label: "In progress" },
  inprogress: { bg: "#E6F4F1", tx: "#1F6E66", bd: "#BFE0D8", dot: "#3AA8A0", label: "In progress" },
  verified: { bg: "#EFECFA", tx: "#4B3A86", bd: "#CFC4EC", dot: "#6F5CC4", label: "Verified" },
  cleaned: { bg: "#E7EFE7", tx: "#123D32", bd: "#BFD4C0", dot: "#123D32", label: "Cleaned" },
};

export default function StatusBadge({ status, size = "md" }) {
  const key = String(status || "pending").toLowerCase().trim();
  const s = styles[key] || { bg: "#EFF0EA", tx: "#45564F", bd: "#D5D9CF", dot: "#819087", label: status || "Unknown" };
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-semibold ${pad}`}
      style={{ background: s.bg, color: s.tx, borderColor: s.bd }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.dot }} />
      {s.label}
    </span>
  );
}
