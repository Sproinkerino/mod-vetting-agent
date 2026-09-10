export function loadingComments(progress, limit = 6) {
  return (progress?.activity_preview || [])
    .filter((item) => item.type === 'comment' && item.body?.trim())
    .slice(0, limit);
}

export function previewComment(text, maxLength = 160) {
  const clean = (text || '').trim();
  return clean.length > maxLength ? `${clean.slice(0, maxLength).trimEnd()}…` : clean;
}