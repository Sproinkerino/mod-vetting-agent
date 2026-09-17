import { useEffect, useState } from 'react';
import { enableJobNotification, notificationConfig } from '../lib/notifications';

export default function LoadingOptions({ jobId }) {
  const [state, setState] = useState({ checking: true, pushEnabled: false, message: '' });
  useEffect(() => {
    let live = true;
    fetchNotificationAvailability().then((value) => live && setState((s) => ({ ...s, checking: false, pushEnabled: value })));
    return () => { live = false; };
  }, []);
  async function notify() {
    setState((s) => ({ ...s, message: 'Turning on notifications…' }));
    try {
      await enableJobNotification(jobId);
      setState((s) => ({ ...s, message: 'We’ll notify this device when the report is ready.' }));
    } catch (error) {
      setState((s) => ({ ...s, message: error.message }));
    }
  }
  async function install() {
    const prompt = window.redditPiInstallPrompt;
    if (prompt) {
      await prompt.prompt();
      window.redditPiInstallPrompt = null;
      setState((s) => ({ ...s, message: 'Home Screen prompt opened.' }));
    } else {
      setState((s) => ({ ...s, message: /iPhone|iPad|iPod/.test(navigator.userAgent)
        ? 'On iPhone: tap Share, then Add to Home Screen. Open reddit-pi there to enable alerts.'
        : 'Open your browser menu and choose Install app or Add to Home screen.' }));
    }
  }
  return <div className="loading-options" aria-label="Keep track of this report">
    {!state.checking && state.pushEnabled && jobId && <button type="button" onClick={notify}>🔔 Notify me when ready</button>}
    <button type="button" onClick={install}>＋ Save to Home Screen</button>
    {state.message && <p role="status">{state.message}</p>}
  </div>;
}

async function fetchNotificationAvailability() {
  try {
    const config = await notificationConfig();
    return config.enabled && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  } catch {
    return false;
  }
}
