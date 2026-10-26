import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import EmptyState from "../components/EmptyState.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import { pointsText } from "../components/MyResultCard.jsx";
import useApi from "../hooks/useApi.js";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { CATEGORIES, categoryInfo, formatPercent } from "../utils/categories.js";
import { formatDateTime } from "../utils/dates.js";

/** 6.5 -> "6.5", null -> "–" */
function number(value, digits = 2) {
  return value === null || value === undefined ? "–" : String(Number(value.toFixed(digits)));
}

/** Shows loading, an error, or "nothing yet" for one section; otherwise the table. */
function Section({ id, title, description, state, emptyText, children }) {
  return (
    <section className="stack" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {description && <p className="muted">{description}</p>}
      {state.loading && !state.data && <Loading />}
      <ErrorMessage message={state.error} onRetry={state.reload} />
      {state.data && (Array.isArray(state.data) && state.data.length === 0 ? <EmptyState title={emptyText} /> : children(state.data))}
    </section>
  );
}

function StatsCards({ stats, passPercent }) {
  const cards = [
    ["Students with a result", String(stats.count)],
    ["Average", formatPercent(stats.mean)],
    ["Lowest", formatPercent(stats.minimum)],
    ["Highest", formatPercent(stats.maximum)],
    ["Variance", number(stats.variance)],
    [`Passing (${passPercent}%+)`, stats.pass_proportion === null ? "–" : formatPercent(100 * stats.pass_proportion)],
  ];
  return (
    <dl className="stat-grid">
      {cards.map(([label, value]) => (
        <div key={label} className="stat-card">
          <dt className="muted small">{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ClassResultsTable({ rows }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Student</th>
            {CATEGORIES.map((c) => (
              <th key={c.key} scope="col">
                {c.label} ({c.weight}%)
              </th>
            ))}
            <th scope="col">Overall</th>
            <th scope="col">Letter</th>
            <th scope="col">Pass</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ student, result }) => (
            <tr key={student.id}>
              <th scope="row">{student.full_name}</th>
              {result.categories.map((category) => (
                <td key={category.category} title={pointsText(category)}>
                  {formatPercent(category.percentage)}
                </td>
              ))}
              <td>
                <strong>{formatPercent(result.percentage)}</strong>
              </td>
              <td>{result.letter ?? "–"}</td>
              <td>{result.passed === null ? "–" : result.passed ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssignmentReport({ rows }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Assignment</th>
            <th scope="col">Due</th>
            <th scope="col">Turned in</th>
            <th scope="col">Late</th>
            <th scope="col">Missing</th>
            <th scope="col">Graded</th>
            <th scope="col">Average</th>
            <th scope="col">Lowest – highest</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <th scope="row">
                {row.title}
                <br />
                <span className="muted small">
                  {categoryInfo(row.category).label} · {row.max_points} points
                </span>
              </th>
              <td>{formatDateTime(row.due_at)}</td>
              <td>
                {row.turned_in} / {row.enrolled}
              </td>
              <td>{row.late}</td>
              <td>{row.missing ?? "in class"}</td>
              <td>
                {row.graded} / {row.enrolled}
              </td>
              <td>{number(row.average_score)}</td>
              <td>{row.lowest_score === null ? "–" : `${row.lowest_score} – ${row.highest_score}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StudentReport({ rows }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Student</th>
            <th scope="col">Turned in</th>
            <th scope="col">Late</th>
            <th scope="col">Graded</th>
            <th scope="col">Points (graded work)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <th scope="row">
                {row.full_name}
                <br />
                <span className="muted small">{row.email}</span>
              </th>
              <td>{row.turned_in}</td>
              <td>{row.late}</td>
              <td>{row.graded}</td>
              <td>
                {row.points_earned} / {row.points_possible}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MissingLateReport({ rows }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Student</th>
            <th scope="col">Assignment</th>
            <th scope="col">Due</th>
            <th scope="col">Problem</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.assignment_id}-${row.student_id}`}>
              <th scope="row">{row.student_name}</th>
              <td>
                <Link to={`/assignments/${row.assignment_id}`}>{row.assignment_title}</Link>
              </td>
              <td>{formatDateTime(row.due_at)}</td>
              <td>
                {row.problem === "late" ? (
                  <span className="badge badge-late">Late · {formatDateTime(row.submitted_at)}</span>
                ) : (
                  <span className="badge badge-missing">Missing</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Teachers only (see App.jsx). Each part loads on its own, so one failing doesn't hide the rest.
export default function ResultsPage() {
  const { courseId } = useParams();
  const course = useApi(() => api.get(`/api/courses/${courseId}`), [courseId]);
  const results = useApi(() => api.get(`/api/courses/${courseId}/results`), [courseId]);
  const byAssignment = useApi(() => api.get(`/api/courses/${courseId}/reports/assignments`), [courseId]);
  const byStudent = useApi(() => api.get(`/api/courses/${courseId}/reports/students`), [courseId]);
  const missingLate = useApi(() => api.get(`/api/courses/${courseId}/reports/missing-late`), [courseId]);
  useDocumentTitle(course.data ? `Results · ${course.data.title}` : "Results");

  if (course.loading && !course.data) {
    return (
      <main className="page">
        <Loading label="Loading results…" />
      </main>
    );
  }
  if (course.error) {
    return (
      <main className="page stack">
        <Link to="/" className="back-link">
          ← My courses
        </Link>
        <ErrorMessage message={course.error} onRetry={course.reload} />
      </main>
    );
  }

  const scale = results.data?.letter_scale ?? [];

  return (
    <main className="page stack">
      <Link to={`/courses/${courseId}`} className="back-link">
        ← {course.data.title}
      </Link>
      <h1>Results and reports</h1>

      <Section id="class-stats" title="Class statistics" state={results}>
        {(data) => <StatsCards stats={data.stats} passPercent={data.pass_percent} />}
      </Section>

      <Section
        id="class-results"
        title="Course results"
        description={
          "Weighted: quiz 10%, assignment 10%, midterm 30%, project 50%. " +
          `Letters: ${scale.map((band) => `${band.letter} ${band.lowest}%+`).join(", ")}.`
        }
        state={{ ...results, data: results.data?.students }}
        emptyText="No students in this course yet."
      >
        {(rows) => <ClassResultsTable rows={rows} />}
      </Section>

      <Section
        id="report-assignments"
        title="Report 1: Assignment summary"
        state={byAssignment}
        emptyText="No assignments yet."
      >
        {(rows) => <AssignmentReport rows={rows} />}
      </Section>

      <Section
        id="report-students"
        title="Report 2: Student progress"
        state={byStudent}
        emptyText="No students in this course yet."
      >
        {(rows) => <StudentReport rows={rows} />}
      </Section>

      <Section
        id="report-missing"
        title="Report 3: Missing and late work"
        description="Work past its due date that hasn't been handed in, or was handed in late."
        state={missingLate}
        emptyText="Nothing missing or late."
      >
        {(rows) => <MissingLateReport rows={rows} />}
      </Section>
    </main>
  );
}
