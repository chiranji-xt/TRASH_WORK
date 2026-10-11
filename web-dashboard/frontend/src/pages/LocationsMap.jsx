import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Correct working cluster library — preserved
import MarkerClusterGroup from "@changey/react-leaflet-markercluster";

// Required CSS — preserved
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { fetchAllReports, fetchCases, fetchCaseById } from "../api/reportsApi";
import { useEffect, useState } from "react";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import L from "leaflet";
import { PageHeader, ErrorState, LoadingState, Card } from "../components/ui";
import ReportModal from "../components/ReportModal";
import CasePanel from "../components/CasePanel";
import HeatmapLayer from "../components/HeatmapLayer";

// Pin colors per waste class — preserved behavior (violet replaces the
// non-existent "purple" asset so E-Waste pins actually render).
const classColors = {
  Plastic: "blue", Organic: "green", Metal: "red", "E-Waste": "violet", Hazardous: "orange",
  plastic: "blue", organic: "green", metal: "red", "e-waste": "violet", hazardous: "orange",
};

// Helper: colored icon — preserved
function makeColoredIcon(color) {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${color}.png`,
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.4/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });
}

// Helper: pin with a report_count badge for merged cases — preserved pin art.
function makeCountIcon(color, count) {
  return L.divIcon({
    className: "case-pin",
    html:
      `<div style="position:relative;width:25px;height:41px;">` +
      `<img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${color}.png" style="width:25px;height:41px;display:block;" alt="" />` +
      `<span style="position:absolute;top:-9px;right:-11px;min-width:20px;height:20px;padding:0 5px;border-radius:999px;background:#12372A;color:#D6F453;font:700 11px/20px ui-monospace,monospace;text-align:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);">${count}</span></div>`,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  });
}
function MapBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points && points.length > 0) {
      const bounds = L.latLngBounds(points.map((p) => [p.latitude, p.longitude]));
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    } else {
      map.setView([18.5204, 73.8567], 12);
    }
  }, [points, map]);
  return null;
}

const LEGEND = [
  ["blue", "Plastic"], ["green", "Organic"], ["red", "Metal"], ["violet", "E-Waste"], ["orange", "Hazardous"],
];

