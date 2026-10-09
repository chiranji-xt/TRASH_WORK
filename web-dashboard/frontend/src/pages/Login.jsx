import { useState } from "react";
import { API_CONFIG } from "../api/apiConfig";

export default function Login({ onLogin }) {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    const key = apiKey.trim();
    if (!key) {
      setError("Enter the admin API key (ADMIN_API_KEY from the backend .env).");
      return;
    }
    setChecking(true);
    try {
      // Confirm the backend is reachable, then store the key. It is sent as
      // the X-API-Key header and is required for status updates.
      const res = await fetch(`${API_CONFIG.BASE_URL}/health`, {
        headers: { "ngrok-skip-browser-warning": "true" },
      });
      if (!res.ok) throw new Error(`Backend unreachable (${res.status})`);
      try {
        localStorage.setItem("admin_api_key", key);
      } catch {
        /* storage unavailable */
      }
      onLogin();
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded-2xl border border-line bg-white shadow-pop md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* Brand panel */}
        <div className="relative hidden flex-col justify-between overflow-hidden bg-forest-deep p-8 text-white md:flex">
          <div className="map-grid pointer-events-none absolute inset-0 opacity-70" />
          <div className="pointer-events-none absolute -bottom-24 -right-16 h-64 w-64 rounded-full bg-civic-lime/15 blur-3xl" />
          <div className="relative">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-civic-lime text-lg font-bold text-forest-deep">◈</span>
            <p className="font-display mt-4 text-[26px] font-semibold leading-tight tracking-tight">CleanCity Ops</p>
            <p className="metalabel mt-1.5 !text-white/40">Municipal waste console</p>
          </div>
          <div className="relative">
            <p className="font-display text-[19px] font-medium leading-snug text-white/90">
              “Every report mapped.<br />Every zone answered.”
            </p>
            <div className="mt-5 space-y-2.5 border-t border-white/10 pt-5 text-[13px]">
              {[
                ["Live report feed", "detections queue in real time"],
                ["Hotspot intelligence", "density, zones and pins"],
                ["One-tap dispatch", "pending → cleaned"],
              ].map(([t, s]) => (
                <div key={t} className="flex items-baseline gap-2">
                  <span className="h-1 w-1 shrink-0 translate-y-[-2px] rounded-full bg-civic-lime" />
                  <p className="text-white/80"><span className="font-semibold text-white">{t}</span> — {s}</p>
                </div>
              ))}
            </div>
          </div>
          <p className="relative font-mono text-[11px] text-white/35">civic operations · est. for the city</p>
        </div>

        {/* Form panel — behavior preserved */}
        <div className="p-7 md:p-9">
          <p className="metalabel md:hidden">CleanCity Ops · sign in</p>
          <h1 className="font-display mt-1 text-[28px] font-semibold tracking-tight text-ink">Welcome back</h1>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-mute">Sign in to manage waste reports and cleanup dispatch.</p>

          <form onSubmit={handleSubmit} className="mt-7 space-y-4">
            <div>
              <label htmlFor="login-key" className="mb-1.5 block text-[13px] font-bold text-ink">Admin API key</label>
              <input id="login-key" type="password" required value={apiKey} className="inv-input px-3.5 py-2.5" placeholder="ADMIN_API_KEY from backend .env" onChange={(e) => setApiKey(e.target.value)} autoComplete="off" />
            </div>
            {error && <p className="text-[13px] font-semibold text-[#A03E2E]">{error}</p>}
            <button type="submit" disabled={checking} className="inv-btn-primary w-full !py-3 disabled:opacity-50">{checking ? "Verifying…" : "Sign in to console"}</button>
          </form>

          <p className="mt-6 border-t border-line pt-4 text-center text-[11px] leading-relaxed text-ink-mute">Backend: {API_CONFIG.BASE_URL} (set VITE_API_URL to change it). The key is sent as the X-API-Key header.</p>
        </div>
      </div>
    </div>
  );
}
