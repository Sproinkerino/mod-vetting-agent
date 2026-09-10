export function redditBlockquote(body, limit = 50) {
  const raw = body || 'Comment text unavailable.';
  const excerpt = `${raw.slice(0, limit).trim()}${raw.length > limit ? '...' : ''}`;
  return excerpt.split(/\r?\n/).map((line) => line ? `> ${line}` : '>').join('\n');
}

export function buildRedditShareText({ sources, answer, origin }) {
  const selected = sources.slice(0, 3);
  const quotes = selected.map((source) => redditBlockquote(source.body)).join('\n\n');
  const links = selected.map((source) => `[Source](${source.permalink})`).join('\n');
  return [quotes, answer.trim(), links, `[reddit-pi](${origin})`].filter(Boolean).join('\n\n');
}