export default function LocationsMap() {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ total: 0, visible: 0, skipped: 0 });
  const [view, setView] = useState("pins"); // "pins" | "heatmap"
  const [casesById, setCasesById] = useState({});
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseLoading, setCaseLoading] = useState(false);
  const [showCase, setShowCase] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAllReports();
      const rawCount = data?.length || 0;
      // Filter reports that have valid coordinates — preserved
      const validReports = (data || [])
        .map((r) => {
          const lat = r.latitude !== undefined ? Number(r.latitude) : Number(r.lat);
          const lon = r.longitude !== undefined ? Number(r.longitude) : Number(r.lon);
          return { ...r, latitude: lat, longitude: lon };
        })
        .filter((r) => !isNaN(r.latitude) && !isNaN(r.longitude) && r.latitude !== 0 && r.longitude !== 0);
      setPoints(validReports);
      setStats({ total: rawCount, visible: validReports.length, skipped: rawCount - validReports.length });
      // Cases for count badges + detail panel. fetchCases falls back to []
      // on backends without the /cases route (e.g. the demo backend).
      try {
        const cases = await fetchCases();
        const map = {};
        for (const c of cases || []) map[c.id] = c;
        setCasesById(map);
      } catch {
        setCasesById({});
      }
    } catch (err) {
      console.error("LocationsMap: Failed to load reports:", err);
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

  const getWasteClass = (report) => report.prediction || report.waste_class || report.predicted_class || report.class || "Plastic";
  const getColor = (report) => {
    const lower = getWasteClass(report).toLowerCase();
    const k = Object.keys(classColors).find((key) => key.toLowerCase() === lower);
    return classColors[k] || "blue";
  };
  const caseCountOf = (p) => {
    if (p.case_id == null) return 0;
    const c = casesById[p.case_id];
    return c ? Number(c.report_count || 0) : 0;
  };

  const openPoint = async (p) => {
    // Reports grouped into a multi-report case open the case dossier
    // (merged photos); lone reports open the standard report modal.
    if (p.case_id != null && caseCountOf(p) > 1) {
      setShowCase(true);
      setCaseLoading(true);
      setSelectedCase(null);
      try {
        setSelectedCase(await fetchCaseById(p.case_id));
      } catch (err) {
        console.error("Failed to load case:", err);
        setSelectedCase(null);
      } finally {
        setCaseLoading(false);
      }
    } else {
      setSelectedReport(p);
      setShowReport(true);
    }
  };

  if (loading && points.length === 0) return <LoadingState label="Loading waste reports…" />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Geographic intelligence"
        title="Zone map"
        description={`Showing ${stats.visible} of ${stats.total} reports${stats.skipped ? ` · ${stats.skipped} without coordinates hidden` : ""}.`}
        actions={
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-line bg-white p-0.5" role="tablist" aria-label="Map view">
              {[
                ["pins", "Pins"],
                ["heatmap", "Heatmap"],
              ].map(([v, label]) => (
                <button
                  key={v}
                  role="tab"
                  aria-selected={view === v}
                  onClick={() => setView(v)}
                  className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${
                    view === v ? "bg-forest-deep text-white" : "text-ink-soft hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="tnum rounded-lg border border-line bg-white px-2.5 py-1.5 font-mono text-xs font-bold text-ink-soft">{stats.visible}/{stats.total} plotted</span>
          </div>
        }
      />

      {points.length === 0 && !loading && (
        <div className="inv-card mb-4 px-5 py-4 text-center text-sm text-ink-mute">No reports with valid coordinates available. Showing default view (Pune).</div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="rise overflow-hidden p-2">
          <div className="h-[52vh] min-h-[340px] w-full overflow-hidden rounded-lg md:h-[68vh]">
            <MapContainer center={[18.5204, 73.8567]} zoom={12} style={{ height: "100%", width: "100%" }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap" />
              <MapBounds points={points} />
              {view === "heatmap" ? (
                <HeatmapLayer points={points} />
              ) : (
              <MarkerClusterGroup chunkedLoading spiderfyOnMaxZoom removeOutsideVisibleBounds={false} maxClusterRadius={40}>
                {points.map((p) => {
                  const count = caseCountOf(p);
                  const icon = count > 1 ? makeCountIcon(getColor(p), count) : makeColoredIcon(getColor(p));
                  return (
                    <Marker
                      key={p.case_id != null && count > 1 ? `case-${p.case_id}` : `report-${p.id}`}
                      position={[p.latitude, p.longitude]}
                      icon={icon}
                      eventHandlers={{ click: () => openPoint(p) }}
                    />
                  );
                })}
              </MarkerClusterGroup>
              )}
            </MapContainer>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3">
            {view === "heatmap" ? (
              <>
                {[["#E66B59", "Critical"], ["#F2B84B", "Elevated"], ["#D9C53A", "Watch"]].map(([c, t]) => (
                  <span key={t} className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} /> {t}
                  </span>
                ))}
                <span className="ml-auto text-xs text-ink-mute">Intensity blends report density with AI confidence</span>
              </>
            ) : (
              <>
            {LEGEND.map(([c, label]) => (
              <span key={label} className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
                <img src={`https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${c}.png`} alt="" className="h-4 w-auto" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
                {label}
              </span>
            ))}
            <span className="ml-auto text-xs text-ink-mute">Tap a cluster to spiderfy</span>
              </>
            )}
          </div>
        </Card>

        <aside className="h-fit space-y-4">
          <div className="inv-card rise-1 p-5">
            <p className="metalabel">Pin legend</p>
            <h2 className="font-display mt-1 text-[19px] font-semibold tracking-tight text-ink">Category colors</h2>
            <ol className="mt-3 space-y-1.5">
              {LEGEND.map(([c, label], i) => (
                <li key={label} className="flex items-center gap-2.5 rounded-lg px-2 py-1.5">
                  <span className="tnum w-5 font-mono text-[11px] text-ink-mute">0{i + 1}</span>
                  <img src={`https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${c}.png`} alt="" className="h-5 w-auto" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
                  <span className="text-[13px] font-semibold text-ink">{label}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="relative overflow-hidden rounded-xl bg-forest-deep p-5 text-white shadow-card">
            <div className="map-grid pointer-events-none absolute inset-0 opacity-60" />
            <div className="relative">
              <p className="metalabel !text-civic-lime/80">Coverage</p>
              <p className="tnum font-display mt-1 text-[38px] font-semibold leading-none">{stats.visible}</p>
              <p className="mt-1.5 text-[13px] leading-relaxed text-white/65">of {stats.total} reports plotted{stats.skipped ? ` · ${stats.skipped} hidden without location` : ""}.</p>
            </div>
          </div>
        </aside>
      </div>

      {showCase && (
        <CasePanel caseData={selectedCase} loading={caseLoading} onClose={() => setShowCase(false)} />
      )}
      {showReport && (
        <ReportModal report={selectedReport} loading={false} onClose={() => setShowReport(false)} />
      )}
    </div>
  );
}
