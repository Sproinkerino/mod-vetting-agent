export function redditBlockquote(body, limit = 50) {
  const raw = body || 'Comment text unavailable.';
  const excerpt = `${raw.slice(0, limit).trim()}${raw.length > limit ? '...' : ''}`;
  return excerpt.split(/\r?\n/).map((line) => line ? `> ${line}` : '>').join('\n');
}

export function buildRedditShareText({ sources, opener = '', answer = '', origin }) {
  const selected = sources.slice(0, 3);
  const receipts = selected.map((source) => `${redditBlockquote(source.body)}\n[Source](${source.permalink})`).join('\n\n');
  return [opener.trim(), receipts, answer.trim(), `[reddit-pi](${origin})`].filter(Boolean).join('\n\n');
}
