import { Link, useLocation } from "react-router-dom";
import { API_CONFIG } from "../api/apiConfig";

export default function Sidebar() {
  const { pathname } = useLocation();

  const isActive = (path) =>
    pathname === path
      ? "bg-gray-900 text-white"
      : "text-gray-300 hover:bg-gray-700";

  return (
    <div className="w-56 h-screen bg-gray-800 text-white flex flex-col py-6 px-4 gap-4">

      {/* APP TITLE */}
      <div className="mb-6">
        <h1 className="text-xl font-bold">📊 Municipal</h1>
        <p className="text-gray-400 text-sm">Waste intelligence console</p>
      </div>

      {/* MENU ITEMS */}
      <nav className="flex flex-col gap-1">

        <Link to="/" className={`py-2 px-3 rounded ${isActive("/")}`}>
          Dashboard
        </Link>

        <Link to="/heatmap" className={`py-2 px-3 rounded ${isActive("/heatmap")}`}>
          Heatmap View
        </Link>

        <Link to="/locations" className={`py-2 px-3 rounded ${isActive("/locations")}`}>
          Locations Map
        </Link>

        <Link to="/reports" className={`py-2 px-3 rounded ${isActive("/reports")}`}>
          Reports
        </Link>

        <Link to="/settings" className={`py-2 px-3 rounded ${isActive("/settings")}`}>
          Settings
        </Link>

      </nav>

      {/* Connection Status */}
      <div className="mt-auto px-4 pb-4 pt-4 border-t border-gray-700">
        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-2">Connection</p>
        <div className="flex items-center gap-2 bg-gray-900/50 p-2 rounded border border-gray-700">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </div>
          <span className="text-xs text-blue-300 font-mono truncate w-full" title={API_CONFIG.BASE_URL}>
            {API_CONFIG.BASE_URL.replace(/^https?:\/\//, '')}
          </span>
        </div>
      </div>
    </div>
  );
}
