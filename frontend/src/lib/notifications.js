import { notificationConfigRequest, subscribeJobNotification } from './api';

export async function notificationConfig() {
  return notificationConfigRequest();
}

function decodeKey(value) {
  const padding = '='.repeat((4 - value.length % 4) % 4);
  const binary = atob((value + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

export async function enableJobNotification(jobId) {
  if (!jobId) throw new Error('The report has not started yet.');
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new Error('Notifications were not enabled.');
  const config = await notificationConfig();
  if (!config.enabled) throw new Error('Notifications are not available right now.');
  const registration = await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true, applicationServerKey: decodeKey(config.public_key),
    });
  }
  await subscribeJobNotification(jobId, subscription.toJSON());
}
