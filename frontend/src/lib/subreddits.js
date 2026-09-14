export const MAX_SUBREDDITS = 5;

export function normalizeSubredditName(value = '') {
  let normalized = value.trim();
  if (normalized.toLowerCase().startsWith('/r/')) normalized = normalized.slice(3);
  else if (normalized.toLowerCase().startsWith('r/')) normalized = normalized.slice(2);
  while (normalized.startsWith('/')) normalized = normalized.slice(1);
  while (normalized.endsWith('/')) normalized = normalized.slice(0, -1);
  return normalized;
}

export function sameSubreddit(left = '', right = '') {
  return left.localeCompare(right, undefined, { sensitivity: 'accent' }) === 0;
}

export function isInSubredditScope(item, selected = []) {
  return selected.length === 0 || selected.some((name) => sameSubreddit(item?.subreddit || '', name));
}

export function communityOptions(activity = []) {
  const communities = new Map();
  for (const item of activity) {
    const name = item.subreddit;
    if (!name) continue;
    const key = name.toLocaleLowerCase();
    const current = communities.get(key) || { name, count: 0 };
    current.count += 1;
    communities.set(key, current);
  }
  return [...communities.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

export function metricsFromFindings(findings = []) {
  const unique = new Map();
  for (const finding of findings) unique.set(`${finding.id}:${finding.category}`, finding);
  const values = [...unique.values()];
  const conduct = values.filter((finding) => finding.category === 'conduct');
  const bias = values.filter((finding) => finding.category === 'bias');
  const coordination = values.filter((finding) => finding.category === 'coordination');
  const hostility = Math.min(100, conduct.reduce((sum, finding) => sum + ((finding.level || 0) <= 1 ? 10 : 25), 0));
  const anger = Math.min(100, conduct.reduce((sum, finding) => sum + (finding.answers?.c5 ? 25 : 10), 0));
  const group_hatred = Math.min(100, bias.reduce((sum, finding) => sum + ((finding.level || 0) >= 3 ? 45 : 30), 0));
  const mobilization = Math.min(100, coordination.length * 30);
  const overall = Math.round(hostility * 0.45 + anger * 0.25 + group_hatred * 0.25 + mobilization * 0.05);
  return { overall, hostility, anger, group_hatred, mobilization };
}