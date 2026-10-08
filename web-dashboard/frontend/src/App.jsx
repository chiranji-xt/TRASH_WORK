import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

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

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />;
  }

  return (
    <div className="flex bg-gray-900 min-h-screen">
      {/* SIDEBAR ALWAYS VISIBLE */}
      <Sidebar />

      {/* MAIN CONTENT */}
      <div className="flex-1 bg-gray-900 min-h-screen">
        {/* NAVBAR */}
        <div className="p-6 pb-0">
          <Navbar />
        </div>

        {/* PAGE CONTENT */}
        <div className="p-6 pt-4">
          <Routes>
            <Route path="/" element={<DashboardHome />} />
            <Route path="/heatmap" element={<HeatmapView />} />
            <Route path="/locations" element={<LocationsMap />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />

            {/* Redirect all unknown routes */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>

      {/* TOAST NOTIFICATIONS */}
      <ToastNotification />
      <NotificationPoller />
    </div>
  );
}
