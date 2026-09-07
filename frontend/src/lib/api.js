const API_BASE = 'https://mod-vetting-api.onrender.com';

// Deliberately no per-subreddit rules/register-notes input -- the tool is
// "type a username, get a report." These generic defaults match the
// backend's own built-in rule set (server-side DEFAULT_RULES in
// mod_vetting/report.py), so the pipeline's actual behavior doesn't
// silently diverge from what's shown here.
const DEFAULT_RULES =
  'Harassment or personal attacks. Hate speech or slurs targeting a group. Threats of violence. ' +
  'Spam or repeated self-promotion. Doxxing or sharing private information. Ban evasion.';
const DEFAULT_REGISTER_NOTES = 'No subreddit-specific house style provided -- read literally.';

export async function startJob(username) {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      rules: DEFAULT_RULES,
      register_notes: DEFAULT_REGISTER_NOTES,
    }),
  });
  if (!res.ok) throw new Error(`Failed to start job (${res.status})`);
  return res.json(); // { job_id, status }
}

export async function pollJob(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job (${res.status})`);
  return res.json(); // { status, report, error }
}

/** Polls until the job leaves "running", calling onTick with each poll
 * for progress UI. Backend runs can take minutes -- dozens of
 * concurrency-capped LLM calls -- so this is a real wait, not a formality. */
export async function waitForJob(jobId, { intervalMs = 4000, timeoutMs = 6 * 60 * 1000, onTick } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const entry = await pollJob(jobId);
    onTick?.(entry, Date.now() - start);
    if (entry.status !== 'running') return entry;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error('Timed out waiting for the report (6 minutes).');
}
