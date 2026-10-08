// API Configuration
import { API_CONFIG } from "./apiConfig";

// API Configuration
const BASE_URL = API_CONFIG.BASE_URL;

// Request timeout (milliseconds)
const REQUEST_TIMEOUT = 30000; // 30 seconds

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// Authentication token (can be set via setAuthToken)
let authToken = null;

/**
 * Set authentication token for API requests
 * @param {string} token - Bearer token
 */
export function setAuthToken(token) {
  authToken = token;
}

/**
 * Clear authentication token
 */
export function clearAuthToken() {
  authToken = null;
}

/**
 * Create timeout promise
 */
function createTimeoutPromise(timeoutMs) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error(`Request timeout after ${timeoutMs}ms`)), timeoutMs);
  });
}

/**
 * Core API fetch wrapper with timeout, retry, and error handling
 */
async function apiFetch(url, options = {}, retryCount = 0) {
  const startTime = performance.now();

  // Build headers
  const headers = {
    "ngrok-skip-browser-warning": "true",
    ...options.headers,
  };

  // Add authentication if token exists
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  // Don't set Content-Type for FormData (browser will set it with boundary)
  if (!(options.body instanceof FormData)) {
    if (!headers["Content-Type"] && options.method !== "GET") {
      headers["Content-Type"] = "application/json";
    }
  }

  const fetchOptions = {
    ...options,
    headers,
  };

  try {
    // Race between fetch and timeout
    const response = await Promise.race([
      fetch(url, fetchOptions),
      createTimeoutPromise(REQUEST_TIMEOUT),
    ]);

    const latency = performance.now() - startTime;

    // Handle non-OK responses
    if (!response.ok) {
      // Handle authentication errors
      if (response.status === 401 || response.status === 403) {
        clearAuthToken();
        throw new Error(`Authentication failed: ${response.statusText}`);
      }

      // Try to parse error message
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } else {
          const errorText = await response.text();
          if (errorText) errorMessage = errorText;
        }
      } catch (e) {
        // Ignore parsing errors, use default message
      }

      // Retry on server errors (5xx) or network issues
      if ((response.status >= 500 || response.status === 429) && retryCount < MAX_RETRIES) {
        const delay = RETRY_DELAY * Math.pow(2, retryCount); // Exponential backoff
        console.warn(`Retrying request (${retryCount + 1}/${MAX_RETRIES}) after ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return apiFetch(url, options, retryCount + 1);
      }

      throw new Error(errorMessage);
    }

    // Parse response
    const contentType = response.headers.get("content-type");
    let data;

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      // Handle non-JSON responses (e.g., plain text, images)
      data = await response.text();
    }

    // Log successful request
    if (process.env.NODE_ENV === "development") {
      console.log(`[API] ${options.method || "GET"} ${url} - ${response.status} (${latency.toFixed(0)}ms)`);
    }

    return { data, latency, status: response.status };
  } catch (error) {
    const latency = performance.now() - startTime;

    // Retry on network errors
    if (
      (error.message.includes("timeout") ||
        error.message.includes("Failed to fetch") ||
        error.message.includes("NetworkError")) &&
      retryCount < MAX_RETRIES
    ) {
      const delay = RETRY_DELAY * Math.pow(2, retryCount);
      console.warn(`Retrying request (${retryCount + 1}/${MAX_RETRIES}) after ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      return apiFetch(url, options, retryCount + 1);
    }

    // Log error
    console.error(`[API Error] ${options.method || "GET"} ${url} - ${error.message} (${latency.toFixed(0)}ms)`);
    throw error;
  }
}

/**
 * Normalize report data to ensure consistent structure
 */
function normalizeReport(report) {
  if (!report) return null;

  const latitude =
    report.latitude != null
      ? Number(report.latitude)
      : report.lat != null
        ? Number(report.lat)
        : null;

  const longitude =
    report.longitude != null
      ? Number(report.longitude)
      : report.lon != null
        ? Number(report.lon)
        : null;

  const prediction =
    report.prediction ||
    report.waste_class ||
    report.predicted_class ||
    report.class ||
    null;

  const createdAt = report.created_at || report.timestamp || null;

  return {
    id: report.id,
    latitude,
    longitude,
    lat: latitude,
    lon: longitude,
    waste_class: prediction,
    prediction,
    status: report.status || null,
    timestamp: createdAt,
    created_at: createdAt,
    location_name: report.location_name || report.locationName || null,
    confidence: report.confidence != null ? Number(report.confidence) : null,
    image_path: report.image_path || report.imagePath || null,
    boxed_image_path: report.boxed_image_path || report.boxedImagePath || null,
    // Preserve any additional fields
    ...Object.fromEntries(
      Object.entries(report).filter(([key]) =>
        ![
          "latitude",
          "lat",
          "longitude",
          "lon",
          "prediction",
          "waste_class",
          "predicted_class",
          "class",
          "created_at",
          "timestamp",
          "location_name",
          "locationName",
          "image_path",
          "imagePath",
          "boxed_image_path",
          "boxedImagePath"
        ].includes(key)
      )
    ),
  };
}

/**
 * Normalize array of reports
 */
