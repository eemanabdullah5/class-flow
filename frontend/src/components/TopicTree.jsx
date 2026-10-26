import { useState } from "react";

import { api } from "../api/client.js";
import { countSubtopics, idsInside, indentedTitle } from "../utils/topics.js";
import ErrorMessage from "./ErrorMessage.jsx";

/** "Needs: Variables, Loops", or nothing if the topic needs nothing. */
function NeedsLine({ topic, titles }) {
  if (topic.prerequisite_ids.length === 0) return null;
  return <span className="muted small">Needs: {topic.prerequisite_ids.map((id) => titles[id]).join(", ")}</span>;
}

/**
 * Teachers: rename, move, delete, and set prerequisites for one topic.
 * The backend refuses loops; its message (e.g. 'That would make a loop: …') is shown here.
 */
function TopicEditor({ topic, allTopics, titles, onChanged, onClose }) {
  const [title, setTitle] = useState(topic.title);
  const [parentId, setParentId] = useState(topic.parent_id === null ? "" : String(topic.parent_id));
  const [newPrerequisite, setNewPrerequisite] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // A topic can't go inside itself or its own subtopics, so those aren't offered.
  const blocked = new Set(idsInside(topic));
  const parentChoices = allTopics.filter((t) => !blocked.has(t.id));
  // Loops are left for the backend to catch, so the teacher sees why one is refused.
  const prerequisiteChoices = allTopics.filter((t) => t.id !== topic.id && !topic.prerequisite_ids.includes(t.id));

  async function run(action) {
    setError("");
    setBusy(true);
    try {
      await action();
      onChanged();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  function handleSave(event) {
    event.preventDefault();
    if (!title.trim()) {
      setError("Enter a topic title.");
      return;
    }
    // Only send what changed. parent_id: null means "move to the top level".
    const changes = {};
    if (title.trim() !== topic.title) changes.title = title.trim();
    const newParent = parentId === "" ? null : Number(parentId);
    if (newParent !== topic.parent_id) changes.parent_id = newParent;
    if (Object.keys(changes).length === 0) return;
    run(() => api.patch(`/api/topics/${topic.id}`, changes));
  }

  async function handleAddPrerequisite() {
    if (!newPrerequisite) return;
    const added = await run(() =>
      api.post(`/api/topics/${topic.id}/prerequisites`, { prerequisite_id: Number(newPrerequisite) }),
    );
    if (added) setNewPrerequisite("");
  }

  function handleDelete() {
    const inside = countSubtopics(topic);
    const extra = inside ? ` and the ${inside} subtopic${inside === 1 ? "" : "s"} inside it` : "";
    if (!window.confirm(`Delete "${topic.title}"${extra}? This can't be undone.`)) return;
    run(() => api.delete(`/api/topics/${topic.id}`));
  }

  const titleId = `topic-title-${topic.id}`;
  const parentSelectId = `topic-parent-${topic.id}`;
  const prerequisiteSelectId = `topic-prerequisite-${topic.id}`;

  return (
    <div className="topic-editor">
      <form className="field-row" onSubmit={handleSave} noValidate>
        <div className="field">
          <label htmlFor={titleId}>Title</label>
          <input id={titleId} maxLength={150} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={parentSelectId}>Put inside</label>
          <select id={parentSelectId} value={parentId} onChange={(e) => setParentId(e.target.value)}>
            <option value="">Top level (no parent)</option>
            {parentChoices.map((t) => (
              <option key={t.id} value={t.id}>
                {indentedTitle(t)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <button type="submit" className="button button-primary" disabled={busy}>
            Save
          </button>
        </div>
      </form>

      <div className="stack-tight">
        <span className="inline-form-label">Learn these first</span>
        {topic.prerequisite_ids.length === 0 ? (
          <span className="muted small">No prerequisites.</span>
        ) : (
          <ul className="prerequisite-list">
            {topic.prerequisite_ids.map((id) => (
              <li key={id}>
                <span>{titles[id]}</span>
                <button
                  type="button"
                  className="button button-secondary button-small"
                  aria-label={`Remove ${titles[id]}`}
                  disabled={busy}
                  onClick={() => run(() => api.delete(`/api/topics/${topic.id}/prerequisites/${id}`))}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="topic-add-prerequisite">
          <label htmlFor={prerequisiteSelectId} className="visually-hidden">
            Prerequisite to add
          </label>
          <select
            id={prerequisiteSelectId}
            value={newPrerequisite}
            onChange={(e) => setNewPrerequisite(e.target.value)}
          >
            <option value="">Choose a topic…</option>
            {prerequisiteChoices.map((t) => (
              <option key={t.id} value={t.id}>
                {indentedTitle(t)}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="button button-secondary"
            disabled={busy || !newPrerequisite}
            onClick={handleAddPrerequisite}
          >
            Add prerequisite
          </button>
        </div>
      </div>

      <ErrorMessage message={error} />

      <div className="button-row">
        <button type="button" className="button button-secondary" onClick={onClose}>
          Done
        </button>
        <button type="button" className="button button-danger" disabled={busy} onClick={handleDelete}>
          Delete topic
        </button>
      </div>
    </div>
  );
}

function TopicItem({ topic, allTopics, titles, canEdit, onChanged }) {
  const [editing, setEditing] = useState(false);

  return (
    <li>
      <div className="topic-row">
        <span className="item-main">
          <span className="item-title">{topic.title}</span>
          <NeedsLine topic={topic} titles={titles} />
        </span>
        {canEdit && !editing && (
          <button
            type="button"
            className="button button-secondary button-small"
            aria-label={`Edit ${topic.title}`}
            onClick={() => setEditing(true)}
          >
            Edit
          </button>
        )}
      </div>
      {editing && (
        <TopicEditor
          topic={topic}
          allTopics={allTopics}
          titles={titles}
          onChanged={onChanged}
          onClose={() => setEditing(false)}
        />
      )}
      {topic.children.length > 0 && (
        <TopicList topics={topic.children} allTopics={allTopics} titles={titles} canEdit={canEdit} onChanged={onChanged} />
      )}
    </li>
  );
}

/** A list of topics, each with its subtopics nested inside (it calls itself for each level). */
function TopicList({ topics, ...rest }) {
  return (
    <ul className="topic-tree">
      {topics.map((topic) => (
        <TopicItem key={topic.id} topic={topic} {...rest} />
      ))}
    </ul>
  );
}

/**
 * The course's topic tree. allTopics is the same tree, flattened (see utils/topics.js).
 * canEdit shows the teacher's Edit buttons.
 */
export default function TopicTree({ tree, allTopics, canEdit, onChanged }) {
  const titles = Object.fromEntries(allTopics.map((t) => [t.id, t.title]));
  return <TopicList topics={tree} allTopics={allTopics} titles={titles} canEdit={canEdit} onChanged={onChanged} />;
}
