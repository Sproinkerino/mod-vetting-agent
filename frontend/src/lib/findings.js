// Pure helpers for finding cards. The frontend renders report.json, it
// never computes/derives/adjusts a score or boolean (PRD §1 "Never") --
// but grouping raw findings by comment id for display, and asserting an
// offset actually lines up before trusting it, aren't derivations of new
// values; they're display bookkeeping and an integrity check.

/**
 * FR-C4: before highlighting, assert body.substr(offset, quote.length) ===
 * quote. A mismatch means the offset is untrustworthy -- render unhighlighted
 * and suppress the level rather than fabricate a highlight in the wrong place.
 */
export function validateQuoteOffset(body, quote, offset) {
  if (typeof body !== 'string' || typeof quote !== 'string' || typeof offset !== 'number') {
    return false;
  }
  return body.substr(offset, quote.length) === quote;
}

/**
 * FR-C5: findings sharing a source comment id render as one card with
 * multiple category tags, never one card per category. Groups the flat
 * findings[] array by id, preserving first-seen order.
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

/** FR-C7: the subsequent-replies block renders only when the card carries
 * a judgment finding. */
export function cardHasJudgmentFinding(categoryFindings) {
  return categoryFindings.some((f) => f.category === 'judgment');
}

export const BOOLEAN_GROUPS = {
  conduct: ['c1', 'c2', 'c3', 'c4', 'c5'],
  bias: ['b1', 'b2', 'b3', 'b4'],
  judgment: ['j1', 'j2', 'j3', 'j4'],
  coordination: ['co1', 'co2', 'co3', 'co4'],
  doxxing: ['d1', 'd2', 'd3'],
  self_description: ['s1'],
};

/** FR-C6: "the criterion that cleared it" -- the boolean(s) that had to
 * be true for this category's booleans to clear per scoring.py. Purely a
 * lookup table mirroring the backend's own scoring logic in prose, not a
 * re-derivation of the level itself. */
export const CLEARING_CRITERIA = {
  conduct: 'c1, c2, c3, and c4 all true',
  bias: 'b1, b2, and b3 all true',
  judgment: 'j1 and j2 both true',
  coordination: 'co1, co2, and co3 all true',
  doxxing: 'd1, d2, and d3 all true',
  self_description: 's1 true',
};
