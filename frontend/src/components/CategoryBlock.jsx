import BooleanPill from './BooleanPill';
import { BOOLEAN_GROUPS, CLEARING_CRITERIA } from '../lib/findings';

const CATEGORY_LABELS = {
  conduct: 'Conduct',
  bias: 'Bias',
  judgment: 'Judgment',
  coordination: 'Coordination',
  doxxing: 'Doxxing',
  self_description: 'Self-description',
};

// FR-C6: each category on a card shows its booleans, its computed level
// (verbatim from JSON -- this component never computes one) or
// "cleared", and the criterion that cleared it.
export default function CategoryBlock({ category, level, answers }) {
  const codes = BOOLEAN_GROUPS[category] || [];
  const isBinary = category === 'doxxing' || category === 'self_description';

  return (
    <div className="category-block">
      <div className="category-header">
        <span className="category-name">{CATEGORY_LABELS[category] || category}</span>
        <span className="category-level">
          {isBinary ? 'binary — no level' : level === 0 || level == null ? 'cleared' : `level ${level}`}
        </span>
      </div>
      <div className="bool-row">
        {codes.map((code) => (
          <BooleanPill key={code} code={code} value={answers[code]} />
        ))}
      </div>
      <p className="clearing-criterion">Clears on: {CLEARING_CRITERIA[category]}</p>
    </div>
  );
}
