export default function Recommendation({ recommendation, challenges }) {
  const dissentChallenges = (challenges || []).filter((c) => c.resolution === 'recorded_as_dissent');
  return (
    <section className="recommendation">
      <h2>Recommendation</h2>
      <p className="recommendation-text">{recommendation.text}</p>
      {recommendation.dissent && (
        <p className="recommendation-dissent">
          <strong>Dissent:</strong> {recommendation.dissent}
        </p>
      )}
      {dissentChallenges.length > 0 && (
        <div className="recorded-dissents">
          <strong>Challenges recorded as dissent:</strong>
          <ul>
            {dissentChallenges.map((c, i) => (
              <li key={i}>{c.challenge}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
