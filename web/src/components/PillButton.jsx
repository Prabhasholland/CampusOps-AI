export default function PillButton({ variant = "primary", className = "", children, ...props }) {
  return (
    <button className={`pill-button pill-button--${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}
