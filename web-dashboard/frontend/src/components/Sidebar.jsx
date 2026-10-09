import { Link, useLocation } from "react-router-dom";
import { API_CONFIG } from "../api/apiConfig";
import { Icon, paths } from "./icons";

const MENU = [
  { to: "/", label: "Overview", icon: paths.grid, match: (p) => p === "/" },
  { to: "/reports", label: "Reports", icon: paths.box, match: (p) => p.startsWith("/reports") },
  { to: "/locations", label: "Zone map", icon: paths.pin, match: (p) => p.startsWith("/locations") },
  { to: "/heatmap", label: "Density", icon: paths.flame, match: (p) => p.startsWith("/heatmap") },
  { to: "/analytics", label: "Analytics", icon: paths.chart, match: (p) => p.startsWith("/analytics") },
];

const GENERAL = [
  { to: "/settings", label: "Settings", icon: paths.gear, match: (p) => p.startsWith("/settings") },
];

export default function Sidebar({ open = false, onClose = () => {} }) {
  const { pathname } = useLocation();

  const item = (nav) => {
    const active = nav.match(pathname);
    return (
      <Link
        key={nav.to}
        to={nav.to}
        onClick={onClose}
        aria-current={active ? "page" : undefined}
        className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
          active ? "bg-white/[0.09] text-white" : "text-white/55 hover:bg-white/[0.05] hover:text-white"
        }`}
      >
        <span className={`flex h-8 w-8 items-center justify-center rounded-md transition ${active ? "bg-civic-lime text-forest-deep" : "text-white/45 group-hover:text-white/80"}`}>
          <Icon d={nav.icon} size={17} />
        </span>
        {nav.label}
        {active && <span className="ml-auto h-4 w-[3px] rounded-full bg-civic-lime" />}
      </Link>
    );
  };

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-forest-deep/60 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[240px] shrink-0 flex-col bg-forest-deep text-white transition-transform duration-300 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="map-grid pointer-events-none absolute inset-0 opacity-70" />
        <div className="relative flex flex-1 flex-col">
          {/* Brand */}
          <div className="flex items-center gap-2.5 px-5 pb-6 pt-6">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-civic-lime text-base font-bold text-forest-deep">◈</span>
            <div className="min-w-0">
              <p className="font-display truncate text-[19px] font-semibold leading-none tracking-tight">CleanCity</p>
              <p className="metalabel mt-1 !text-[10px] !text-white/40">Waste operations</p>
            </div>
            <button onClick={onClose} aria-label="Close navigation" className="ml-auto rounded-md p-1.5 text-white/60 hover:bg-white/10 lg:hidden">
              <Icon d={paths.x} size={18} />
            </button>
          </div>

          {/* Nav */}
          <nav className="inv-scroll flex-1 space-y-5 overflow-y-auto px-3" aria-label="Primary">
            <div>
              <p className="metalabel px-3 pb-2 !text-white/35">Operate</p>
              <div className="space-y-0.5">{MENU.map(item)}</div>
            </div>
            <div>
              <p className="metalabel px-3 pb-2 !text-white/35">Configure</p>
              <div className="space-y-0.5">{GENERAL.map(item)}</div>
            </div>
          </nav>

          {/* Field note */}
          <div className="p-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.05] p-4">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-civic-lime opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-civic-lime" />
                </span>
                <p className="text-[13px] font-semibold">Crews on shift</p>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-white/55">
                Mark reports <span className="font-semibold text-civic-lime">Cleaned</span> as zones are swept.
              </p>
              <p className="mt-2 truncate font-mono text-[10px] text-white/35" title={API_CONFIG.BASE_URL}>
                {(API_CONFIG.BASE_URL || "").replace(/^https?:\/\//, "")}
              </p>
            </div>
            <div className="mt-3 flex items-center gap-2.5 px-1">
              <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-civic-lime text-[13px] font-bold text-forest-deep">
                M
                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-forest-deep bg-civic-lime" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-[13px] font-semibold text-white">Municipality</p>
                <p className="text-[11px] text-white/45">Operator console</p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
