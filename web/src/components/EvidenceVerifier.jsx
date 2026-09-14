import React from "react";
import MonoValue from "./MonoValue";

export default function EvidenceVerifier({ verification, confidenceScore }) {
  if (!verification) return null;

  const scorePercent = Math.round((verification.score || confidenceScore || 0.85) * 100);
  const checklist = verification.checklist || [];
  const status = verification.status || "VERIFIED";

  const isVerified = status === "VERIFIED";
  const isActionRequired = status === "ACTION_REQUIRED";

  return (
    <div className={`verification-panel ${isVerified ? "verification-panel--success" : isActionRequired ? "verification-panel--warning" : "verification-panel--danger"}`}>
      <div className="verification-header">
        <div className="verification-header__title">
          <span className="verification-icon">{isVerified ? "✓" : isActionRequired ? "⚠️" : "✗"}</span>
          <h4>Evidence Verification Engine</h4>
        </div>
        <div className="confidence-meter-box">
          <span className="confidence-label">Confidence</span>
          <MonoValue className="confidence-value">{scorePercent}%</MonoValue>
          <div className="confidence-bar-bg">
            <div
              className="confidence-bar-fill"
              style={{ width: `${scorePercent}%`, backgroundColor: isVerified ? "var(--accent-green, #10b981)" : "var(--accent-amber, #f59e0b)" }}
            />
          </div>
        </div>
      </div>

      <div className="checklist-container">
        <p className="checklist-title">Required Evidence Validation</p>
        <div className="checklist-items">
          {checklist.map((item, idx) => (
            <div key={idx} className={`checklist-row ${item.satisfied ? "checklist-row--satisfied" : "checklist-row--missing"}`}>
              <div className="checklist-row__status">
                {item.satisfied ? "✓" : "✗"}
              </div>
              <div className="checklist-row__label">
                <span>{item.label}</span>
                {item.note && <small className="checklist-note">{item.note}</small>}
              </div>
              <div className="checklist-row__value">
                <MonoValue>{item.value != null ? String(item.value) : "Missing"}</MonoValue>
              </div>
            </div>
          ))}
        </div>
      </div>

      {verification.notes && (
        <div className="verification-notes">
          <p><b>Decision:</b> {verification.notes}</p>
        </div>
      )}
    </div>
  );
}
