/**
 * API Configuration Module
 * Centralized configuration for API endpoints and settings
 */

export const API_CONFIG = {
  // NOTE: If using ngrok, update this URL every 2 hours. For local dev, use localhost:8000
  BASE_URL: "https://subtemporal-superdesirously-austin.ngrok-free.dev",
  REQUEST_TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000, // 1 second
  ENABLE_LOGGING: process.env.NODE_ENV === "development",
};

/**
 * API Endpoints
 */
export const API_ENDPOINTS = {
  HEALTH: "/health",
  REPORTS: "/reports",
  REPORT_BY_ID: (id) => `/reports/${id}`,
  REPORTS_IN_AREA: "/reports-in-area",
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



