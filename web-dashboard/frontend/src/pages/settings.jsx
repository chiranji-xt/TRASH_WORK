import { useState } from "react";
import { PageHeader, Card } from "../components/ui";

export default function Settings() {
  const [interval, setInterval] = useState("30 seconds");
  const [theme, setTheme] = useState("Default");
  const [saved, setSaved] = useState(false);

  const save = (e) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="w-full max-w-3xl">
      <PageHeader
        eyebrow="Console"
        title="Preferences"
        description="Refresh cadence and map rendering for this workstation. Display-only — API endpoints and auth are never altered here."
      />

      <Card className="rise">
        <form onSubmit={save} className="grid grid-cols-1 gap-x-4 gap-y-5 px-5 py-5 sm:grid-cols-2">
          <div>
            <label htmlFor="refresh-interval" className="text-[13px] font-bold text-ink">Auto-refresh interval</label>
            <p className="mt-0.5 text-xs text-ink-mute">How often the feed heartbeat polls.</p>
            <select id="refresh-interval" value={interval} onChange={(e) => setInterval(e.target.value)} className="inv-input mt-1.5 bg-white px-3 py-2.5 [&>option]:bg-white">
              <option>10 seconds</option>
              <option>30 seconds</option>
              <option>1 minute</option>
            </select>
          </div>
          <div>
            <label htmlFor="map-theme" className="text-[13px] font-bold text-ink">Map theme</label>
            <p className="mt-0.5 text-xs text-ink-mute">Base layer treatment for zone maps.</p>
            <select id="map-theme" value={theme} onChange={(e) => setTheme(e.target.value)} className="inv-input mt-1.5 bg-white px-3 py-2.5 [&>option]:bg-white">
              <option>Default</option>
              <option>Dark</option>
              <option>Satellite</option>
            </select>
          </div>

          <div className="rounded-lg bg-[#FAF8F1] p-4 text-[13px] leading-relaxed text-ink-soft sm:col-span-2">
            Live signal polling (5s) and the 30s console heartbeat run independently of these
            preferences. Changes apply to this workstation immediately after saving.
          </div>

          <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
            <button type="submit" className="inv-btn-primary">Save preferences</button>
            {saved && <p role="status" className="text-[13px] font-bold text-forest">Saved to this workstation.</p>}
          </div>
        </form>
      </Card>
    </div>
  );
}
