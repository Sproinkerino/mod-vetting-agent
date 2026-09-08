# RoastReel UI System

## Foundations

The interface uses two token tiers in `src/index.css`: raw palette tokens (`--orange`, `--purple`, `--blue`) and semantic surface/content tokens (`--bg`, `--surface`, `--line`, `--text`, `--muted`). Components must consume tokens rather than introduce one-off hex values. Space follows a compact 4/8px rhythm, cards use 12–18px radii, and headings use Space Grotesk while body copy uses DM Sans.

Orange marks the primary action and the central receipt. Purple marks investigation and filtering. Blue is reserved for links and focus. Green confirms a successfully grounded, copy-ready result. Color is never the only state cue.

## Elements

- **Primary button:** solid orange, one per interaction region, 44px minimum target.
- **Text button:** low-emphasis navigation action with a visible border.
- **Filter chip:** a real button with `aria-pressed`; horizontally scrollable on mobile.
- **Input/textarea:** persistent programmatic label, help or error association, visible focus ring.
- **Source link:** describes its destination and always opens the original Reddit context.

## Components

- **TargetComment:** the statement being investigated; quote and source link only.
- **AskPanel:** suggested grounded intents, free-text question, loading/error/result states.
- **ReplyCard:** copy-ready claim check, numbered sources, and small viral attribution.
- **FindingCard:** category, exact quote, source, and progressively disclosed full context.
- **SignalStrip:** secondary behavior summary of the sample, never a a personality diagnosis.
- **ActivityExplorer:** searchable, paginated source archive.

## Page patterns

Home uses one clear input and honest indeterminate loading. Case files follow: target → ask/copy → evidence → sampled behavior → complete archive. Mobile is single-column; evidence and history become two columns at 760px. Content remains capped at 1120px.

## Governance

Keep component behavior and this document updated in the same change. New colors or spacing values require a semantic token. New interactive components require keyboard, focus, loading, empty, error, and disabled-state review. Review the system whenever a second visually divergent implementation of an existing component appears.
