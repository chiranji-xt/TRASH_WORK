import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import eventBus from "../data/eventBus.js";

export default function ToastNotification() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const unsubscribe = eventBus.subscribe("new-notification", (notification) => {
      setToasts((prev) => [...prev, notification]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== notification.id));
      }, 4000);
    });
    return unsubscribe;
  }, []);

  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed right-4 top-4 z-[60] w-[calc(100vw-2rem)] max-w-sm space-y-2">
      {toasts.map((toast) => (
        <div key={toast.id} role="status" className="flex items-start gap-3 rounded-xl border border-line bg-white p-3.5 shadow-pop">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-forest text-[13px] font-bold text-civic-lime">◈</span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold leading-snug text-ink">{toast.message}</p>
            <p className="mt-0.5 font-mono text-[11px] text-ink-mute">{new Date(toast.timestamp).toLocaleTimeString()}</p>
          </div>
          <button
            onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
            aria-label="Dismiss notification"
            className="shrink-0 rounded-md p-1 text-ink-mute transition hover:bg-[#F4F2E9] hover:text-ink"
          >
            ×
          </button>
        </div>
      ))}
    </div>,
    document.body
  );
}
