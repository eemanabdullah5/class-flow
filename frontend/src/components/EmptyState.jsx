// Shown when a list has nothing in it yet, with a hint about what to do next.
export default function EmptyState({ title, message, children }) {
  return (
    <div className="empty-state">
      <p className="empty-title">{title}</p>
      {message && <p className="muted">{message}</p>}
      {children}
    </div>
  );
}
