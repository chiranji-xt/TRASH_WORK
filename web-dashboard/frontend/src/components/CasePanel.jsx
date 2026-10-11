import { useEffect, useState } from "react";
import { getImageUrl, fetchVerifications, priorityBand, PRIORITY_COLORS } from "../api/reportsApi";
import { convertUTCtoIST, ageOf } from "../utils/timezone";
import StatusBadge from "./StatusBadge";
import { Icon, paths, wasteMeta } from "./icons";

const COMPONENT_LABELS = {
  items: "Waste items",
  area: "Ground coverage",
  class: "Hazard mix",
  reporters: "Reporters",
  age: "Days open",
};

/**
 * Case detail panel: one real-world problem, its merged photos,
 * member reports and merge evidence. Rendered as a modal like ReportModal.
 */
export default function CasePanel({ caseData, onClose, loading }) {
  if (!caseData && !loading) return null;

  const reports = caseData?.reports || [];
  const log = caseData?.merge_log || [];
  const pending = String(caseData?.status || "").toLowerCase() !== "cleaned";
  const priority = caseData?.priority || null;
  const score = priority != null ? Number(priority.score) : null;
  const band = score != null ? priorityBand(score) : null;
  const bandColor = band ? PRIORITY_COLORS[band] : null;
  const [verifications, setVerifications] = useState([]);
  const [verifError, setVerifError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setVerifications([]);
    setVerifError(false);
    if (caseData?.id == null) return undefined;
    // Review queue needs the admin key; failures degrade to hidden section.
    fetchVerifications({ caseId: caseData.id })
      .then((rows) => { if (!cancelled) setVerifications(rows || []); })
      .catch(() => { if (!cancelled) setVerifError(true); });
    return () => { cancelled = true; };
  }, [caseData?.id]);

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-forest-deep/55 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Case details"
    >
      <div
        className="inv-scroll max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-line bg-white shadow-pop sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-line bg-[#FAF8F1] px-5 py-4 md:px-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="metalabel">Case dossier</p>
              <h2 className="font-display text-[22px] font-semibold leading-tight tracking-tight text-ink">
                Case <span className="tnum">#{caseData?.id ?? "…"}</span>
                <span className="tnum ml-2 rounded-full bg-forest-deep px-2.5 py-0.5 text-[13px] font-bold text-white">
                  {caseData?.report_count ?? 0} reports
                </span>
                {score != null && (
                  <span
                    className="tnum ml-2 rounded-full px-2.5 py-0.5 text-[13px] font-bold text-white"
                    style={{ background: bandColor }}
                    title={`Priority ${score} (${band})`}
                  >
                    {score} priority
                  </span>
                )}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {caseData?.status && <StatusBadge status={caseData.status} />}
              <button onClick={onClose} aria-label="Close case details" className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink-soft transition hover:border-forest/40">
                <Icon d={paths.x} size={16} />
              </button>
            </div>
          </div>
          {caseData && !loading && (
            <p className="mt-2 text-[13px] text-ink-soft">
              {caseData.report_count} citizen report{caseData.report_count === 1 ? "" : "s"} merged ·{" "}
              <span className={`tnum font-mono font-semibold ${pending ? "text-[#9A6700]" : "text-forest"}`}>
                {pending ? `latest waiting ${ageOf(caseData.last_reported_at)}` : "resolved"}
              </span>
            </p>
          )}
          {caseData?.recurrence_of != null && (
            <p className="mt-1.5 text-xs font-semibold text-[#9A6700]">
              Re-dumped near cleaned case #{caseData.recurrence_of}
            </p>
          )}
          {caseData?.suggested_duplicate_of != null && (
            <p className="mt-1.5 text-xs font-semibold text-ink-soft">
              Possibly the same pile as case #{caseData.suggested_duplicate_of} — awaiting review
            </p>
          )}
        </div>

        <div className="px-5 py-5 md:px-6">
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-12">
              <span className="brand-pulse flex h-9 w-9 items-center justify-center rounded-lg bg-forest text-[15px] font-bold text-civic-lime">◈</span>
              <p className="text-sm font-medium text-ink-soft">Loading dossier…</p>
            </div>
          ) : caseData ? (
            <div className="space-y-5">
              <div>
                <p className="metalabel mb-2">Merged photos · {reports.length}</p>
                {reports.length === 0 && (
                  <p className="text-sm text-ink-mute">No member reports.</p>
                )}
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                  {reports.map((r) => {
                    const src = getImageUrl(r.boxed_image_path || r.image_path);
                    const meta = wasteMeta(r.prediction || "Unclassified");
                    return (
                      <figure key={r.id} className="overflow-hidden rounded-lg border border-line bg-[#F4F2E9]">
                        {src ? (
                          <img src={src} alt={`Report #${r.id}`} className="aspect-[4/3] w-full object-cover" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
                        ) : (
                          <div className="flex aspect-[4/3] w-full items-center justify-center text-ink-mute">
                            <Icon d={meta.icon} size={22} />
                          </div>
                        )}
                        <figcaption className="flex items-center justify-between gap-1 px-2 py-1.5">
                          <span className="tnum font-mono text-[11px] font-bold text-ink">#{r.id}</span>
                          <span className="truncate text-[11px] font-semibold text-ink-soft">{r.prediction || "—"}</span>
                        </figcaption>
                      </figure>
                    );
                  })}
                </div>
              </div>

              {priority?.components && (
                <div>
                  <details className="group rounded-lg border border-line px-3.5 py-3">
                    <summary className="cursor-pointer list-none">
                      <span className="metalabel">Why this score</span>
                      <span className="mt-1 block text-[13px] font-semibold text-ink">
                        Priority {score} · {band} — expand for the breakdown
                      </span>
                    </summary>
                    <div className="mt-2.5 space-y-2">
                      {Object.entries(priority.components).map(([name, c]) => (
                        <div key={name}>
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="text-[13px] font-semibold text-ink">
                              {COMPONENT_LABELS[name] || name}
                              <span className="ml-1.5 font-mono text-[11px] font-normal text-ink-mute">
                                raw {String(c.raw)}
                              </span>
                            </span>
                            <span className="tnum font-mono text-[11px] text-ink-mute">
                              ×{c.weight} = {(c.contribution * 100).toFixed(1)}
                            </span>
                          </div>
                          <div className="mt-1 h-1 overflow-hidden rounded-full bg-[#EDEAE0]">
                            <div className="h-full rounded-full bg-forest" style={{ width: `${Math.round(c.normalized * 100)}%` }} />
                          </div>
                        </div>
                      ))}
                      <p className="pt-1 text-[11px] leading-relaxed text-ink-mute">
                        Formula v{priority.version} · ranks dispatch order, does not measure volume.
                      </p>
                    </div>
                  </details>
                </div>
              )}

              {verifError === false && verifications.length > 0 && (
                <div>
                  <p className="metalabel mb-2">Cleanup verification · before / after</p>
                  <div className="space-y-3">
                    {verifications.slice(0, 3).map((v) => (
                      <div key={v.id} className="rounded-lg border border-line px-3.5 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className="rounded-full px-2.5 py-0.5 text-[11px] font-bold text-white"
                            style={{ background: v.decision === "passed" ? "#2E7D4F" : v.decision === "failed_still_litter" ? "#E66B59" : "#F2B84B" }}
                          >
                            {String(v.decision || "").replace(/_/g, " ")}
                          </span>
                          <span className="tnum font-mono text-[11px] text-ink-mute">
                            attempt #{v.attempt_no} · {v.cleaner_id || "crew"}
                          </span>
                          {v.spot_checked && (
                            <span className="text-[11px] font-semibold text-[#9A6700]">spot check</span>
                          )}
                        </div>
                        {(v.photos || []).length > 0 && (
                          <div className="mt-2 grid grid-cols-3 gap-1.5">
                            {(v.photos || []).slice(0, 3).map((src, i) => {
                              const url = getImageUrl(src);
                              return url ? (
                                <img key={i} src={url} alt={`After photo ${i + 1}`} className="aspect-[4/3] w-full rounded-md border border-line object-cover" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
                              ) : null;
                            })}
                          </div>
                        )}
                        {Array.isArray(v.checks) && v.checks.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {v.checks.slice(0, 4).map((c, i) => (
                              <li key={i} className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-ink-soft">
                                <span className="font-semibold text-ink">Photo {(c.photo_index ?? 0) + 1}</span>
                                <CheckChip ok={c.location?.ok} label={`GPS${c.location?.distance_m != null ? ` ${c.location.distance_m}m` : ""}`} />
                                <CheckChip ok={c.time?.ok} label="time" />
                                <CheckChip ok={c.reuse?.ok} label="original" />
                                <CheckChip ok={(c.detection?.case_class_hits ?? -1) === 0} label={`litter ${(c.detection?.case_class_hits ?? 0)}`} />
                              </li>
                            ))}
                          </ul>
                        )}
                        {v.review_reason && (
                          <p className="mt-1.5 text-[11px] text-ink-mute">Review: {v.review_reason}{v.reviewed_by ? ` — ${v.reviewed_by}` : ""}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {log.length > 0 && (
                <div>
                  <p className="metalabel mb-2">Merge evidence</p>                  <ol className="space-y-1.5">
                    {log.slice(0, 8).map((e, i) => (
                      <li key={i} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 rounded-lg border border-line/80 px-3 py-2 text-xs">
                        <span className="font-bold text-ink">{e.decision.replace(/_/g, " ")}</span>
                        {e.report_id != null && <span className="tnum font-mono text-ink-mute">report #{e.report_id}</span>}
                        {e.score != null && <span className="tnum ml-auto font-mono font-bold text-ink-soft">score {(Number(e.score) * 100).toFixed(0)}%</span>}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <p className="text-xs text-ink-mute">
                Reported {convertUTCtoIST(caseData.first_reported_at)} → {convertUTCtoIST(caseData.last_reported_at)}
                {caseData.distinct_reporters ? ` · ${caseData.distinct_reporters} distinct reporter${caseData.distinct_reporters === 1 ? "" : "s"}` : ""}
              </p>
            </div>
          ) : (
            <p className="py-10 text-center text-ink-mute">Case details not found.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function CheckChip({ ok, label }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-semibold"
      style={{ background: ok ? "#E4F2E8" : "#FBE7E4", color: ok ? "#2E7D4F" : "#B3402E" }}
    >
      <span aria-hidden="true">{ok ? "✓" : "✗"}</span> {label}
    </span>
  );
}

