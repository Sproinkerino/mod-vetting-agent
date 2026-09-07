// Pure helpers for finding cards.

/**
 * Before highlighting a quote inside a comment body, assert
 * body.substr(offset, quote.length) === quote. A mismatch means the
 * offset is untrustworthy -- render unhighlighted and suppress the level
 * rather than fabricate a highlight in the wrong place.
 */
export function validateQuoteOffset(body, quote, offset) {
  if (typeof body !== 'string' || typeof quote !== 'string' || typeof offset !== 'number') {
    return false;
  }
  return body.substr(offset, quote.length) === quote;
}

/**
 * Findings sharing a source comment id render as one card with multiple
 * category tags, never one card per category. Groups the flat findings[]
 * array by id, preserving first-seen order.
 */
export function groupFindingsById(findings) {
  const order = [];
  const byId = new Map();
  for (const f of findings) {
    if (!byId.has(f.id)) {
      byId.set(f.id, []);
      order.push(f.id);
    }
    byId.get(f.id).push(f);
  }
  return order.map((id) => ({ id, categoryFindings: byId.get(id) }));
}

/** The subsequent-replies block renders only when the card carries a
 * judgment finding. */
export function cardHasJudgmentFinding(categoryFindings) {
  return categoryFindings.some((f) => f.category === 'judgment');
}
