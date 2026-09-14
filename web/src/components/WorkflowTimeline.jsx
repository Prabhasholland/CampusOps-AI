import React from "react";
import StatusPill from "./StatusPill";
import MonoValue from "./MonoValue";

export default function WorkflowTimeline({ item }) {
  const steps = item.steps || [];
  const plan = item.plan;
  const currentStep = item.current_step_index || 0;
  const totalSteps = item.total_steps || (steps.length > 0 ? steps.length : 1);

  return (
    <div className="workflow-timeline-card">
      <div className="timeline-header">
        <div className="timeline-header__left">
          <span className="workflow-type-badge">{item.workflow_type?.toUpperCase() || "OPERATION"}</span>
          <h3 className="timeline-title">{item.title || "Autonomous Phone Workflow"}</h3>
        </div>
        <div className="timeline-header__right">
          <span className="step-count-badge">
            Step {Math.min(currentStep, totalSteps)} of {totalSteps}
          </span>
        </div>
      </div>

      {plan && plan.reasoning && (
        <div className="timeline-plan-box">
          <div className="plan-tag">AI Operational Plan</div>
          <p className="plan-text">{plan.reasoning}</p>
        </div>
      )}

      <div className="stepper-list">
        {steps.length > 0 ? (
          steps.map((s, idx) => {
            const isCompleted = idx < currentStep || item.status === "resolved";
            const isActive = idx + 1 === currentStep && item.status !== "resolved";

            return (
              <div
                key={idx}
                className={`stepper-node ${isCompleted ? "stepper-node--completed" : ""} ${
                  isActive ? "stepper-node--active" : ""
                }`}
              >
                <div className="stepper-marker">
                  {isCompleted ? "✓" : idx + 1}
                </div>
                <div className="stepper-content">
                  <div className="stepper-content__top">
                    <span className="stepper-role">{s.target_role?.replace("_", " ").toUpperCase()}</span>
                    <span className="stepper-name">{s.target_name}</span>
                    <MonoValue className="stepper-phone">{s.target_phone}</MonoValue>
                    <StatusPill status={s.call_status || (isCompleted ? "resolved" : "calling")} />
                  </div>

                  {s.structured_result && (
                    <div className="stepper-result-summary">
                      {s.structured_result.application_status && (
                        <span className="result-chip">Status: <b>{s.structured_result.application_status}</b></span>
                      )}
                      {s.structured_result.payment_status && (
                        <span className="result-chip">Payment: <b>{s.structured_result.payment_status}</b></span>
                      )}
                      {s.structured_result.expected_date && (
                        <span className="result-chip">Date: <b>{s.structured_result.expected_date}</b></span>
                      )}
                      {s.structured_result.confirmed_slot && (
                        <span className="result-chip">Confirmed Slot: <b>{s.structured_result.confirmed_slot}</b></span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="stepper-node stepper-node--active">
            <div className="stepper-marker">1</div>
            <div className="stepper-content">
              <div className="stepper-content__top">
                <span className="stepper-role">TARGET</span>
                <span className="stepper-name">{item.student_name || item.caller_name || "Operational Contact"}</span>
                <MonoValue className="stepper-phone">{item.phone}</MonoValue>
                <StatusPill status={item.status} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
