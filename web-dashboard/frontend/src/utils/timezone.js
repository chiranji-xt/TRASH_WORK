// Convert UTC timestamp string to IST localized, readable format
export function convertUTCtoIST(utcString) {
  if (!utcString) return "";
  const date = new Date(`${utcString}Z`); // force UTC interpretation
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour12: true,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Helper: get YYYY-MM-DD for IST day comparisons
export function getISTDateKey(utcString) {
  if (!utcString) return "";
  const date = new Date(`${utcString}Z`);
  return date.toLocaleString("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

// Short waiting-time label for dispatch priority, e.g. "3d 5h", "45m", "just now"
export function ageOf(utcString) {
  if (!utcString) return "—";
  const then = new Date(/Z$/.test(utcString) ? utcString : `${utcString}Z`).getTime();
  if (isNaN(then)) return "—";
  const mins = Math.max(0, Math.floor((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  const days = Math.floor(hours / 24);
  return days < 30 ? `${days}d ${hours % 24}h` : `${Math.floor(days / 30)}mo`;
}


