import { useState, useEffect, useRef } from "react";
import { getNotifications, getUnreadCount, markAllAsRead } from "../data/notifications.js";
import eventBus from "../data/eventBus.js";

export default function Navbar() {
  const [notifications, setNotifications] = useState(getNotifications());
  const [unreadCount, setUnreadCount] = useState(getUnreadCount());
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Update notifications when new ones arrive
  useEffect(() => {
    const unsubscribe = eventBus.subscribe("new-notification", () => {
      setNotifications(getNotifications());
      setUnreadCount(getUnreadCount());
    });

    return unsubscribe;
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleBellClick = () => {
    setIsDropdownOpen(!isDropdownOpen);
    if (!isDropdownOpen && unreadCount > 0) {
      markAllAsRead();
      setUnreadCount(0);
      setNotifications(getNotifications());
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const recentNotifications = notifications.slice(-10).reverse();

  return (
    <header className="flex items-center justify-between mb-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-gray-500">
          Overview
        </p>
        <h1 className="text-2xl md:text-3xl font-semibold mt-1 text-white">
          City Cleanliness Dashboard
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-2 px-3 py-2 rounded-full bg-gray-800 border border-gray-700 shadow-sm">
          <span className="text-gray-400 text-sm">⌘K</span>
          <input
            type="text"
            placeholder="Search reports, areas..."
            className="bg-transparent text-sm outline-none placeholder:text-gray-400 w-40 text-white"
          />
        </div>

        {/* Notification Bell */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={handleBellClick}
            className="relative h-9 w-9 rounded-full bg-gray-800 border border-gray-700 shadow-sm flex items-center justify-center text-white hover:bg-gray-700 transition"
          >
            <span className="text-lg">🔔</span>
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown */}
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 max-h-96 overflow-hidden flex flex-col">
              <div className="p-4 border-b border-gray-700">
                <h3 className="text-white font-semibold">Notifications</h3>
                <p className="text-gray-400 text-xs mt-1">
                  {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
                </p>
              </div>

              <div className="overflow-y-auto flex-1">
                {recentNotifications.length === 0 ? (
                  <div className="p-4 text-center text-gray-400 text-sm">
                    No notifications yet
                  </div>
                ) : (
                  <div className="divide-y divide-gray-700">
                    {recentNotifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-4 hover:bg-gray-750 transition ${
                          !notification.read ? "bg-gray-750/50" : ""
                        }`}
                      >
                        <p className="text-white text-sm">{notification.message}</p>
                        <p className="text-gray-400 text-xs mt-1">
                          {formatTime(notification.timestamp)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {recentNotifications.length > 0 && (
                <div className="p-2 border-t border-gray-700">
                  <button
                    onClick={() => {
                      markAllAsRead();
                      setUnreadCount(0);
                      setNotifications(getNotifications());
                    }}
                    className="w-full text-xs text-blue-400 hover:text-blue-300 py-2"
                  >
                    Mark all as read
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <button className="relative h-9 w-9 rounded-full bg-gray-800 border border-gray-700 shadow-sm flex items-center justify-center text-sm font-medium text-white hover:bg-gray-700 transition">
          M
        </button>
      </div>
    </header>
  );
}
