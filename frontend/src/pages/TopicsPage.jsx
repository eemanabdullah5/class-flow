import { useState } from "react";
import { Link, useParams } from "react-router";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import AddTopicForm from "../components/AddTopicForm.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import Loading from "../components/Loading.jsx";
import TopicTree from "../components/TopicTree.jsx";
import useApi from "../hooks/useApi.js";
import useDocumentTitle from "../hooks/useDocumentTitle.js";
import { flattenTree } from "../utils/topics.js";

/** Every topic, prerequisites first (worked out by the backend's topological sort). */
function StudyOrder({ items }) {
  const titles = Object.fromEntries(items.map((item) => [item.id, item.title]));
  return (
    <ol className="study-order">
      {items.map((item) => (
        <li key={item.id}>
          <span className="item-title">{item.title}</span>
          {item.prerequisite_ids.length > 0 && (
            <span className="muted small"> after {item.prerequisite_ids.map((id) => titles[id]).join(", ")}</span>
          )}
        </li>
      ))}
    </ol>
  );
}

// Shared by students (read only) and the course's teacher (can edit).
export default function TopicsPage() {
  const { courseId } = useParams();
  const { user } = useAuth();
  const isTeacher = user.role === "teacher";

  // Goes up after every change, so the tree and the study order both load again.
  const [version, setVersion] = useState(0);
  const refresh = () => setVersion((v) => v + 1);

  const course = useApi(() => api.get(`/api/courses/${courseId}`), [courseId]);
  const tree = useApi(() => api.get(`/api/courses/${courseId}/topics`), [courseId, version]);
  const order = useApi(() => api.get(`/api/courses/${courseId}/topics/study-order`), [courseId, version]);
  useDocumentTitle(course.data ? `Topics · ${course.data.title}` : "Topics");

  // The course loads first; if it fails (e.g. 404 for outsiders) nothing else is shown.
  if (course.loading && !course.data) {
    return (
      <main className="page">
        <Loading label="Loading topics…" />
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

  const allTopics = tree.data ? flattenTree(tree.data) : [];

  return (
    <main className="page stack">
      <Link to={`/courses/${courseId}`} className="back-link">
        ← {course.data.title}
      </Link>
      <h1>Topics</h1>

      {isTeacher && <AddTopicForm courseId={courseId} topics={allTopics} onAdded={refresh} />}

      <section className="stack" aria-labelledby="topic-tree-heading">
        <h2 id="topic-tree-heading">Topic tree</h2>
        {tree.loading && !tree.data && <Loading label="Loading topics…" />}
        <ErrorMessage message={tree.error} onRetry={tree.reload} />
        {tree.data && tree.data.length === 0 && (
          <EmptyState
            title="No topics yet."
            message={isTeacher ? "Add the first topic above." : "Your teacher hasn't added any topics."}
          />
        )}
        {tree.data && tree.data.length > 0 && (
          <div className="card">
            <TopicTree tree={tree.data} allTopics={allTopics} canEdit={isTeacher} onChanged={refresh} />
          </div>
        )}
      </section>

      {order.data && order.data.length > 0 && (
        <section className="stack" aria-labelledby="study-order-heading">
          <h2 id="study-order-heading">Study order</h2>
          <p className="muted">A suggested order: every topic comes after the topics it needs.</p>
          <div className="card">
            <StudyOrder items={order.data} />
          </div>
        </section>
      )}
      {!order.data && <ErrorMessage message={order.error} onRetry={order.reload} />}
    </main>
  );
}
