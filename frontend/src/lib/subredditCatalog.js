import names from '../data/popularSubreddits.json';

export const POPULAR_SUBREDDITS = names.map((name, index) => ({ name, rank: index + 1 }));

export function findSubreddits(query = '', limit = 10) {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return POPULAR_SUBREDDITS.slice(0, limit);
  return POPULAR_SUBREDDITS
    .filter((item) => item.name.toLocaleLowerCase().includes(needle))
    .sort((left, right) => {
      const leftName = left.name.toLocaleLowerCase();
      const rightName = right.name.toLocaleLowerCase();
      const prefixDifference = Number(!leftName.startsWith(needle)) - Number(!rightName.startsWith(needle));
      return prefixDifference || left.rank - right.rank;
    })
    .slice(0, limit);
}