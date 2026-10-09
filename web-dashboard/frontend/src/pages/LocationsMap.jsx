import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Correct working cluster library — preserved
import MarkerClusterGroup from "@changey/react-leaflet-markercluster";

// Required CSS — preserved
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { fetchAllReports, getImageUrl } from "../api/reportsApi";
import { useEffect, useState } from "react";
import eventBus from "../data/eventBus";
import { useRefresh } from "../context/RefreshContext.jsx";
import { convertUTCtoIST, ageOf } from "../utils/timezone";
import L from "leaflet";
import { PageHeader, ErrorState, LoadingState, Card } from "../components/ui";
import StatusBadge from "../components/StatusBadge";

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

// --- SUB-COMPONENT FOR AUTO-FITTING BOUNDS — preserved ---
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
  const getLocationText = (p) => {
    if (p.location_name && p.location_name !== "Unknown") return p.location_name;
    if (p.locationName && p.locationName !== "Unknown") return p.locationName;
    return `${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}`;
  };

  if (loading && points.length === 0) return <LoadingState label="Loading waste reports…" />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Geographic intelligence"
        title="Zone map"
        description={`Showing ${stats.visible} of ${stats.total} reports${stats.skipped ? ` · ${stats.skipped} without coordinates hidden` : ""}.`}
        actions={<span className="tnum rounded-lg border border-line bg-white px-2.5 py-1.5 font-mono text-xs font-bold text-ink-soft">{stats.visible}/{stats.total} plotted</span>}
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
              <MarkerClusterGroup chunkedLoading spiderfyOnMaxZoom removeOutsideVisibleBounds={false} maxClusterRadius={40}>
                {points.map((p) => {
                  const pending = String(p.status || "").toLowerCase() === "pending";
                  return (
                    <Marker key={p.id} position={[p.latitude, p.longitude]} icon={makeColoredIcon(getColor(p))}>
                      <Popup minWidth={250}>
                        <div className="p-1">
                          {p.boxed_image_path || p.image_path ? (
                            <div className="mb-2 h-32 w-full overflow-hidden rounded-md bg-[#F4F2E9]">
                              <img src={getImageUrl(p.boxed_image_path || p.image_path)} alt="Detection preview" className="h-full w-full object-cover" onError={(e) => { e.target.style.display = "none"; }} />
                            </div>
                          ) : (
                            <div className="mb-2 flex h-16 w-full items-center justify-center rounded-md border border-dashed border-line bg-[#FAF8F1] text-xs text-ink-mute">No photograph</div>
                          )}
                          <div className="space-y-1">
                            <div className="flex items-center justify-between gap-2">
                              <span className="tnum font-display text-[16px] font-semibold text-ink">#{p.id}</span>
                              <span className="rounded bg-[#EFF0EA] px-2 py-0.5 text-xs font-bold text-ink-soft">{getWasteClass(p)}</span>
                            </div>
                            <p className="text-[13px] text-ink-soft">{getLocationText(p)}</p>
                            <p className="tnum font-mono text-[11px] text-ink-mute">
                              {convertUTCtoIST(p.created_at || p.timestamp)}
                              {pending && <span className="font-bold text-[#9A6700]"> · waiting {ageOf(p.created_at || p.timestamp)}</span>}
                            </p>
                            {p.status && <div className="pt-1"><StatusBadge status={p.status} size="sm" /></div>}
                          </div>
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}
              </MarkerClusterGroup>
            </MapContainer>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3">
            {LEGEND.map(([c, label]) => (
              <span key={label} className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
                <img src={`https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${c}.png`} alt="" className="h-4 w-auto" loading="lazy" onError={(e) => { e.target.style.display = "none"; }} />
                {label}
              </span>
            ))}
            <span className="ml-auto text-xs text-ink-mute">Tap a cluster to spiderfy</span>
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
    </div>
  );
}
