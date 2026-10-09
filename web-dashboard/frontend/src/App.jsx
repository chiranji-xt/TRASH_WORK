import { useState } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";

import Login from "./pages/Login.jsx";
import DashboardHome from "./pages/DashboardHome.jsx";
import HeatmapView from "./pages/HeatmapView.jsx";
import LocationsMap from "./pages/LocationsMap.jsx";
import Reports from "./pages/Reports.jsx";
import Settings from "./pages/settings.jsx";

import Sidebar from "./components/Sidebar.jsx";
import Navbar from "./components/Navbar.jsx";
import ToastNotification from "./components/ToastNotification.jsx";
import NotificationPoller from "./components/NotificationPoller.jsx";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(true);
  // Set to true so you don't get blocked while testing UI
  const [navOpen, setNavOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />;
  }

  const handleSearch = (q) => {
    // Global search jumps to the waste reports page and hands off the query
    // via navigation state; Reports preserves all existing filter logic.
    if (location.pathname !== "/reports") {
      navigate("/reports", { state: { q } });
    } else {
      window.dispatchEvent(new CustomEvent("ops:search", { detail: q }));
    }
  };

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />

      <div className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-[1400px] px-4 py-5 md:px-6">
          <Navbar onMenu={() => setNavOpen(true)} onSearch={handleSearch} />

          <main className="pb-8">
            <Routes>
              <Route path="/" element={<DashboardHome />} />
              <Route path="/heatmap" element={<HeatmapView />} />
              <Route path="/locations" element={<LocationsMap />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />

              {/* Redirect all unknown routes */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>

      <ToastNotification />
      <NotificationPoller />
    </div>
  );
}
