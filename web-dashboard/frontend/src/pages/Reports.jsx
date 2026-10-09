import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { fetchAllReports, fetchReportsByStatus, fetchReportById, getImageUrl } from "../api/reportsApi";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST, ageOf } from "../utils/timezone";
import ReportModal from "../components/ReportModal";
import UpdateStatusButton from "../components/UpdateStatusButton";
import { PageHeader, Tabs, EmptyState, ErrorState, LoadingState, Card } from "../components/ui";
import { Icon, paths, wasteMeta } from "../components/icons";

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Filter state — preserved
  const [currentFilter, setCurrentFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [oldestFirst, setOldestFirst] = useState(false);
  const routeLocation = useLocation();

  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setLoading(true);
      setError(null);

      let data;
      if (currentFilter === "all") {
        data = await fetchAllReports();
      } else {
        // Backend expects lowercase "pending" | "cleaned" (case-insensitive).
        data = await fetchReportsByStatus(currentFilter.toLowerCase());
      }

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
  }, [refreshTick, currentFilter]);

  // Global search handoff from Navbar
  useEffect(() => {
    if (routeLocation.state?.q) setQuery(routeLocation.state.q);
    const onSearch = (e) => setQuery(e.detail || "");
    window.addEventListener("ops:search", onSearch);
    return () => window.removeEventListener("ops:search", onSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpdateStatus = (id, newStatus) => {
    // Optimistically update local state — preserved
    setReports((prev) => prev.map((r) => (r.id === id ? { ...r, status: newStatus } : r)));
    eventBus.emit("report-updated", { id, status: newStatus });
  };

  const handleViewReport = async (report) => {
    setLoadingDetail(true);
    setShowModal(true);
    setSelectedReport(report);
    try {
      const freshReport = await fetchReportById(report.id);
      setSelectedReport(freshReport);
    } catch (err) {
      console.error("Failed to load report details:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const getLocationString = (r) => {
    if (r.location_name) return r.location_name;
    if (r.locationName) return r.locationName;
    if (r.latitude && r.longitude) return `${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}`;
    if (r.lat && r.lon) return `${Number(r.lat).toFixed(4)}, ${Number(r.lon).toFixed(4)}`;
    return "Unknown zone";
  };

  const wasteOf = (r) => r.waste_class || r.prediction || r.predicted_class || r.class || "Unknown";
  const tsOf = (r) => new Date(r.created_at || r.timestamp || 0).getTime();

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = q
      ? reports.filter((r) =>
          [String(r.id), getLocationString(r), wasteOf(r), String(r.status || "")].join(" ").toLowerCase().includes(q)
        )
      : [...reports];
    // Presentation-only ordering; backend values untouched
    list.sort((a, b) => (oldestFirst ? tsOf(a) - tsOf(b) : tsOf(b) - tsOf(a)));
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports, query, oldestFirst]);

  const pendingCount = reports.filter((r) => String(r.status || "").toLowerCase() === "pending").length;
  const cleanedCount = reports.filter((r) => String(r.status || "").toLowerCase() === "cleaned").length;

  // The backend data model supports exactly two workflow statuses (Pending/Cleaned).
  const filters = [
    { id: "all", label: "All Reports", count: currentFilter === "all" ? reports.length : undefined },
    { id: "pending", label: "Pending Cleanup", count: pendingCount || undefined },
    { id: "cleaned", label: "Cleaned", count: cleanedCount || undefined },
  ];

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Dispatch operations"
        title="Waste Reports"
        description="Monitor citizen reports and track cleanup progress across municipal zones."
        actions={
          <>
            <label className="flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 transition focus-within:border-forest">
              <span className="text-ink-mute"><Icon d={paths.search} size={15} /></span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search report ID, location, waste type..."
                aria-label="Filter reports"
                className="w-48 bg-transparent text-sm text-ink outline-none placeholder:text-ink-mute/70"
              />
              {query && (
                <button onClick={() => setQuery("")} aria-label="Clear filter" className="text-ink-mute hover:text-ink">
                  <Icon d={paths.x} size={14} />
                </button>
              )}
            </label>
            <Tabs options={filters} value={currentFilter} onChange={setCurrentFilter} ariaLabel="Status filter" />
          </>
        }
      />

      {error && <div className="mb-4"><ErrorState message={error} onRetry={loadReports} /></div>}

      {loading ? (
        <LoadingState label="Loading waste reports…" />
      ) : visible.length === 0 ? (
        <EmptyState
          title="No waste reports found"
          hint="There are currently no reports matching your selected filters."
          action={
            query || currentFilter !== "all" ? (
              <button onClick={() => { setQuery(""); setCurrentFilter("all"); }} className="inv-btn-ghost !py-2 text-[13px]">
                Clear filters
              </button>
            ) : null
          }
        />
      ) : (
        <Card className="rise overflow-hidden">
          <div className="flex flex-wrap items-end justify-between gap-3 px-5 pb-4 pt-5">
            <div>
              <p className="metalabel mb-1">Queue</p>
              <h2 className="font-display text-[19px] font-semibold tracking-tight text-ink">Report Management</h2>
              <p className="mt-0.5 text-[13px] text-ink-mute">Review reported waste and coordinate cleanup operations.</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="tnum rounded border border-line bg-[#FAF8F1] px-2 py-1 font-mono text-[11px] font-bold text-ink-soft">
                {visible.length} shown
              </span>
              <div className="flex rounded-lg border border-line bg-white p-0.5" role="group" aria-label="Sort order">
                {[
                  { id: false, label: "Newest" },
                  { id: true, label: "Oldest" },
                ].map((o) => (
                  <button
                    key={o.label}
                    onClick={() => setOldestFirst(o.id)}
                    aria-pressed={oldestFirst === o.id}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${oldestFirst === o.id ? "bg-forest text-white" : "text-ink-mute hover:text-ink"}`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Desktop ledger */}
          <ol className="hidden divide-y divide-line/80 border-t border-line/80 md:block">
            {visible.map((r) => {
              const cls = wasteOf(r);
              const meta = wasteMeta(cls);
              const pending = String(r.status || "").toLowerCase() === "pending";
              return (
                <li key={r.id} className="inv-row flex items-center gap-3 px-4 py-3 md:gap-4 md:px-5">
                  <span className={`hidden w-1 self-stretch rounded-full sm:block ${pending ? "bg-civic-amber" : "bg-forest/25"}`} aria-hidden="true" />
                  <span className="block h-12 w-12 shrink-0 overflow-hidden rounded-lg border border-line bg-[#F4F2E9]">
                    {(r.boxed_image_path || r.image_path) ? (
                      <img src={getImageUrl(r.boxed_image_path || r.image_path)} alt="Report evidence" loading="lazy" className="h-full w-full object-cover" onError={(e) => { e.target.style.display = "none"; }} />
                    ) : (
                      <span className="flex h-full w-full items-center justify-center" style={{ color: meta.tx, background: meta.bg }}>
                        <Icon d={meta.icon} size={20} />
                      </span>
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-baseline gap-x-2">
                      <span className="tnum font-display text-[17px] font-semibold text-ink">#{r.id}</span>
                      <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink-soft" title={getLocationString(r)}>{getLocationString(r)}</span>
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-mute">
                      <span className="inline-flex items-center gap-1 font-semibold" style={{ color: meta.tx }}>
                        <Icon d={meta.icon} size={12} /> {cls}
                      </span>
                      <span className="tnum">{convertUTCtoIST(r.created_at || r.timestamp)}</span>
                      {pending && <span className="tnum font-mono font-semibold text-[#9A6700]">waiting {ageOf(r.created_at || r.timestamp)}</span>}
                    </span>
                  </span>
                  <span className="shrink-0">
                    <UpdateStatusButton reportId={r.id} currentStatus={r.status} onUpdate={(s) => handleUpdateStatus(r.id, s)} />
                  </span>
                  <button onClick={() => handleViewReport(r)} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-bold text-ink transition hover:border-forest/50 hover:text-forest">
                    Dossier <Icon d={paths.arrowUR} size={13} />
                  </button>
                </li>
              );
            })}
          </ol>

          {/* Mobile cards */}
          <ol className="space-y-2.5 p-3 md:hidden">
            {visible.map((r) => {
              const cls = wasteOf(r);
              const meta = wasteMeta(cls);
              const pending = String(r.status || "").toLowerCase() === "pending";
              return (
                <li key={r.id} className="rounded-xl border border-line bg-white p-3.5">
                  <div className="flex items-start gap-3">
                    <span className="block h-14 w-14 shrink-0 overflow-hidden rounded-lg border border-line bg-[#F4F2E9]">
                      {(r.boxed_image_path || r.image_path) ? (
                        <img src={getImageUrl(r.boxed_image_path || r.image_path)} alt="Report evidence" loading="lazy" className="h-full w-full object-cover" onError={(e) => { e.target.style.display = "none"; }} />
                      ) : (
                        <span className="flex h-full w-full items-center justify-center" style={{ color: meta.tx, background: meta.bg }}>
                          <Icon d={meta.icon} size={22} />
                        </span>
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="tnum font-display text-[16px] font-semibold text-ink">#{r.id}</p>
                      <p className="truncate text-[13px] text-ink-soft">{getLocationString(r)}</p>
                      <p className="tnum mt-0.5 font-mono text-[11px] text-ink-mute">
                        {convertUTCtoIST(r.created_at || r.timestamp)}
                        {pending && <span className="font-bold text-[#9A6700]"> · waiting {ageOf(r.created_at || r.timestamp)}</span>}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2 border-t border-line/70 pt-3">
                    <UpdateStatusButton reportId={r.id} currentStatus={r.status} onUpdate={(s) => handleUpdateStatus(r.id, s)} />
                    <button onClick={() => handleViewReport(r)} className="inline-flex items-center gap-1.5 rounded-lg bg-forest px-3 py-2 text-xs font-bold text-white">
                      Dossier <Icon d={paths.arrowUR} size={13} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {showModal && <ReportModal report={selectedReport} loading={loadingDetail} onClose={() => setShowModal(false)} />}
    </div>
  );
}
