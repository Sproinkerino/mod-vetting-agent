import { useId, useState } from 'react';

/** Compact long public text while keeping the complete source one action away. */
export default function ExpandableText({ text = '', maxChars = 300, className = '' }) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();
  const isLong = text.length > maxChars;
  const visible = !isLong || expanded ? text : `${text.slice(0, maxChars).trimEnd()}…`;

  return <div className={`expandable-text ${className}`.trim()}>
    <p id={contentId}>{visible}</p>
    {isLong && <button type="button" aria-expanded={expanded} aria-controls={contentId} onClick={() => setExpanded((value) => !value)}>
      {expanded ? 'Show less' : 'Show full comment'}
    </button>}
  </div>;
}
