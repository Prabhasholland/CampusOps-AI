import React from "react";
import PillButton from "./PillButton";
import MonoValue from "./MonoValue";

export default function EscalationCard({ packet, item, onHandled }) {
  if (!packet && !item.routed_office && item.status !== "escalated") return null;

  const data = packet || {};
  const routedOffice = data.routed_office || item.routed_office || "Administrative Office";
  const routedContact = data.routed_contact || item.routed_contact || "Staff Member";
  const rootCause = data.root_cause || item.routed_reason || "Requires human review.";
  const recommendations = data.recommended_staff_actions || [
    "Review student file in the SIS.",
    "Follow up directly via phone or official institutional email.",
  ];

  return (
    <div className="escalation-card">
      <div className="escalation-card__header">
        <div className="escalation-alert-tag">Human Escalation Packet</div>
        <span className="urgency-pill">{data.urgency?.toUpperCase() || "ACTION REQUIRED"}</span>
      </div>

      <div className="escalation-body">
        <div className="escalation-field">
          <label>Assigned Department</label>
          <p className="escalation-office-name">{routedOffice}</p>
          <MonoValue className="escalation-contact">{routedContact}</MonoValue>
        </div>

        <div className="escalation-field">
          <label>Root Cause & Gap Analysis</label>
          <p className="escalation-root-cause">{rootCause}</p>
        </div>

        {recommendations.length > 0 && (
          <div className="escalation-field">
            <label>Recommended Staff Actions</label>
            <ol className="recommendation-list">
              {recommendations.map((action, i) => (
                <li key={i}>{action}</li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {item.status === "escalated" && onHandled && (
        <div className="escalation-actions">
          <PillButton variant="secondary" onClick={onHandled}>
            Acknowledge & Mark Handled
          </PillButton>
        </div>
      )}
    </div>
  );
}
