import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAllReports, fetchReportById, getImageUrl } from "../api/reportsApi";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST, getISTDateKey, ageOf } from "../utils/timezone";
import StatusBadge from "../components/StatusBadge";
import ReportModal from "../components/ReportModal";
import { Card, CardHeader, AreaChart, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { Icon, paths, wasteMeta } from "../components/icons";

function classKey(r) {
  return String(r.waste_class || r.prediction || r.predicted_class || r.class || "Unknown");
}

function locOf(r) {
  if (r.location_name && r.location_name !== "Unknown") return r.location_name;
  if (r.locationName && r.locationName !== "Unknown") return r.locationName;
  if (r.latitude && r.longitude) return `${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}`;
  if (r.lat && r.lon) return `${Number(r.lat).toFixed(4)}, ${Number(r.lon).toFixed(4)}`;
  return "Unknown zone";
}

export default function DashboardHome() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setError(null);
      const data = await fetchAllReports();
      setReports(data || []);
    } catch (err) {
      console.error("Failed to load reports:", err);
      setError("Failed to load reports. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
    const unsubscribe = eventBus.subscribe("new-report", () => loadReports());
    return () => unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTick]);

  const openReport = async (report) => {
    setLoadingDetail(true);
    setShowModal(true);
    setSelected(report);
    try {
      const fresh = await fetchReportById(report.id);
      setSelected(fresh);
    } catch (err) {
      console.error("Failed to load report details:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const s = useMemo(() => {
    const isPending = (r) => String(r.status || "").toLowerCase() === "pending";
    const isCleaned = (r) => String(r.status || "").toLowerCase() === "cleaned";
    const total = reports.length;
    const pending = reports.filter(isPending).length;
    const cleaned = reports.filter(isCleaned).length;
    const rate = total ? Math.round((cleaned / total) * 100) : 0;

    const days = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      days.push(d.toISOString().slice(0, 10));
    }
    const perDay = days.map((day) => reports.filter((r) => getISTDateKey(r.created_at || r.timestamp) === day).length);
    const dayLabels = days.map((d) => new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { weekday: "narrow" }));
    const todayCount = perDay[6] || 0;
    const peak = Math.max(...perDay, 0);
    const peakIdx = perDay.indexOf(peak);

    const byClass = {};
    reports.forEach((r) => {
      const k = classKey(r);
      byClass[k] = (byClass[k] || 0) + 1;
    });
    const mix = Object.entries(byClass)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, value]) => ({ name, value, share: total ? Math.round((value / total) * 100) : 0, color: wasteMeta(name).dot }));

    const zoneCount = {};
    reports.filter(isPending).forEach((r) => {
      const z = locOf(r);
      zoneCount[z] = (zoneCount[z] || 0) + 1;
    });
    const hotspots = Object.entries(zoneCount).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const maxHot = hotspots.length ? hotspots[0][1] : 1;

    const ledger = [...reports]
      .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))
      .slice(0, 6);

    const crew = [...reports]
      .filter(isCleaned)
      .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))
      .slice(0, 4);

    return { total, pending, cleaned, rate, perDay, dayLabels, todayCount, peak, peakIdx, days, mix, hotspots, maxHot, ledger, crew };
  }, [reports]);

  if (loading) return <LoadingState label="Loading waste reports…" />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  const todayLong = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="w-full">
      <PageHeader
        eyebrow={`Municipal operations · ${todayLong}`}
        title="Operations overview"
        description={`${s.total} citizen reports on record · ${s.pending} awaiting cleanup · ${s.cleaned} resolved across municipal zones.`}
        actions={
          <Link to="/locations" className="inv-btn-ghost">
            <Icon d={paths.pin} size={15} /> Zone map
          </Link>
        }
      />

      {/* Ledger strip — one ruled panel, not four cards */}
      <div className="inv-card rise divide-y divide-line sm:divide-y-0 sm:grid sm:grid-cols-2 xl:grid-cols-4 sm:divide-x sm:divide-line">
        <LedgerCell label="Pending cleanup" value={s.pending} tone="text-[#9A6700]" caption={s.pending ? "Crews needed on the ground" : "Nothing waiting — queue clear"} />
        <LedgerCell label="Resolved to date" value={s.cleaned} tone="text-forest" caption={s.total ? `${s.rate}% of all reports` : "No reports on record yet"} />
        <LedgerCell label="Cleanup rate" value={`${s.rate}%`} tone="text-ink" caption="Resolved share of total volume" bar={s.rate} />
        <LedgerCell label="Reported today" value={s.todayCount} tone="text-ink" caption="New detections · IST" live={s.todayCount > 0} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_330px]">
        {/* Dispatch ledger */}
        <Card className="rise-1 overflow-hidden">
          <CardHeader
            eyebrow="Dispatch ledger"
            title="Latest reports"
            subtitle="Newest first · open a row for the full dossier"
            right={<Link to="/reports" className="inline-flex items-center gap-1 text-[13px] font-bold text-forest hover:underline">All reports <Icon d={paths.arrowUR} size={14} /></Link>}
          />
          {s.ledger.length === 0 ? (
            <div className="px-5 pb-5"><EmptyState title="No waste reports found" hint="There are currently no reports in the live feed." /></div>
          ) : (
            <ol className="divide-y divide-line/80 border-t border-line/80">
              {s.ledger.map((r) => {
                const pending = String(r.status || "").toLowerCase() === "pending";
                const cls = classKey(r);
                const meta = wasteMeta(cls);
                const conf = r.confidence != null ? Math.round(Number(r.confidence) * 100) : null;
                return (
                  <li key={r.id}>
                    <button onClick={() => openReport(r)} className="inv-row flex w-full items-center gap-3 px-4 py-3 text-left md:gap-4 md:px-5">
                      <span className={`hidden w-1 self-stretch rounded-full sm:block ${pending ? "bg-civic-amber" : "bg-forest/25"}`} aria-hidden="true" />
                      <Thumb id={r.id} boxed={r.boxed_image_path} raw={r.image_path} icon={meta.icon} />
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-baseline gap-x-2">
                          <span className="tnum font-display text-[17px] font-semibold text-ink">#{r.id}</span>
                          <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink-soft" title={locOf(r)}>{locOf(r)}</span>
                        </span>
                        <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-mute">
                          <span className="inline-flex items-center gap-1 font-semibold" style={{ color: meta.tx }}>
                            <Icon d={meta.icon} size={12} /> {cls}
                          </span>
                          {conf != null && <span className="tnum font-mono">{conf}% match</span>}
                          <span className="tnum">{convertUTCtoIST(r.created_at || r.timestamp)}</span>
                        </span>
                      </span>
                      <span className="hidden shrink-0 text-right md:block">
                        <span className={`tnum block font-mono text-[11px] font-semibold ${pending ? "text-[#9A6700]" : "text-ink-mute"}`}>
                          {pending ? `waiting ${ageOf(r.created_at || r.timestamp)}` : "resolved"}
                        </span>
                        <span className="mt-1 block"><StatusBadge status={r.status} size="sm" /></span>
                      </span>
                      <span className="shrink-0 text-ink-mute"><Icon d={paths.chevronR} size={16} /></span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </Card>

        {/* Right rail — varied weights */}
        <div className="flex flex-col gap-4">
          <section className="rise-2 relative overflow-hidden rounded-xl bg-forest-deep text-white shadow-card">
            <div className="map-grid pointer-events-none absolute inset-0 opacity-60" />
            <div className="relative p-5">
              <p className="metalabel !text-civic-lime/80">Needs crews</p>
              <h2 className="font-display mt-1 text-[19px] font-semibold tracking-tight">Critical waste hotspots</h2>
              {s.hotspots.length === 0 ? (
                <p className="mt-3 rounded-lg bg-white/[0.07] px-3.5 py-3 text-[13px] text-white/75">All zones clear — nothing awaiting dispatch.</p>
              ) : (
                <ol className="mt-3 space-y-2.5">
                  {s.hotspots.map(([zone, count], idx) => (
                    <li key={zone}>
                      <div className="flex items-baseline gap-2">
                        <span className="font-display text-[15px] font-semibold text-civic-lime/90">0{idx + 1}</span>
                        <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-white" title={zone}>{zone}</span>
                        <span className="tnum font-mono text-xs font-bold text-civic-amber">{count} open</span>
                      </div>
                      <div className="ml-7 mt-1 h-1 overflow-hidden rounded-full bg-white/15">
                        <div className="h-full rounded-full bg-civic-amber" style={{ width: `${Math.max(10, (count / s.maxHot) * 100)}%` }} />
                      </div>
                    </li>
                  ))}
                </ol>
              )}
              <Link to="/heatmap" className="mt-4 inline-flex items-center gap-1 text-[13px] font-bold text-civic-lime hover:underline">
                Open density view <Icon d={paths.arrowUR} size={14} />
              </Link>
            </div>
          </section>

          <Card className="rise-3">
            <CardHeader eyebrow="Composition" title="Waste mix" subtitle="Share of total volume" />
            <ol className="space-y-2.5 px-5 pb-5">
              {s.mix.length === 0 && <li className="text-[13px] text-ink-mute">No data yet.</li>}
              {s.mix.map((g, i) => (
                <li key={g.name} className="flex items-center gap-2.5">
                  <span className="tnum w-5 font-mono text-[11px] text-ink-mute">0{i + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-[13px] font-semibold text-ink">{g.name}</span>
                      <span className="tnum font-mono text-xs font-bold text-ink">{g.share}%</span>
                    </span>
                    <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-[#EFECE1]">
                      <span className="block h-full rounded-full" style={{ width: `${Math.max(4, g.share)}%`, background: g.color }} />
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </Card>

          <Card className="rise-3">
            <CardHeader eyebrow="Field log" title="Recent cleanups" />
            <ol className="space-y-1 px-3 pb-4">
              {s.crew.length === 0 && <li className="px-2 pb-2 text-[13px] text-ink-mute">No cleanups logged yet.</li>}
              {s.crew.map((r) => (
                <li key={r.id} className="flex items-center gap-2.5 rounded-lg px-2 py-1.5">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-forest" />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-ink-soft">
                    <span className="tnum font-bold text-ink">#{r.id}</span> · {classKey(r)} — {locOf(r)}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>

      {/* Rhythm panel */}
      <Card className="rise-2 mt-4">
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_240px]">
          <div>
            <CardHeader eyebrow="Throughput" title="Collection rhythm" subtitle="Reports per day · last 7 days (IST)" />
            <div className="px-4 pb-4"><AreaChart values={s.perDay} labels={s.dayLabels} /></div>
          </div>
          <aside className="border-t border-line px-5 py-5 lg:border-l lg:border-t-0">
            <p className="metalabel">Reading the city</p>
            <dl className="mt-3 space-y-3 text-[13px]">
              <div className="flex items-baseline justify-between gap-2 border-b border-line/70 pb-2.5">
                <dt className="text-ink-mute">Peak day</dt>
                <dd className="tnum font-mono font-bold text-ink">{s.peak} reports · {s.dayLabels[s.peakIdx]}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-2 border-b border-line/70 pb-2.5">
                <dt className="text-ink-mute">Reported today</dt>
                <dd className="tnum font-mono font-bold text-ink">{s.todayCount}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-2">
                <dt className="text-ink-mute">Cleanup rate</dt>
                <dd className="tnum font-mono font-bold text-forest">{s.rate}%</dd>
              </div>
            </dl>
            <Link to="/reports" className="inv-btn-ghost mt-4 w-full !py-2 text-[13px]">
              Coordinate dispatch <Icon d={paths.arrowUR} size={14} />
            </Link>
          </aside>
        </div>
      </Card>

      {showModal && <ReportModal report={selected} loading={loadingDetail} onClose={() => setShowModal(false)} />}
    </div>
  );
}

function LedgerCell({ label, value, tone, caption, bar, live }) {
  return (
    <div className="px-5 py-4 md:px-6">
      <p className="metalabel flex items-center gap-1.5">
        {live && <span className="h-1.5 w-1.5 rounded-full bg-forest" />}
        {label}
      </p>
      <p className={`tnum font-display mt-1 text-[34px] font-semibold leading-none tracking-tight ${tone}`}>{value}</p>
      {bar != null && (
        <div className="mt-2 h-1 w-28 overflow-hidden rounded-full bg-[#EDEAE0]">
          <div className="h-full rounded-full bg-forest" style={{ width: `${Math.min(100, bar)}%` }} />
        </div>
      )}
      <p className="mt-1.5 text-xs text-ink-mute">{caption}</p>
    </div>
  );
}

function Thumb({ boxed, raw, icon }) {
  const src = boxed ? getImageUrl(boxed) : raw ? getImageUrl(raw) : null;
  if (!src)
    return (
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-line bg-[#F4F2E9] text-ink-mute">
        <Icon d={icon || paths.box} size={18} />
      </span>
    );
  return (
    <span className="block h-11 w-11 shrink-0 overflow-hidden rounded-lg border border-line bg-[#F4F2E9]">
      <img src={src} alt="Report evidence" loading="lazy" className="h-full w-full object-cover" onError={(e) => { e.target.style.display = "none"; }} />
    </span>
  );
}
