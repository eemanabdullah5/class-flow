import { useState } from "react";

import { api } from "../api/client.js";
import ErrorMessage from "./ErrorMessage.jsx";
import FormField from "./FormField.jsx";

// Teachers create a course; the backend makes the join code.
export default function CreateCourseForm({ onCreated }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [titleError, setTitleError] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setCreated(null);
    if (!title.trim()) {
      setTitleError("Enter a course title.");
      return;
    }
    setTitleError("");

    setSubmitting(true);
    try {
      const course = await api.post("/api/courses", {
        title: title.trim(),
        description: description.trim() || null,
      });
      setCreated(course);
      setTitle("");
      setDescription("");
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card stack" onSubmit={handleSubmit} noValidate>
      <h2>Create a course</h2>
      <FormField
        id="course-title"
        label="Course title"
        value={title}
        maxLength={150}
        onChange={(e) => setTitle(e.target.value)}
        error={titleError}
      />
      <FormField
        id="course-description"
        label="Description (optional)"
        multiline
        rows={2}
        maxLength={2000}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <ErrorMessage message={error} />
      {created && (
        <div className="alert alert-success" role="status">
          Created {created.title}. Share the join code <strong>{created.join_code}</strong> with your
          students.
        </div>
      )}
      <div>
        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create course"}
        </button>
      </div>
    </form>
  );
}
