import { useRef, useState } from "react";

import { api } from "../api/client.js";
import useApi from "../hooks/useApi.js";
import { formatDateTime, isPast } from "../utils/dates.js";
import { ACCEPT_ATTRIBUTE, checkFile, formatFileSize } from "../utils/files.js";
import ErrorMessage from "./ErrorMessage.jsx";
import Loading from "./Loading.jsx";
import StatusBadge from "./StatusBadge.jsx";

/**
 * The student's own work for one assignment:
 *   nothing yet -> upload a file (draft) -> mark as done (submitted) -> graded (locked)
 * A submitted file can be unsubmitted to replace it, until it is graded.
 */
export default function StudentWorkPanel({ assignment }) {
  const base = `/api/assignments/${assignment.id}`;
  const submission = useApi(() => api.get(`${base}/my-submission`), [assignment.id]);
  const grade = useApi(() => api.get(`${base}/my-grade`), [assignment.id]);

  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  const work = submission.data; // null if nothing uploaded yet
  const myGrade = grade.data; // null if not graded yet

  // Run one action (upload, mark as done, ...), show any error, then refresh.
  async function run(action) {
    setError("");
    setBusy(true);
    try {
      await action();
      submission.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function handleUpload(event) {
    event.preventDefault();
    const problem = checkFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    run(async () => {
      await api.upload(`${base}/submission`, file);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    });
  }

  async function handleDownload() {
    setError("");
    try {
      await api.download(`/api/submissions/${work.id}/file`, work.original_filename);
    } catch (err) {
      setError(err.message);
    }
  }

  if ((submission.loading && !busy && !submission.data) || grade.loading) {
    return <Loading label="Loading your work…" />;
  }
  if (submission.error || grade.error) {
    return <ErrorMessage message={submission.error || grade.error} onRetry={submission.reload} />;
  }

  const canUpload = !myGrade && (!work || work.status === "draft");

  return (
    <section className="card stack work-panel" aria-labelledby="your-work">
      <div className="work-header">
        <h2 id="your-work">Your work</h2>
        <StatusBadge
          submissionStatus={work ? work.status : "none"}
          isLate={work?.is_late}
          grade={myGrade}
          dueAt={assignment.due_at}
        />
      </div>

      {myGrade && (
        <div className="grade-box">
          <p className="grade-score">
            {myGrade.score} / {assignment.max_points}
          </p>
          {myGrade.feedback && <p className="grade-feedback">“{myGrade.feedback}”</p>}
          <p className="muted">Graded work can no longer be changed.</p>
        </div>
      )}

      {work && (
        <div className="file-row">
          <span>
            <strong>{work.original_filename}</strong>{" "}
            <span className="muted">({formatFileSize(work.file_size)})</span>
            <br />
            <span className="muted">
              {work.submitted_at
                ? `Turned in ${formatDateTime(work.submitted_at)}`
                : `Uploaded ${formatDateTime(work.uploaded_at)} · not turned in yet`}
            </span>
          </span>
          <button type="button" className="button button-secondary" onClick={handleDownload}>
            Download
          </button>
        </div>
      )}

      <ErrorMessage message={error} />

      {!myGrade && isPast(assignment.due_at) && work?.status !== "submitted" && (
        <div className="alert alert-warning">
          The due date has passed. You can still turn in work, but it will be marked late.
        </div>
      )}

      {canUpload && (
        <form className="upload-form" onSubmit={handleUpload} noValidate>
          <label htmlFor="work-file">{work ? "Replace file" : "Choose a file"}</label>
          <input
            id="work-file"
            ref={fileInput}
            type="file"
            accept={ACCEPT_ATTRIBUTE}
            onChange={(e) => setFile(e.target.files[0] || null)}
          />
          <p className="muted small">PDF, DOCX, ZIP, PNG or JPG · up to 10 MB</p>
          <button type="submit" className="button button-secondary" disabled={busy}>
            {busy ? "Working…" : "Upload"}
          </button>
        </form>
      )}

      {work?.status === "draft" && !myGrade && (
        <button
          type="button"
          className="button button-primary"
          disabled={busy}
          onClick={() => run(() => api.post(`${base}/submission/turn-in`))}
        >
          Mark as done
        </button>
      )}

      {work?.status === "submitted" && !myGrade && (
        <button
          type="button"
          className="button button-secondary"
          disabled={busy}
          onClick={() => run(() => api.post(`${base}/submission/unsubmit`))}
        >
          Unsubmit
        </button>
      )}
    </section>
  );
}
