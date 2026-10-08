import Sidebar from "../components/Sidebar.jsx";
import Navbar from "../components/Navbar.jsx";

function ChartCard({ title, description }) {
  return (
    <div className="glass-card p-4 flex flex-col justify-between">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-gray-500 mb-1">
          {title}
        </p>
        <p className="text-xs text-gray-500 mb-3">{description}</p>
      </div>

      {/* Faux chart */}
      <div className="h-32 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 relative overflow-hidden">
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_1px_1px,_#e5e7eb_1px,_transparent_0)] [background-size:16px_16px]" />
        <div className="absolute inset-x-4 bottom-3 flex items-end gap-1">
          <div className="flex-1 h-8 rounded-t-xl bg-sky-400/80" />
          <div className="flex-1 h-14 rounded-t-xl bg-emerald-400/80" />
          <div className="flex-1 h-20 rounded-t-xl bg-blue-400/80" />
          <div className="flex-1 h-10 rounded-t-xl bg-purple-400/80" />
          <div className="flex-1 h-16 rounded-t-xl bg-rose-400/80" />
        </div>
      </div>
    </div>
  );
}

export default function Analytics() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f5f5f7] to-[#e5e5ea] flex">
      <Sidebar />

      <main className="flex-1 p-4 md:p-8 space-y-6">
        <Navbar />

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Analytics</h2>
          <p className="text-xs text-gray-500">
            High-level trends based on detections, classifications and
            municipal actions. Replace the faux charts with a library like
            Recharts / Chart.js later.
          </p>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <ChartCard
            title="Reports per day"
            description="Volume of detections over the last 7 days."
          />
          <ChartCard
            title="Class distribution"
            description="Breakdown across plastic, organic, metal and others."
          />
          <ChartCard
            title="Area hotspots"
            description="Zones with the highest concentration of reports."
          />
        </section>
      </main>
    </div>
  );
}
