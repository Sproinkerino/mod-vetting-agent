export function sourceText(source) {
  const title = (source?.title || '').trim();
  const body = (source?.body || '').trim();
  if (source?.type !== 'post') return body || title || 'Content unavailable.';
  if (title && body && title.toLocaleLowerCase() !== body.toLocaleLowerCase()) return `${title}\n${body}`;
  return title || body || 'Post content unavailable.';
}

export function sourceExcerpt(source, limit = 50) {
  const raw = sourceText(source).replace(/\s+/g, ' ').trim();
  return `${raw.slice(0, limit).trim()}${raw.length > limit ? '...' : ''}`;
}

export function sourceKind(source) {
  return source?.type === 'post' ? 'Post' : 'Comment';
}
