// Utility function to trigger notifications after successful uploads
import { addNotification } from "../data/notifications.js";
import eventBus from "../data/eventBus.js";

/**
 * Trigger notification after successful report upload
 * @param {Object} report - Normalized report object from API
 */
export function triggerUploadNotification(report) {
  if (!report) {
    console.warn("triggerUploadNotification called with null/undefined report");
    return;
  }

  const location = report.location_name || "Unknown location";
  const wasteClass = report.waste_class || "Unknown";
  const message = `New report received at ${location} — Class: ${wasteClass}`;
  
  const notification = addNotification(message);
  eventBus.emit("new-notification", notification);
  eventBus.emit("new-report", report);
}

