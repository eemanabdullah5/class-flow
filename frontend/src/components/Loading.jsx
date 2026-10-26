// role="status" lets screen readers announce that something is loading.
export default function Loading({ label = "Loading…" }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}
