export default function ScenarioTest({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <section className="scenario-test">
      <h2>Scenario test</h2>
      {items.map((item) => (
        <div key={item.item_id} className="scenario-item">
          <p className="scenario-call">
            <strong>Applicant's call:</strong> {item.applicant_call}
          </p>
          <p className="scenario-reasoning">{item.applicant_reasoning}</p>
          <p className="scenario-assessment">
            <strong>Assessment:</strong> {item.assessment} (level {item.level})
          </p>
        </div>
      ))}
    </section>
  );
}
