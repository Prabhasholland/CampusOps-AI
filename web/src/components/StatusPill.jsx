import React from "react";

const STATUS_CONFIG = {
  received: { label: "Received", className: "status-pill--received", live: false },
  planning: { label: "Planning", className: "status-pill--planning", live: true },
  in_progress: { label: "In Progress", className: "status-pill--in_progress", live: true },
  calling: { label: "Dialing CALL-E", className: "status-pill--calling", live: true },
  dialing: { label: "Dialing", className: "status-pill--dialing", live: true },
  verifying: { label: "Verifying", className: "status-pill--in_progress", live: true },
  resolved: { label: "Verified & Resolved", className: "status-pill--resolved", live: false },
  completed: { label: "Completed", className: "status-pill--resolved", live: false },
  escalated: { label: "Escalated to Staff", className: "status-pill--escalated", live: false },
  routed: { label: "Routed", className: "status-pill--escalated", live: false },
  failed: { label: "Failed", className: "status-pill--failed", live: false },
  no_answer: { label: "No Answer", className: "status-pill--no_answer", live: false },
};

export default function StatusPill({ status }) {
  const norm = (status || "received").toLowerCase().replace(" ", "_");
  const config = STATUS_CONFIG[norm] || STATUS_CONFIG.received;

  return (
    <span className={`status-pill ${config.className}`}>
      <span className={`status-pill__dot ${config.live ? "status-pill__dot--pulse" : ""}`} />
      {config.label}
    </span>
  );
}
