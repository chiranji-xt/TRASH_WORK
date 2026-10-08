import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import eventBus from "../data/eventBus.js";

export default function ToastNotification() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const unsubscribe = eventBus.subscribe("new-notification", (notification) => {
      // Add toast
      setToasts((prev) => [...prev, notification]);

      // Auto-dismiss after 4 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== notification.id));
      }, 4000);
    });

    return unsubscribe;
  }, []);

  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="bg-gray-800 border border-gray-700 text-white px-4 py-3 rounded-lg shadow-lg min-w-[300px] max-w-md animate-slide-in-right"
          style={{
            animation: "slideInRight 0.3s ease-out",
          }}
        >
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              <span className="text-green-400 text-xl">🔔</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{toast.message}</p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(toast.timestamp).toLocaleTimeString()}
              </p>
            </div>
            <button
              onClick={() => {
                setToasts((prev) => prev.filter((t) => t.id !== toast.id));
              }}
              className="flex-shrink-0 text-gray-400 hover:text-white transition"
            >
              ×
            </button>
          </div>
        </div>
      ))}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>,
    document.body
  );
}

