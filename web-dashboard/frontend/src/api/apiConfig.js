/**
 * API Configuration Module
 * Centralized configuration for API endpoints and settings.
 *
 * Backend URL comes from the VITE_API_URL environment variable —
 * never commit ngrok URLs. See frontend/.env.example.
 *   Local dev:  VITE_API_URL=http://localhost:8000
 *   ngrok:      VITE_API_URL=https://<your-subdomain>.ngrok-free.dev
 */

const fromEnv =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_URL) || "";

export const API_CONFIG = {
  BASE_URL: (fromEnv || "http://localhost:8000").replace(/\/$/, ""),
  REQUEST_TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000, // 1 second
  ENABLE_LOGGING: (typeof import.meta !== "undefined" && import.meta.env?.DEV) || false,
};

/** Admin API key (for PATCH /reports/{id}/status), stored after login. */
export function getAdminKey() {
  try {
    return localStorage.getItem("admin_api_key") || "";
  } catch {
    return "";
  }
}

export function setAdminKey(key) {
  try {
    if (key) localStorage.setItem("admin_api_key", key);
    else localStorage.removeItem("admin_api_key");
  } catch {
    /* storage unavailable */
  }
}

/**
 * API Endpoints
 */
export const API_ENDPOINTS = {
  HEALTH: "/health",
  REPORTS: "/reports",
  REPORT_BY_ID: (id) => `/reports/${id}`,
  REPORTS_IN_AREA: "/reports-in-area",
  REPORTS_BY_STATUS: (status) => `/reports/by-status/${status}`,
  STATS_SUMMARY: "/reports/stats/summary",
  STATS_HOTSPOTS: "/reports/stats/hotspots",
  UPLOAD_REPORT: "/upload-report",
  UPLOADS: (filename) => `/uploads/${filename}`,
};

/**
 * Get full URL for an endpoint
 */
export function getApiUrl(endpoint) {
  const baseUrl = API_CONFIG.BASE_URL.endsWith("/")
    ? API_CONFIG.BASE_URL.slice(0, -1)
    : API_CONFIG.BASE_URL;
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${baseUrl}${path}`;
}
