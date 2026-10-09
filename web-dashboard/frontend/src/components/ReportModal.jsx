import { useEffect } from "react";
import StatusBadge from "./StatusBadge";
import { getImageUrl } from "../api/reportsApi";
import { convertUTCtoIST, ageOf } from "../utils/timezone";
import SecureImage from "./SecureImage";
import { Icon, paths, wasteMeta } from "./icons";

export default function ReportModal({ report, onClose, loading }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  if (!report && !loading) return null;

  const cls = report?.waste_class || report?.prediction || "Unclassified";
  const meta = wasteMeta(cls);
  const conf = report?.confidence != null ? Number(report.confidence) : null;
  const pending = String(report?.status || "").toLowerCase() === "pending";
  const loc =
    report?.location_name ||
    report?.locationName ||
    (report?.lat && report?.lon ? `${Number(report.lat).toFixed(6)}, ${Number(report.lon).toFixed(6)}` : null) ||
    (report?.latitude && report?.longitude ? `${Number(report.latitude).toFixed(6)}, ${Number(report.longitude).toFixed(6)}` : null) ||
    "Unknown zone";

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-forest-deep/55 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Report details"
    >
      <div
        className="inv-scroll max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-line bg-white shadow-pop sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Masthead band */}
        <div className="border-b border-line bg-[#FAF8F1] px-5 py-4 md:px-6">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-lg border" style={{ background: meta.bg, color: meta.tx, borderColor: meta.bd }}>
                <Icon d={meta.icon} size={21} />
              </span>
              <div>
                <p className="metalabel">Report dossier</p>
                <h2 className="font-display text-[22px] font-semibold leading-tight tracking-tight text-ink">
                  Report <span className="tnum">#{report?.id ?? "…"}</span>
                </h2>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {report?.status && <StatusBadge status={report.status} />}
              <button onClick={onClose} aria-label="Close report details" className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink-soft transition hover:border-forest/40">
                <Icon d={paths.x} size={16} />
              </button>
            </div>
          </div>
          {report && !loading && (
            <p className="mt-2 text-[13px] text-ink-soft">
              {cls} · {loc} ·{" "}
              <span className={`tnum font-mono font-semibold ${pending ? "text-[#9A6700]" : "text-forest"}`}>
                {pending ? `waiting ${ageOf(report.created_at || report.timestamp)}` : "resolved"}
              </span>
            </p>
          )}
        </div>

        <div className="px-5 py-5 md:px-6">
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-12">
              <span className="brand-pulse flex h-9 w-9 items-center justify-center rounded-lg bg-forest text-[15px] font-bold text-civic-lime">◈</span>
              <p className="text-sm font-medium text-ink-soft">Loading dossier…</p>
            </div>
          ) : report ? (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <p className="metalabel mb-2">Evidence</p>
                {report.boxed_image_path && (
                  <figure className="mb-3">
                    <SecureImage src={report.boxed_image_path} alt="Detected processed image" className="aspect-[4/3] w-full rounded-lg border border-line object-cover" onError={(e) => (e.target.style.display = "none")} />
                    <figcaption className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-ink-mute">
                      <span className="h-1.5 w-1.5 rounded-full bg-forest" /> AI detection overlay
                    </figcaption>
                  </figure>
                )}
                {report.image_path ? (
                  <figure>
                    <SecureImage src={report.image_path} alt="Report evidence" className="aspect-[4/3] w-full rounded-lg border border-line object-cover" onError={() => console.log("SecureImage failed to load")} />
                    {report.boxed_image_path && <figcaption className="mt-1.5 text-xs text-ink-mute">Original capture</figcaption>}
                  </figure>
                ) : !report.boxed_image_path ? (
                  <div className="flex h-48 w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-[#FAF8F1] text-ink-mute">
                    <Icon d={meta.icon} size={26} />
                    <p className="text-sm">No photograph attached</p>
                  </div>
                ) : null}
              </div>

              <dl className="space-y-2.5">
                <div className="rounded-lg border border-line px-3.5 py-3">
                  <dt className="metalabel">Waste category</dt>
                  <dd className="mt-1 text-[17px] font-bold text-ink">{cls}</dd>
                  <dd className="mt-2.5">
                    <div className="h-1.5 overflow-hidden rounded-full bg-[#EDEAE0]">
                      <div className="h-full rounded-full bg-forest" style={{ width: `${Math.round((conf || 0) * 100)}%` }} />
                    </div>
                    <p className="tnum mt-1 text-right font-mono text-xs text-ink-mute">
                      {conf != null ? `${(conf * 100).toFixed(1)}% match` : "confidence unavailable"}
                    </p>
                  </dd>
                </div>
                <Field label="Municipal zone" value={loc} />
                <Field label="Reported (IST)" value={convertUTCtoIST(report.created_at || report.timestamp)} mono />
                {(report.latitude ?? report.lat) != null && (
                  <Field label="Coordinates" value={`${Number(report.latitude ?? report.lat).toFixed(6)}, ${Number(report.longitude ?? report.lon).toFixed(6)}`} mono />
                )}
              </dl>
            </div>
          ) : (
            <p className="py-10 text-center text-ink-mute">Report details not found.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, mono }) {
  return (
    <div className="rounded-lg border border-line/80 px-3.5 py-2.5">
      <dt className="metalabel">{label}</dt>
      <dd className={`mt-0.5 break-words text-[13.5px] font-semibold text-ink ${mono ? "tnum font-mono text-[13px]" : ""}`}>{value}</dd>
    </div>
  );
}
