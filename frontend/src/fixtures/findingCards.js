// Hand-written fixtures per the PRD (§7 M1): "The fixtures are the
// renderer's test set for the life of the project." All content is
// fabricated for testing -- no real usernames, no real people.
//
// Six cases, matching the M1 acceptance criteria exactly:
//   1. multiCategory   -- two categories on one comment id, mixed true/false/unknown booleans
//   2. topLevel         -- parent_body is null
//   3. judgmentWithReplies -- j1-j4 answered against real replies, including a correction
//   4. corruptedOffset  -- quote_offset does not match body.substr(offset, quote.length)
//   5. doxxing          -- binary hard-fail category, level is null (not graduated)
//   6. coordination     -- exercises co1-co4, another true/false/unknown mix
//
// quote_offset is computed from body.indexOf(quote) at load time (via
// withOffset below) rather than hand-typed -- hand-typed offsets on the
// first pass of this file were ALL wrong (verified with a script before
// this fix landed), which would have made every "should be valid" card
// render as a corrupted-offset error. Computing it removes that whole
// class of mistake. corruptedOffset is the one deliberate exception.

function withOffset(entry) {
  const offset = entry.body.indexOf(entry.quote);
  if (offset === -1) {
    throw new Error(`fixture error: quote not found verbatim in body for id ${entry.id}/${entry.category}`);
  }
  return { ...entry, quote_offset: offset };
}

export const multiCategory = [
  withOffset({
    id: 'fx_multi',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/abc123/thread/fx_multi/',
    created_utc: 1735689600,
    subreddit: 'fakesubreddit',
    quote: "you people are all the same, can't trust any of you",
    category: 'bias',
    level: 2,
    answers: {
      c1: true, c2: true, c3: true, c4: true, c5: null,
      b1: true, b2: true, b3: true, b4: false,
      j1: false, j2: null, j3: null, j4: null,
      co1: false, co2: null, co3: null, co4: null,
      d1: false, d2: null, d3: null,
      s1: false,
    },
    context_note: 'Parent comment was a general complaint about a moderation decision, not directed at any individual.',
    register_note: null,
    body:
      "Honestly at this point you people are all the same, can't trust any of you to run this sub fairly. " +
      'The rules only ever seem to get enforced one direction.',
    parent_body: 'The mods removed my post again without explanation.',
    replies: [],
  }),
  withOffset({
    id: 'fx_multi',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/abc123/thread/fx_multi/',
    created_utc: 1735689600,
    subreddit: 'fakesubreddit',
    quote: "you people are all the same, can't trust any of you",
    category: 'conduct',
    level: 1,
    answers: {
      c1: true, c2: true, c3: true, c4: true, c5: false,
      b1: true, b2: true, b3: true, b4: false,
      j1: false, j2: null, j3: null, j4: null,
      co1: false, co2: null, co3: null, co4: null,
      d1: false, d2: null, d3: null,
      s1: false,
    },
    context_note: 'Parent comment was a general complaint about a moderation decision, not directed at any individual.',
    register_note: null,
    body:
      "Honestly at this point you people are all the same, can't trust any of you to run this sub fairly. " +
      'The rules only ever seem to get enforced one direction.',
    parent_body: 'The mods removed my post again without explanation.',
    replies: [],
  }),
];

export const topLevel = [
  withOffset({
    id: 'fx_toplevel',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/def456/thread/',
    created_utc: 1733097600,
    subreddit: 'fakesubreddit',
    quote: 'I work as a licensed electrician',
    category: 'self_description',
    level: null,
    answers: {
      c1: false, c2: null, c3: true, c4: true, c5: null,
      b1: false, b2: null, b3: null, b4: null,
      j1: false, j2: null, j3: null, j4: null,
      co1: false, co2: null, co3: null, co4: null,
      d1: false, d2: null, d3: null,
      s1: true,
    },
    context_note: null,
    register_note: null,
    body: 'For context, I work as a licensed electrician, so take my read on the wiring question for what it is worth.',
    parent_body: null,
    replies: [],
  }),
];

