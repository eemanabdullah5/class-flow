import { useState } from "react";

import { api } from "../api/client.js";
import { indentedTitle } from "../utils/topics.js";
import ErrorMessage from "./ErrorMessage.jsx";
import FormField from "./FormField.jsx";

/** Teachers: add a topic at the top level or inside another topic. */
export default function AddTopicForm({ courseId, topics, onAdded }) {
  const [title, setTitle] = useState("");
  const [parentId, setParentId] = useState("");
  const [titleError, setTitleError] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!title.trim()) {
      setTitleError("Enter a topic title.");
      return;
    }
    setTitleError("");

    setSaving(true);
    try {
      const body = { title: title.trim() };
      if (parentId) body.parent_id = Number(parentId);
      await api.post(`/api/courses/${courseId}/topics`, body);
      setTitle(""); // keep the parent chosen, so several subtopics can be added in a row
      onAdded();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card stack" onSubmit={handleSubmit} noValidate>
      <h2>Add a topic</h2>
      <div className="field-row">
        <FormField
          id="new-topic-title"
          label="Title"
          maxLength={150}
          value={title}
          error={titleError}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="field">
          <label htmlFor="new-topic-parent">Put inside</label>
          <select id="new-topic-parent" value={parentId} onChange={(e) => setParentId(e.target.value)}>
            <option value="">Top level (no parent)</option>
            {topics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {indentedTitle(topic)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <ErrorMessage message={error} />
      <div>
        <button type="submit" className="button button-primary" disabled={saving}>
          {saving ? "Adding…" : "Add topic"}
        </button>
      </div>
    </form>
  );
}