function normalizeReports(reports) {
  if (!Array.isArray(reports)) return [];
  return reports.map(normalizeReport).filter(Boolean);
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * Check API health and connectivity
 * @returns {Promise<{status: string, latency: number, available: boolean}>}
 */
export async function checkHealth() {
  try {
    const startTime = performance.now();
    const result = await apiFetch(`${BASE_URL}/health`, {
      method: "GET",
    });

    const latency = performance.now() - startTime;
    const available = result.status === 200;

    const healthInfo = {
      status: available ? "healthy" : "unhealthy",
      latency: Math.round(latency),
      available,
      timestamp: new Date().toISOString(),
    };

    console.log("[API Health]", healthInfo);
    return healthInfo;
  } catch (error) {
    const healthInfo = {
      status: "unreachable",
      latency: null,
      available: false,
      error: error.message,
      timestamp: new Date().toISOString(),
    };

    console.error("[API Health]", healthInfo);
    return healthInfo;
  }
}

/**
 * Fetch all reports
 * @returns {Promise<Array>} Normalized array of reports
 */
export async function fetchAllReports() {
  try {
    const result = await apiFetch(`${BASE_URL}/reports?_t=${Date.now()}`, {
      method: "GET",
    });

    return normalizeReports(result.data || []);
  } catch (error) {
    console.error("Failed to fetch reports:", error);
    throw new Error(`Failed to fetch reports: ${error.message}`);
  }
}

/**
 * Fetch report by ID
 * @param {number|string} id - Report ID
 * @returns {Promise<Object>} Normalized report object
 */
export async function fetchReportById(id) {
  if (!id) {
    throw new Error("Report ID is required");
  }

  try {
    const result = await apiFetch(`${BASE_URL}/reports/${id}`, {
      method: "GET",
    });

    return normalizeReport(result.data);
  } catch (error) {
    console.error(`Failed to fetch report ${id}:`, error);
    throw new Error(`Failed to fetch report ${id}: ${error.message}`);
  }
}

/**
 * Fetch reports by status
 * @param {string} status - Status to filter by (e.g. "Pending", "Cleaned")
 * @returns {Promise<Array>} Normalized array of reports
 */
export async function fetchReportsByStatus(status) {
  if (!status) return fetchAllReports();

  try {
    // The backend endpoint takes the status directly in the path
    const result = await apiFetch(`${BASE_URL}/detections/by-status/${status}`, {
      method: "GET",
    });

    return normalizeReports(result.data || []);
  } catch (error) {
    console.error(`Failed to fetch reports with status ${status}:`, error);
    throw new Error(`Failed to fetch reports: ${error.message}`);
  }
}

/**
 * Fetch reports in area (bounding box)
 * @param {Object} bbox - Bounding box object
 * @param {number} bbox.minLat - Minimum latitude
 * @param {number} bbox.minLon - Minimum longitude
 * @param {number} bbox.maxLat - Maximum latitude
 * @param {number} bbox.maxLon - Maximum longitude
 * @returns {Promise<Array>} Normalized array of reports
 */
export async function fetchReportsInArea(bbox) {
  const { minLat, minLon, maxLat, maxLon } = bbox || {};

  // Validate bounding box
  if (
    minLat == null ||
    minLon == null ||
    maxLat == null ||
    maxLon == null ||
    isNaN(minLat) ||
    isNaN(minLon) ||
    isNaN(maxLat) ||
    isNaN(maxLon)
  ) {
    throw new Error("Invalid bounding box: minLat, minLon, maxLat, maxLon are required");
  }

  try {
    // Build query string
    const params = new URLSearchParams({
      min_lat: String(minLat),
      min_lon: String(minLon),
      max_lat: String(maxLat),
      max_lon: String(maxLon),
    });

    const result = await apiFetch(`${BASE_URL}/reports-in-area?${params.toString()}`, {
      method: "GET",
    });

    return normalizeReports(result.data || []);
  } catch (error) {
    console.error("Failed to fetch reports in area:", error);
    throw new Error(`Failed to fetch reports in area: ${error.message}`);
  }
}

/**
 * Upload report
 * @param {FormData} formData - FormData containing image and metadata
 * @returns {Promise<Object>} Normalized report object
 */
export async function uploadReport(formData) {
  if (!formData || !(formData instanceof FormData)) {
    throw new Error("FormData is required for upload");
  }

  try {
    const result = await apiFetch(`${BASE_URL}/upload-report`, {
      method: "POST",
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary for FormData
    });

    return normalizeReport(result.data);
  } catch (error) {
    console.error("Failed to upload report:", error);
    throw new Error(`Failed to upload report: ${error.message}`);
  }
}

/**
 * Get image URL from image path
 * Handles various URL formats:
 * - Absolute URLs (http/https)
 * - Relative paths with leading slash (/uploads/file.jpg)
 * - Relative paths without leading slash (uploads/file.jpg)
 * @param {string} imagePath - Image path from API
 * @returns {string|null} Full image URL or null if invalid
 */
export function getImageUrl(imagePath) {
  if (!imagePath || typeof imagePath !== "string") {
    return null;
  }

  // Already an absolute URL
  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    return imagePath;
  }

  // Ensure BASE_URL doesn't have trailing slash
  const baseUrl = BASE_URL.endsWith("/") ? BASE_URL.slice(0, -1) : BASE_URL;

  // Ensure imagePath starts with slash
  const path = imagePath.startsWith("/") ? imagePath : `/${imagePath}`;

  return `${baseUrl}${path}`;
}

/**
 * Update report status
 * @param {number|string} id - Report ID
 * @param {string} status - New status
 * @returns {Promise<Object>} Normalized report object
 */
export async function updateReportStatus(id, status) {
  try {
    const url = `${BASE_URL}/reports/${id}/status?status=${encodeURIComponent(status)}`;
    const result = await apiFetch(url, {
      method: "PATCH",
    });

    return normalizeReport(result.data);
  } catch (error) {
    console.error(`Failed to update report status ${id}:`, error);
    throw new Error(`Failed to update report status: ${error.message}`);
  }
}

/**
 * Get API base URL
 * @returns {string}
 */
export function getBaseUrl() {
  return BASE_URL;
}