export const judgmentWithReplies = [
  withOffset({
    id: 'fx_judgment',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/ghi789/thread/fx_judgment/',
    created_utc: 1731110400,
    subreddit: 'fakesubreddit',
    quote: 'Reposting within 24 hours has never been against the rules here',
    category: 'judgment',
    level: 4,
    answers: {
      c1: false, c2: null, c3: true, c4: true, c5: null,
      b1: false, b2: null, b3: null, b4: null,
      j1: true, j2: true, j3: true, j4: true,
      co1: false, co2: null, co3: null, co4: null,
      d1: false, d2: null, d3: null,
      s1: false,
    },
    context_note: 'Rule 4 explicitly states a 48-hour repost window.',
    register_note: null,
    body: 'Reposting within 24 hours has never been against the rules here, people just like to complain.',
    parent_body: 'Why did you repost this again so soon after the last one got removed?',
    replies: [
      { id: 'r1', author: 'fake_mod_account', body: "Rule 4 says 48 hours, not 24 -- that's why it was removed." },
      { id: 'r2', author: 'fx_judgment_author', body: "Still think 24 hours should be fine, I'm not changing my repost habits." },
    ],
  }),
];

export const corruptedOffset = [
  {
    id: 'fx_corrupted',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/jkl012/thread/fx_corrupted/',
    created_utc: 1728432000,
    subreddit: 'fakesubreddit',
    quote: 'this is a deliberately wrong quote span',
    quote_offset: 999, // intentionally out of range / mismatched -- see FR-C4. NOT run through withOffset.
    category: 'conduct',
    level: 3,
    answers: {
      c1: true, c2: true, c3: true, c4: true, c5: true,
      b1: false, b2: null, b3: null, b4: null,
      j1: false, j2: null, j3: null, j4: null,
      co1: false, co2: null, co3: null, co4: null,
      d1: false, d2: null, d3: null,
      s1: false,
    },
    context_note: null,
    register_note: null,
    body: 'This is a short, ordinary comment body that does not contain the quote text at the given offset at all.',
    parent_body: 'A normal parent comment.',
    replies: [],
  },
];

export const doxxing = [
  withOffset({
    id: 'fx_doxxing',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/mno345/thread/fx_doxxing/',
    created_utc: 1726358400,
    subreddit: 'fakesubreddit',
    quote: 'his real name is John Q. Fakeperson and he works at Fake Corp on Main St',
    category: 'doxxing',
    level: null, // binary, not graduated -- see spec section 2
    answers: {
      c1: false, c2: null, c3: true, c4: true, c5: null,
      b1: false, b2: null, b3: null, b4: null,
      j1: false, j2: null, j3: null, j4: null,
      co1: false, co2: null, co3: null, co4: null,
      d1: true, d2: true, d3: true,
      s1: false,
    },
    context_note: null,
    register_note: null,
    body: 'I looked him up, his real name is John Q. Fakeperson and he works at Fake Corp on Main St.',
    parent_body: 'Does anyone know anything about this guy?',
    replies: [],
  }),
];

export const coordination = [
  withOffset({
    id: 'fx_coordination',
    permalink: 'https://reddit.com/r/fakesubreddit/comments/pqr678/thread/fx_coordination/',
    created_utc: 1723420800,
    subreddit: 'fakesubreddit',
    quote: 'Everyone go report u/fake_target_user and downvote everything they post',
    category: 'coordination',
    level: 3,
    answers: {
      c1: false, c2: null, c3: true, c4: true, c5: null,
      b1: false, b2: null, b3: null, b4: null,
      j1: false, j2: null, j3: null, j4: null,
      co1: true, co2: true, co3: true, co4: true,
      d1: false, d2: null, d3: null,
      s1: false,
    },
    context_note: null,
    register_note: null,
    body: "Everyone go report u/fake_target_user and downvote everything they post, let's bury their account.",
    parent_body: null,
    replies: [],
  }),
];

export const ALL_FIXTURE_CARDS = {
  multiCategory,
  topLevel,
  judgmentWithReplies,
  corruptedOffset,
  doxxing,
  coordination,
};
