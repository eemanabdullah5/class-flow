import { useState } from "react";

import { api } from "../api/client.js";
import { CATEGORIES } from "../utils/categories.js";
import { localInputToIso, toLocalInputValue } from "../utils/dates.js";
import ErrorMessage from "./ErrorMessage.jsx";
import FormField from "./FormField.jsx";

const MAX_POINTS = 1000; // same limit as the backend

function validate(form) {
  const problems = {};
  if (!form.title.trim()) problems.title = "Enter a title.";
  const points = Number(form.maxPoints);
  if (form.maxPoints === "" || Number.isNaN(points) || points <= 0 || points > MAX_POINTS) {
    problems.maxPoints = `Max points must be more than 0 and at most ${MAX_POINTS}.`;
  }
  if (!form.dueAt) problems.dueAt = "Choose a due date and time.";
  else if (new Date(form.dueAt).getTime() <= Date.now()) problems.dueAt = "The due date must be in the future.";
  return problems;
}

/**
 * Create a new assignment (pass courseId) or edit one (pass existing).
 * When editing, only the fields that changed are sent, so an old due date
 * that has already passed doesn't block fixing a typo in the title.
 */
export default function AssignmentForm({ courseId, existing, onSaved, onCancel }) {
  const [form, setForm] = useState({
    title: existing?.title ?? "",
    category: existing?.category ?? "assignment",
    instructions: existing?.instructions ?? "",
    maxPoints: existing ? String(existing.max_points) : "",
    dueAt: existing ? toLocalInputValue(existing.due_at) : "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  function changedFields() {
    const all = {
      title: form.title.trim(),
      category: form.category,
      instructions: form.instructions.trim() || null,
      max_points: Number(form.maxPoints),
      due_at: form.dueAt,
    };
    if (!existing) return { ...all, due_at: localInputToIso(form.dueAt) };

    const changes = {};
    if (all.title !== existing.title) changes.title = all.title;
    if (all.category !== existing.category) changes.category = all.category;
    if (all.instructions !== (existing.instructions || null)) changes.instructions = all.instructions;
    if (all.max_points !== existing.max_points) changes.max_points = all.max_points;
    if (form.dueAt !== toLocalInputValue(existing.due_at)) changes.due_at = localInputToIso(form.dueAt);
    return changes;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const problems = validate(form);
    // An unchanged due date that is already past is fine when editing.
    if (existing && form.dueAt === toLocalInputValue(existing.due_at)) delete problems.dueAt;
    setFieldErrors(problems);
    if (Object.keys(problems).length > 0) return;

    const body = changedFields();
    if (existing && Object.keys(body).length === 0) {
      onCancel();
      return;
    }

    setSubmitting(true);
    try {
      const saved = existing
        ? await api.patch(`/api/assignments/${existing.id}`, body)
        : await api.post(`/api/courses/${courseId}/assignments`, body);
      onSaved(saved);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <form className="card stack" onSubmit={handleSubmit} noValidate>
      <h2>{existing ? "Edit assignment" : "New assignment"}</h2>
      <FormField
        id="assignment-title"
        label="Title"
        maxLength={150}
        value={form.title}
        onChange={update("title")}
        error={fieldErrors.title}
      />
      <div className="field">
        <label htmlFor="assignment-category">Category</label>
        <select id="assignment-category" value={form.category} onChange={update("category")}>
          {CATEGORIES.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label} ({c.weight}% of the course{c.inClass ? ", taken in class" : ""})
            </option>
          ))}
        </select>
      </div>
      <FormField
        id="assignment-instructions"
        label="Instructions (optional)"
        multiline
        rows={4}
        maxLength={5000}
        value={form.instructions}
        onChange={update("instructions")}
      />
      <div className="field-row">
        <FormField
          id="assignment-points"
          label="Max points"
          type="number"
          min="1"
          max={MAX_POINTS}
          step="any"
          value={form.maxPoints}
          onChange={update("maxPoints")}
          error={fieldErrors.maxPoints}
        />
        <FormField
          id="assignment-due"
          label="Due date (your local time)"
          type="datetime-local"
          value={form.dueAt}
          onChange={update("dueAt")}
          error={fieldErrors.dueAt}
        />
      </div>
      <ErrorMessage message={error} />
      <div className="button-row">
        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Saving…" : existing ? "Save changes" : "Create assignment"}
        </button>
        <button type="button" className="button button-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
