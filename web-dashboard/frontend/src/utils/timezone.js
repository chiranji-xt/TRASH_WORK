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


