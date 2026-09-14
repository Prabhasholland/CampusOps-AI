export default function MonoValue({ children, className = "", ...props }) {
  return (
    <span className={`mono ${className}`} {...props}>
      {children}
    </span>
  );
}
