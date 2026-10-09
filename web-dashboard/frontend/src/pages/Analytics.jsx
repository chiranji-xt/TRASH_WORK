import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, Card } from "../components/ui";
import { fetchAllReports, fetchHotspots, fetchStatsSummary } from "../api/reportsApi";

const COLORS = ["#123D32", "#3E9B4F", "#E66B59"];

function LiveBars({ values, color }) {
  const max = Math.max(1, ...values);
  return (
    <div className="mt-4 flex h-28 items-end gap-1.5 rounded-lg bg-[#FAF8F1] p-3">
      {values.map((v, j) => (
        <div
          key={j}
          className="flex-1 rounded-t-sm"
          title={String(v)}
          style={{ height: `${Math.max(4, Math.round((v / max) * 100))}%`, background: color, opacity: 0.45 + (j / Math.max(1, values.length)) * 0.5 }}
        />
      ))}
    </div>
  );
}

export default function Analytics() {
  const [reports, setReports] = useState([]);
  const [summary, setSummary] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        try {
          const [s, h] = await Promise.all([fetchStatsSummary(), fetchHotspots()]);
          if (!cancelled) {
            setSummary(s);
            setHotspots(h?.hotspots || []);
          }
        } catch {
          /* client-side fallback below */
        }
        const all = await fetchAllReports();
        if (!cancelled) setReports(all || []);
      } catch {
        if (!cancelled) setReports([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const perDay = useMemo(() => {
    const map = summary?.per_day ? { ...summary.per_day } : {};
    if (!summary?.per_day) {
      for (const r of reports) {
        const key = (r.created_at || r.timestamp || "").slice(0, 10) || "unknown";
        map[key] = (map[key] || 0) + 1;
      }
    }
    return Object.entries(map).sort().slice(-7);
  }, [reports, summary]);

  const perClass = useMemo(() => {
    const map = summary?.per_class ? { ...summary.per_class } : {};
    if (!summary?.per_class) {
      for (const r of reports) {
        const k = r.prediction || r.waste_class || "unknown";
        map[k] = (map[k] || 0) + 1;
      }
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 7);
  }, [reports, summary]);

  const hotspotRows = useMemo(() => {
    if (hotspots.length) return hotspots.slice(0, 7);
    const cells = {};
    for (const r of reports) {
      const lat = Number(r.latitude ?? r.lat);
      const lon = Number(r.longitude ?? r.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
      const key = `${lat.toFixed(2)},${lon.toFixed(2)}`;
      cells[key] = (cells[key] || 0) + 1;
    }
    return Object.entries(cells)
      .map(([key, count]) => {
        const [latitude, longitude] = key.split(",").map(Number);
        return { latitude, longitude, count };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 7);
  }, [reports, hotspots]);

  const cards = [
    {
      title: "Reports per day",
      description: `Detection volume over the last 7 days — live (${summary?.total ?? reports.length} total).`,
      values: perDay.map(([, v]) => v),
      footer: perDay.length ? perDay.map(([d]) => d.slice(5)).join(" · ") : "No data yet",
    },
    {
      title: "Category split",
      description: "Detected waste classes, ranked — live.",
      values: perClass.map(([, v]) => v),
      footer: perClass.length ? perClass.map(([c]) => c).join(" · ") : "No data yet",
    },
    {
      title: "Zone hotspots",
      description: "Highest-concentration zones, ranked — live.",
      values: hotspotRows.map((h) => h.count),
      footer: hotspotRows.length
        ? hotspotRows.map((h) => `${Number(h.latitude).toFixed(2)},${Number(h.longitude).toFixed(2)} (${h.count})`).join(" · ")
        : "No data yet",
    },
  ];

  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Analysis"
        title="Resolution analytics"
        description={loading ? "Loading live trends…" : "Live trends from the backend (/reports/stats/* with client-side fallback)."}
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((c, i) => (
          <Card key={c.title} className={`p-5 ${i === 0 ? "rise" : i === 1 ? "rise-1" : "rise-2"}`}>
            <p className="metalabel">{c.title}</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-mute">{c.description}</p>
            {c.values.length === 0 ? (
              <p className="mt-4 text-[13px] text-ink-mute">No data yet — submit a report to populate this chart.</p>
            ) : (
              <LiveBars values={c.values} color={COLORS[i % COLORS.length]} />
            )}
            <p className="mt-3 text-[11px] leading-relaxed text-ink-mute">{c.footer}</p>
          </Card>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to="/" className="inv-btn-primary">Open live overview →</Link>
        <Link to="/heatmap" className="inv-btn-ghost">View density heatmap</Link>
      </div>
    </div>
  );
}
