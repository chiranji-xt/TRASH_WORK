import { Link } from "react-router-dom";
import { PageHeader, Card } from "../components/ui";

const CARDS = [
  { title: "Reports per day", description: "Detection volume over the last 7 days — live version on the Overview.", bars: [32, 56, 80, 42, 64, 52, 88], color: "#123D32" },
  { title: "Category split", description: "Plastic, organic, metal and others — live version on the Overview.", bars: [70, 45, 60, 35, 78, 50, 66], color: "#3E9B4F" },
  { title: "Zone hotspots", description: "Highest-concentration zones — live version on Density.", bars: [40, 62, 48, 84, 58, 72, 44], color: "#E66B59" },
];

export default function Analytics() {
  return (
    <div className="w-full">
      <PageHeader
        eyebrow="Analysis"
        title="Resolution analytics"
        description="High-level trends. Live charts ship on the Overview — this view is kept for deep dives."
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((c, i) => (
          <Card key={c.title} className={`p-5 ${i === 0 ? "rise" : i === 1 ? "rise-1" : "rise-2"}`}>
            <p className="metalabel">{c.title}</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-mute">{c.description}</p>
            <div className="mt-4 flex h-28 items-end gap-1.5 rounded-lg bg-[#FAF8F1] p-3">
              {c.bars.map((h, j) => (
                <div key={j} className="flex-1 rounded-t-sm" style={{ height: `${h}%`, background: c.color, opacity: 0.45 + (j / c.bars.length) * 0.5 }} />
              ))}
            </div>
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
