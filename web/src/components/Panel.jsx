export default function Panel({ title, right, children, className = "" }) {
  return (
    <div className={`panel ${className}`}>
      {(title || right) && (
        <div className="panel__header">
          {title && <h2 className="panel__title">{title}</h2>}
          {right}
        </div>
      )}
      {children}
    </div>
  );
}
