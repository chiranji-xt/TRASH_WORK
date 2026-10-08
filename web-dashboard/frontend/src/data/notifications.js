// Global notifications store
let notifications = [];
let notificationIdCounter = 1;

// Add a new notification
export function addNotification(message) {
  const notification = {
    id: notificationIdCounter++,
    message,
    timestamp: Date.now(),
    read: false
  };
  notifications.push(notification);
  return notification;
}

// Get all notifications
export function getNotifications() {
  return [...notifications];
}

// Get unread count
export function getUnreadCount() {
  return notifications.filter(n => !n.read).length;
}

// Mark all as read
export function markAllAsRead() {
  notifications.forEach(n => n.read = true);
}

// Mark specific notification as read
export function markAsRead(id) {
  const notification = notifications.find(n => n.id === id);
  if (notification) {
    notification.read = true;
  }
}

// Clear all notifications
export function clearNotifications() {
  notifications = [];
}

// Get recent notifications (last N)
export function getRecentNotifications(limit = 10) {
  return [...notifications].reverse().slice(0, limit);
}



