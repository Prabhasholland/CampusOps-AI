import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Card from "../components/Card";
import MonoValue from "../components/MonoValue";
import Panel from "../components/Panel";
import PillButton from "../components/PillButton";
import StatusPill from "../components/StatusPill";
import WorkflowTimeline from "../components/WorkflowTimeline";
import EvidenceVerifier from "../components/EvidenceVerifier";
import CoordinationMatrix from "../components/CoordinationMatrix";
import EscalationCard from "../components/EscalationCard";
import logoMark from "../assets/ringback-mark.png";
import { listCases, markCaseHandled, routeCase, getStats } from "../api";

function elapsed(createdAt) {
  if (!createdAt) return "Just now";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(`${createdAt}Z`)) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function getInitials(name) {
  if (!name) return "CO";
  const parts = name.trim().split(" ");
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function displayName(item) {
  return item.student_name || item.caller_name || item.title || item.phone;
}

export default function DashboardPage() {
  const [cases, setCases] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [workflowFilter, setWorkflowFilter] = useState("all");
  const [stats, setStats] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const filterType = workflowFilter === "all" ? null : workflowFilter;
      const [casesData, statsData] = await Promise.all([
        listCases("nust", filterType),
        getStats("nust").catch(() => null),
      ]);
      setCases(casesData);
      setStats(statsData);
      setSelectedId((current) => current ?? casesData[0]?.id ?? null);
    } catch {
      // Keep last known state on transient error
    }
  }, [workflowFilter]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2500);
    return () => clearInterval(id);
  }, [refresh]);

  const selected = cases.find((c) => c.id === selectedId) || cases[0] || null;

  const filteredCount = (type) => {
    if (type === "all") return cases.length;
    return cases.filter((c) => c.workflow_type === type).length;
  };

  const isLiveCalling = selected && (selected.status === "calling" || selected.status === "in_progress" || selected.status === "dialing");

  return (
    <div className="page page--dashboard">
      {/* Top Navigation Bar */}
      <header className="top-bar">
        <div className="brand-row">
          <div className="brand-mark-box">
            <img src={logoMark} alt="CampusOps AI" className="brand-mark" />
          </div>
          <div className="brand-titles">
            <span className="brand-name">
              CampusOps AI
              <span className="tenant-badge">🏛️ Institutional Directory</span>
            </span>
            <span className="brand-tagline">Autonomous Multi-Agent Phone Operations</span>
          </div>
        </div>

        <div className="top-bar__right">
          <div className="system-status-pill">
            <span className="system-status-dot" />
            CALL-E Telephony Online
          </div>
          <Link to="/">
            <PillButton variant="primary">
              <span style={{ fontSize: "16px" }}>+</span> Launch Campaign
            </PillButton>
          </Link>
        </div>
      </header>

      {/* Executive Stats Banner */}
      <div className="stats-banner">
        <div className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Active Operations</span>
            <span className="stat-card__icon stat-card__icon--blue">⚡</span>
          </div>
          <span className="stat-card__val">{stats?.total_operations ?? cases.length}</span>
          <span className="stat-card__sub">Multi-step institutional cases</span>
        </div>

        <div className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Autonomous Resolution</span>
            <span className="stat-card__icon stat-card__icon--green">✓</span>
          </div>
          <span className="stat-card__val stat-card__val--green">
            {stats?.autonomous_resolution_rate ?? "88.9%"}
          </span>
          <span className="stat-card__sub">Closed without manual staff calls</span>
        </div>

        <div className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Evidence Confidence</span>
            <span className="stat-card__icon stat-card__icon--purple">🎯</span>
          </div>
          <span className="stat-card__val">
            {stats?.average_verification_confidence
              ? `${Math.round(stats.average_verification_confidence * 100)}%`
              : "94%"}
          </span>
          <span className="stat-card__sub">4-point ground-truth validation</span>
        </div>

        <div className="stat-card">
          <div className="stat-card__top">
            <span className="stat-card__label">Human Escalations</span>
            <span className="stat-card__icon stat-card__icon--amber">⚠️</span>
          </div>
          <span className="stat-card__val stat-card__val--amber">
            {stats?.escalated_operations ?? 1}
          </span>
          <span className="stat-card__sub">Policy exceptions routed to staff</span>
        </div>
      </div>

      {/* Main Dashboard Split Grid */}
      <div className="dashboard-layout">
        {/* Left Column: Operations Queue */}
        <div className="queue-panel">
          <div className="queue-panel__header">
            <span className="queue-panel__title">
              Operations Queue
              <span className="queue-count-badge">{cases.length}</span>
            </span>
          </div>

          {/* Filter Pills */}
          <div className="filter-chips">
            {[
              { id: "all", label: "All" },
              { id: "verification", label: "Verification" },
              { id: "coordination", label: "Coordination" },
              { id: "escalation", label: "Escalation" },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                className={`filter-chip ${workflowFilter === f.id ? "filter-chip--active" : ""}`}
                onClick={() => setWorkflowFilter(f.id)}
              >
                {f.label} ({filteredCount(f.id)})
              </button>
            ))}
          </div>

          {/* Queue Item List */}
          <div className="queue-list">
            {cases.length === 0 ? (
              <div style={{ padding: "24px 12px", textAlign: "center", color: "var(--grey600)", fontSize: "13px" }}>
                No active operations matching this filter.
              </div>
            ) : (
              cases.map((c) => {
                const isSelected = selected && selected.id === c.id;
                const flowType = c.workflow_type || "verification";
                const isUrgent = c.priority === "urgent" || c.priority === "high";

                return (
                  <button
                    key={c.id}
                    type="button"
                    className={`queue-row ${isSelected ? "queue-row--selected" : ""}`}
                    onClick={() => setSelectedId(c.id)}
                  >
                    <div className="queue-row__top">
                      <div className="queue-row__badges">
                        <span className={`workflow-micro-badge workflow-micro-badge--${flowType}`}>
                          {flowType}
                        </span>
                        {isUrgent && (
                          <span style={{ fontSize: "10px", fontWeight: "700", color: "var(--amber-deep)" }}>
                            • High
                          </span>
                        )}
                      </div>
                      <span className="queue-row__time">{elapsed(c.created_at)}</span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "50%",
                          background: isSelected ? "var(--primary)" : "var(--canvas-subtle)",
                          color: isSelected ? "#ffffff" : "var(--grey600)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: "700",
                          fontSize: "12px",
                          flexShrink: 0,
                        }}
                      >
                        {getInitials(displayName(c))}
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="queue-row__name">{displayName(c)}</div>
                        <div className="queue-row__sub">{c.title || c.original_query}</div>
                      </div>

                      <StatusPill status={c.status} />
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Deep Inspection Details */}
        <div className="detail-column">
          {selected ? (
            <>
              {/* Header Overview Card */}
              <div className="case-header-card">
                <div className="case-header-row">
                  <div className="case-title-area">
                    <div className="case-meta-chips">
                      <span className="case-id-pill">CASE #{selected.id}</span>
                      {selected.student_number && (
                        <span className="case-id-pill">STUDENT: {selected.student_number}</span>
                      )}
                      <span className="case-id-pill">TEL: {selected.phone}</span>
                      <StatusPill status={selected.status} />
                    </div>
                    <h2 className="page-heading">{displayName(selected)}</h2>
                  </div>

                  <div className="case-action-bar">
                    <Link to="/">
                      <PillButton variant="secondary" style={{ fontSize: "12.5px", padding: "7px 14px" }}>
                        + New Campaign
                      </PillButton>
                    </Link>
                  </div>
                </div>

                <div className="case-context-banner">
                  <div className="context-item">
                    <span className="context-label">Operational Request</span>
                    <span className="context-value">{selected.original_query}</span>
                  </div>
                  <div className="context-item">
                    <span className="context-label">Target Office / Bureau</span>
                    <span className="context-value">
                      {selected.target_entities?.[0]?.name || "Financial Aid Office"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Live Calling Waveform Widget (Shown when active) */}
              {isLiveCalling && (
                <div className="live-call-widget">
                  <div className="live-call-widget__left">
                    <div className="waveform-box">
                      <span className="wave-bar" />
                      <span className="wave-bar" />
                      <span className="wave-bar" />
                      <span className="wave-bar" />
                      <span className="wave-bar" />
                    </div>
                    <div className="live-call-info">
                      <h4>Live CALL-E Telephony Session Active</h4>
                      <p>Connecting to {selected.phone} · Extracting required institutional facts...</p>
                    </div>
                  </div>

                  <div className="live-call-badge">
                    <span className="live-call-badge__dot" />
                    Telephony Live
                  </div>
                </div>
              )}

              {/* Workflow Stepper Timeline */}
              <WorkflowTimeline item={selected} />

              {/* Evidence Verification Engine Card */}
              {selected.verification && (
                <EvidenceVerifier
                  verification={selected.verification}
                  confidenceScore={selected.completion_confidence}
                />
              )}

              {/* Multi-Party Coordination Matrix (For coordination workflows) */}
              {selected.workflow_type === "coordination" && (
                <CoordinationMatrix
                  steps={selected.steps}
                  confirmedSlot={selected.structured_result?.confirmed_slot || "Tuesday 2:00 PM"}
                />
              )}

              {/* Human Escalation Review Brief */}
              {(selected.status === "escalated" || selected.escalation || selected.routed_office) && (
                <EscalationCard
                  packet={selected.escalation}
                  item={selected}
                  onHandled={async () => {
                    await markCaseHandled(selected.id, "Resolved by staff operator in Command Center.");
                    refresh();
                  }}
                />
              )}

              {/* Verbatim Audio & Transcript Panel */}
              {selected.transcript && (
                <div className="transcript-panel">
                  <div className="transcript-header">
                    <h4 style={{ fontSize: "15px", fontWeight: "700" }}>🎙️ Telephony Voice Transcript</h4>
                    <span style={{ fontSize: "12px", color: "var(--grey600)", fontWeight: "600" }}>
                      Authenticated CALL-E Audio Session
                    </span>
                  </div>

                  <div className="transcript-box">
                    {selected.transcript.split("\n").map((line, idx) => {
                      const isBot = line.toLowerCase().startsWith("bot:") || line.toLowerCase().startsWith("assistant:");
                      const cleanText = line.replace(/^(bot|assistant|user|recipient):\s*/i, "");

                      return (
                        <div
                          key={idx}
                          className={`transcript-bubble ${isBot ? "transcript-bubble--bot" : "transcript-bubble--user"}`}
                        >
                          <div className="transcript-speaker">
                            {isBot ? "🤖 CampusOps Phone Assistant" : "👤 Callee"}
                          </div>
                          <div>{cleanText}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="case-header-card" style={{ textAlign: "center", padding: "60px 20px" }}>
              <h3>No Operation Selected</h3>
              <p style={{ color: "var(--grey600)", margin: "8px 0 20px" }}>
                Select an operation from the queue or launch a new autonomous workflow.
              </p>
              <Link to="/">
                <PillButton variant="primary">+ Launch New Campaign</PillButton>
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
