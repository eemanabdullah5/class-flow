import { useState } from "react";

import { api } from "../api/client.js";
import ErrorMessage from "./ErrorMessage.jsx";

// Students type the code their teacher shared. onJoined lets the page refresh its course list.
export default function JoinCourseForm({ onJoined }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (!code.trim()) {
      setError("Enter the join code your teacher gave you.");
      return;
    }

    setSubmitting(true);
    try {
      const course = await api.post("/api/courses/join", { join_code: code.trim() });
      setSuccess(`You joined ${course.title}.`);
      setCode("");
      onJoined();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card inline-form" onSubmit={handleSubmit} noValidate>
      <label htmlFor="join-code" className="inline-form-label">
        Join a course
      </label>
      <div className="inline-form-row">
        <input
          id="join-code"
          placeholder="Class code, e.g. AB12CD"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          maxLength={20}
          autoComplete="off"
        />
        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Joining…" : "Join"}
        </button>
      </div>
      <ErrorMessage message={error} />
      {success && (
        <div className="alert alert-success" role="status">
          {success}
        </div>
      )}
    </form>
  );
}
