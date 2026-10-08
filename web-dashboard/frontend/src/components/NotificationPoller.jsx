import { useEffect, useRef } from "react";
import { fetchAllReports } from "../api/reportsApi";
import { addNotification } from "../data/notifications";
import eventBus from "../data/eventBus";

export default function NotificationPoller() {
    // We do NOT use the global slow refresh context here.
    // We want notifications to be snappy (e.g. every 5 seconds).

    // Track the ID of the last report we've "seen"
    // Initialize with null so we don't blast notifications on first load
    const lastSeenIdRef = useRef(null);
    const firstLoadRef = useRef(true);

    useEffect(() => {
        const checkForNewReports = async () => {
            try {
                // Use a lightweight fetch if possible, or just fetch all (assuming pagination isn't huge yet)
                const reports = await fetchAllReports();

                if (!reports || reports.length === 0) return;

                // Ensure strict numeric comparison for IDs
                // Sort by ID descending (newest first)
                const sortedReports = [...reports].sort((a, b) => Number(b.id) - Number(a.id));
                const latestReport = sortedReports[0];
                const latestId = Number(latestReport.id);

                // logging for debug
                // console.log(`[NotificationPoller] Checking... Latest: ${latestId}, Seen: ${lastSeenIdRef.current}`);

                // First load: just sync the ID, don't notify
                if (firstLoadRef.current) {
                    console.log("[NotificationPoller] Initialized. Latest ID:", latestId);
                    lastSeenIdRef.current = latestId;
                    firstLoadRef.current = false;
                    return;
                }

                // Subsequent loads: check if we have newer items
                if (lastSeenIdRef.current !== null && latestId > lastSeenIdRef.current) {

                    // Find ALL new reports
                    const newReports = sortedReports.filter(r => Number(r.id) > lastSeenIdRef.current);

                    console.log(`[NotificationPoller] Found ${newReports.length} new reports`);

                    newReports.forEach(report => {
                        const wasteClass = report.prediction || report.waste_class || "Waste";
                        const location = report.location_name || "Unknown Location";

                        // 1. Add to notification store
                        const notif = addNotification(`New report: ${wasteClass} detected at ${location}`);

                        // 2. Emit notification event (Navbar, Toast)
                        eventBus.emit("new-notification", notif);
                    });

                    // 3. Update last seen
                    lastSeenIdRef.current = latestId;

                    // 4. Emit general 'new-report' event so maps refresh immediately
                    eventBus.emit("new-report", newReports);
                }

            } catch (err) {
                console.error("[NotificationPoller] Failed to check for updates:", err);
            }
        };

        // Run immediately on mount
        checkForNewReports();

        // Set up a dedicated 5-second polling interval
        const intervalId = setInterval(checkForNewReports, 5000);

        return () => clearInterval(intervalId);
    }, []); // Empty dependency array = runs once on mount + interval

    return null; // Headless component
}
