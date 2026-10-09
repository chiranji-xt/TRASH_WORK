import { useState, useEffect, useRef } from "react";
import { useLocation, Link } from "react-router-dom";
import { getNotifications, getUnreadCount, markAllAsRead } from "../data/notifications.js";
import eventBus from "../data/eventBus.js";
import { Icon, paths } from "./icons";

const SECTIONS = {
  "/": "Overview",
  "/reports": "Waste reports",
  "/heatmap": "Waste density",
  "/locations": "Zone map",
  "/settings": "Preferences",
};

export default function Navbar({ onMenu, onSearch }) {
  const { pathname } = useLocation();
  const [notifications, setNotifications] = useState(getNotifications());
  const [unreadCount, setUnreadCount] = useState(getUnreadCount());
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [query, setQuery] = useState("");
  const dropdownRef = useRef(null);

  const section = SECTIONS[pathname] || "Overview";
  const today = new Date().toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });

  useEffect(() => {
    const unsubscribe = eventBus.subscribe("new-notification", () => {
      setNotifications(getNotifications());
      setUnreadCount(getUnreadCount());
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) setIsDropdownOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleBellClick = () => {
    const next = !isDropdownOpen;
    setIsDropdownOpen(next);
    if (next && unreadCount > 0) {
      markAllAsRead();
      setUnreadCount(0);
      setNotifications(getNotifications());
    }
  };

  const formatTime = (timestamp) => {
    const diffMins = Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  const recentNotifications = notifications.slice(-8).reverse();

  return (
    <div className="mb-5 flex flex-wrap items-center gap-2.5">
      <button
        onClick={onMenu}
        aria-label="Open navigation"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink-soft lg:hidden"
      >
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>

      <p className="mr-auto hidden items-center gap-2 text-[13px] text-ink-mute sm:flex">
        <span className="font-semibold text-ink">Console</span>
        <span className="text-line">/</span>
        <span>{section}</span>
        <span className="ml-1 hidden items-center gap-1.5 rounded-full bg-forest px-2 py-0.5 text-[11px] font-bold text-civic-lime xl:inline-flex">
          <span className="h-1.5 w-1.5 rounded-full bg-civic-lime" /> Live
        </span>
      </p>

      <form
        className="order-5 flex w-full min-w-0 items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 transition focus-within:border-forest md:order-none md:w-auto md:max-w-[240px] md:flex-1"
        onSubmit={(e) => { e.preventDefault(); if (onSearch) onSearch(query); }}
        role="search"
      >
        <span className="shrink-0 text-ink-mute"><Icon d={paths.search} size={15} /></span>
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); if (onSearch) onSearch(e.target.value); }}
          type="text"
          placeholder="Search reports, locations, waste types..."
          aria-label="Search reports"
          className="w-full bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-mute/70"
        />
      </form>

      <span className="hidden items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-2 text-[13px] font-medium text-ink-soft xl:inline-flex">
        <Icon d={paths.calendar} size={14} /> {today}
      </span>

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={handleBellClick}
          aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
          aria-expanded={isDropdownOpen}
          className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-ink-soft transition hover:border-forest/40"
        >
          <Icon d={paths.bell} size={17} />
          {unreadCount > 0 && (
            <span className="tnum absolute -right-1 -top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-civic-coral px-1 text-[10px] font-bold text-white ring-2 ring-[#F7F6F0]">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
        {isDropdownOpen && (
          <div className="absolute right-0 z-50 mt-2 flex max-h-96 w-[calc(100vw-2rem)] max-w-80 flex-col overflow-hidden rounded-xl border border-line bg-white shadow-pop">
            <div className="border-b border-line/70 p-4">
              <h3 className="font-display text-[16px] font-semibold text-ink">Field alerts</h3>
              <p className="mt-0.5 text-xs text-ink-mute">{unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}</p>
            </div>
            <div className="inv-scroll flex-1 overflow-y-auto">
              {recentNotifications.length === 0 ? (
                <p className="p-6 text-center text-[13px] text-ink-mute">No alerts yet — new detections will land here.</p>
              ) : (
                  <div className="divide-y divide-[#EDEFE6]">
                  {recentNotifications.map((n) => (
                    <div key={n.id} className={`px-4 py-3 ${!n.read ? "bg-[#F4F6EC]" : ""}`}>
                      <p className="text-[13px] leading-snug text-ink">{n.message}</p>
                      <p className="mt-1 font-mono text-[11px] text-ink-mute">{formatTime(n.timestamp)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <Link to="/reports" className="inv-btn-primary !py-2">
        <Icon d={paths.send} size={15} /> New Dispatch
      </Link>
    </div>
  );
}
