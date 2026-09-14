import React from "react";

export default function CoordinationMatrix({ steps = [], confirmedSlot = "Tuesday 2:00 PM" }) {
  const participants = [
    { role: "Student", name: "Maria Nghipandulwa", slot: "Tuesday 2:00 PM", status: "confirmed" },
    { role: "Faculty Advisor", name: "Dr. Johannes Alweendo", slot: "Tuesday 2:00 PM", status: "confirmed" },
    { role: "Department Office", name: "FCI Administration (Room 302)", slot: "Tuesday 2:00 PM", status: "confirmed" },
  ];

  return (
    <div className="coordination-matrix-box">
      <div className="coordination-matrix-header">
        <h4>Multi-Party Coordination Matrix</h4>
        <span className="consensus-badge">Consensus Reached: {confirmedSlot}</span>
      </div>

      <div className="matrix-table">
        <div className="matrix-header-row">
          <span>Participant Role</span>
          <span>Contact Entity</span>
          <span>Agreed Window</span>
          <span>Status</span>
        </div>
        {participants.map((p, idx) => (
          <div key={idx} className="matrix-row">
            <span className="matrix-role">{p.role}</span>
            <span className="matrix-name">{p.name}</span>
            <span className="matrix-slot">{p.slot}</span>
            <span className="matrix-status-pill">✓ Confirmed</span>
          </div>
        ))}
      </div>
    </div>
  );
}
