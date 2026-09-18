import { abortableDelay, throwIfAborted } from './polling';

// Local development talks to the local API; production defaults to Render.
// VITE_API_BASE can override either environment explicitly.
const API_BASE = import.meta.env.VITE_API_BASE || (
  import.meta.env.DEV ? 'http://127.0.0.1:8000' : 'https://mod-vetting-api.onrender.com'
);

// Deliberately no per-subreddit rules/register-notes input -- the tool is
// "type a username, get a report." These generic defaults match the
// backend's own built-in rule set (server-side DEFAULT_RULES in
// mod_vetting/report.py), so the pipeline's actual behavior doesn't
// silently diverge from what's shown here.
const DEFAULT_RULES =
  'Harassment or personal attacks. Hate speech or slurs targeting a group. Threats of violence. ' +
  'Spam or repeated self-promotion. Doxxing or sharing private information. Ban evasion.';
const DEFAULT_REGISTER_NOTES = 'No subreddit-specific house style provided -- read literally.';

export async function startJob(target, subreddits = [], discoverCommunities = false) {
  const isUrl = /^https?:\/\//i.test(target);
  const res = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...(isUrl ? { url: target } : { username: target }),
      rules: DEFAULT_RULES,
      register_notes: DEFAULT_REGISTER_NOTES,
      subreddits,
      discover_communities: discoverCommunities,
    }),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || `Failed to start job (${res.status})`);
  }
  return res.json(); // { job_id, status }
}

export async function pollJob(jobId, { signal } = {}) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, { signal });
  if (!res.ok) throw new Error(`Failed to fetch job (${res.status})`);
  return res.json(); // { status, report, error }
}

export async function askArchive(jobId, question, report, sourceCount = 1, subreddits = []) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      username: report?.applicant?.username,
      activity: report?.activity || [],
      source_count: sourceCount,
      subreddits,
    }),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || `Could not ask the archive (${res.status})`);
  }
  return res.json();
}

export async function cancelJob(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error(`Could not cancel job (${res.status})`);
  return res.json();
}
export async function compileToxicArchive(report, subreddits = []) {
  const res = await fetch(`${API_BASE}/jobs/${report.api_job_id}/compile-toxic`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: report.applicant.username, activity: report.activity || [], subreddits }),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || 'Could not compile the receipts.');
  }
  return res.json();
}

/** Polls until the job leaves "running", calling onTick with each poll
 * for progress UI. Backend runs can take minutes -- dozens of
 * concurrency-capped LLM calls -- so this is a real wait, not a formality. */
export async function waitForJob(jobId, { intervalMs = 4000, timeoutMs = 6 * 60 * 1000, onTick, signal } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    throwIfAborted(signal);
    const entry = await pollJob(jobId, { signal });
    onTick?.(entry, Date.now() - start);
    if (entry.status !== 'running') return entry;
    await abortableDelay(intervalMs, signal);
  }
  throw new Error('Timed out waiting for the report (6 minutes).');
}
export async function notificationConfigRequest() {
  const res = await fetch(`${API_BASE}/notifications/config`);
  if (!res.ok) throw new Error('Notifications are unavailable.');
  return res.json();
}

export async function subscribeJobNotification(jobId, subscription) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/notifications`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(subscription),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || 'Could not enable notifications.');
  }
  return res.json();
}

async function subredditRequest(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error('Could not load communities (' + res.status + ')');
  const payload = await res.json();
  return payload.items || [];
}

export function fetchPopularSubreddits() {
  return subredditRequest('/subreddits/popular');
}

export function suggestSubreddits(query) {
  return subredditRequest('/subreddits/suggest?q=' + encodeURIComponent(query));
}
