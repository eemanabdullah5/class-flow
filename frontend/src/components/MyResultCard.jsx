import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import { categoryInfo, formatPercent } from "../utils/categories.js";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";

/** "27 / 40", or a dash when nothing in the category counts yet. */
export function pointsText(category) {
  return category.possible === null ? "–" : `${category.earned} / ${category.possible}`;
}

/** Students: their weighted course result, and what each category adds. */
export default function MyResultCard({ courseId }) {
  const { data: result, loading, error, reload } = useApi(
    () => api.get(`/api/courses/${courseId}/my-result`),
    [courseId],
  );

  if (loading && !result) return <Loading label="Loading your result…" />;
  if (error) return <ErrorMessage message={error} onRetry={reload} />;

  return (
    <section className="card stack" aria-labelledby="my-result">
      <h2 id="my-result">My result</h2>
      {result.percentage === null ? (
        <p className="muted">No result yet. It appears once work is graded or a due date passes.</p>
      ) : (
        <p className="result-headline">
          <span className="result-percent">{formatPercent(result.percentage)}</span>
          <span className={`letter letter-${result.letter}`}>{result.letter}</span>
          <span className={result.passed ? "pass-text" : "fail-text"}>
            {result.passed ? "Passing" : "Not passing yet (50% needed)"}
          </span>
        </p>
      )}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col">Weight</th>
              <th scope="col">Points</th>
              <th scope="col">Score</th>
            </tr>
          </thead>
          <tbody>
            {result.categories.map((category) => (
              <tr key={category.category}>
                <th scope="row">{categoryInfo(category.category).label}</th>
                <td>{category.weight}%</td>
                <td>{pointsText(category)}</td>
                <td>{formatPercent(category.percentage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        Missing work counts as 0 after its due date. A category with nothing counted yet is left out for now, and the
        other weights are scaled up to make 100%.
      </p>
    </section>
  );
}
