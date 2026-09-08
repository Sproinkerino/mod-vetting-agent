# Evidence Assistant Flow

RoastReel uses a structured, guided conversation over the fetched Reddit archive. It is not an open-domain chatbot.

## Supported intents

1. **Claim check:** find public statements that support or contradict a claim.
2. **Topic history:** summarize what the account has publicly said about a named topic.
3. **Repeated behavior:** find recurring, directly quoted interaction patterns.
4. **Self-disclosure lookup:** retrieve explicit statements about work or background without inferring sensitive traits.

Every answer is grounded in retrieved activity and includes direct links. A result without a supporting source is not presented as fact.

## Boundaries and fallbacks

- Unclear question: offer the three on-screen suggested intents once.
- No relevant evidence: say the sampled archive does not support the claim; do not fill the gap with model knowledge.
- Insult, harassment, or sensitive-trait inference request: redirect to a factual, cited rebuttal.
- Provider or network failure: preserve the question, show a retryable error, and keep the already fetched evidence visible.
- URL without a resolvable author: explain that a username or public Reddit comment URL is required.

## Conversation depth

The current interaction resolves in one turn. Suggestions reduce blank-page friction, and the user can immediately ask a different question. Future multi-turn follow-ups should retain cited sources and stop after one clarification if the intent remains unclear.

## Maintenance signals

Track intent selected, grounded-result rate, no-evidence rate, provider-error rate, copy action, and source-link opening. Review failed questions to improve retrieval—not to broaden the model beyond the fetched archive.
