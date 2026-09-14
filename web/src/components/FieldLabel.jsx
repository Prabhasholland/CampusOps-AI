export default function FieldLabel({ children, hint }) {
  if (!hint) {
    return <label className="field-label">{children}</label>;
  }
  return (
    <div className="field-label-row">
      <label className="field-label" style={{ marginBottom: 0 }}>{children}</label>
      <span className="tag tag--muted">{hint}</span>
    </div>
  );
}
