export function loadingActivity(progress, limit = 6) {
  return (progress?.activity_preview || [])
    .filter((item) => ['comment', 'post'].includes(item.type) && (item.body?.trim() || item.title?.trim()))
    .slice(0, limit);
}
