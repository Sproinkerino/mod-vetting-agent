self.addEventListener('push', (event) => {
  let message = { title: 'reddit-pi', body: 'Your report is ready.', url: '/' };
  try { message = { ...message, ...event.data.json() }; } catch {}
  event.waitUntil(self.registration.showNotification(message.title, {
    body: message.body, icon: '/favicon.svg', badge: '/favicon.svg',
    data: { url: message.url }, tag: 'reddit-pi-report',
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
    const existing = windows.find((window) => window.url.startsWith(self.location.origin));
    return existing ? existing.focus().then(() => existing.navigate(url)) : clients.openWindow(url);
  }));
});
