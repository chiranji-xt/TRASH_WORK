import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import HeatmapLayer from "../components/HeatmapLayer";
import { fetchAllReports } from "../api/reportsApi";
import eventBus from "../data/eventBus";

import { useEffect, useState } from "react";
import { useRefresh } from "../context/RefreshContext.jsx";
import { PageHeader, ErrorState, LoadingState, Card } from "../components/ui";

export default function HeatmapView() {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const refreshTick = useRefresh();

  const loadReports = async () => {
    try {
      setError(null);
      const data = await fetchAllReports();
      // Filter reports that have valid coordinates and format for heatmap — preserved
      const validReports = (data || [])
        .filter((r) => r.latitude != null && r.longitude != null && !isNaN(parseFloat(r.latitude)) && !isNaN(parseFloat(r.longitude)))
        .map((r) => ({ latitude: parseFloat(r.latitude), longitude: parseFloat(r.longitude), confidence: r.confidence || 0.8 }));
      setPoints(validReports);
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

  if (loading) return <LoadingState label="Loading waste reports…" />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Geographic intelligence"
        title="Waste density"
        description={`${points.length} geotagged detection${points.length === 1 ? "" : "s"} · intensity weighted by AI confidence.`}
        actions={<span className="tnum rounded-lg border border-line bg-white px-2.5 py-1.5 font-mono text-xs font-bold text-ink-soft">{points.length} plotted</span>}
      />

      {points.length === 0 && (
        <div className="inv-card mb-4 px-5 py-4 text-center text-sm text-ink-mute">No reports with valid coordinates available yet.</div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="rise overflow-hidden p-2">
          <div className="h-[52vh] min-h-[340px] w-full overflow-hidden rounded-lg md:h-[64vh]">
            <MapContainer center={[18.5204, 73.8567]} zoom={12.5} style={{ height: "100%", width: "100%" }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap" />
              <HeatmapLayer points={points} />
            </MapContainer>
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 px-4 py-3">
            {[
              ["#E66B59", "Critical"],
              ["#F2B84B", "Elevated"],
              ["#D9C53A", "Watch"],
            ].map(([c, t]) => (
              <span key={t} className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink-soft">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} /> {t}
              </span>
            ))}
            <span className="ml-auto text-xs text-ink-mute">Crew priority scale</span>
          </div>
        </Card>

        <aside className="relative overflow-hidden rounded-xl bg-forest-deep p-5 text-white shadow-card">
          <div className="map-grid pointer-events-none absolute inset-0 opacity-60" />
          <div className="relative">
            <p className="metalabel !text-civic-lime/80">Coverage</p>
            <p className="tnum font-display mt-1 text-[38px] font-semibold leading-none">{points.length}</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-white/65">plottable detections in the current feed. Deep color marks sustained dumping — dispatch there first.</p>
            <div className="mt-4 border-t border-white/10 pt-3 text-xs leading-relaxed text-white/55">
              Intensity blends report density with AI confidence per detection.
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
