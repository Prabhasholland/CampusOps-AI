import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import FieldLabel from "../components/FieldLabel";
import MonoValue from "../components/MonoValue";
import Panel from "../components/Panel";
import PhoneInput from "../components/PhoneInput";
import PillButton from "../components/PillButton";
import logoMark from "../assets/ringback-mark.png";
import { createCase, listCountries } from "../api";

const PRESET_TEMPLATES = [
  {
    id: "scholarship_verify",
    icon: "🎓",
    title: "1. Scholarship Status Verification",
    desc: "Autonomous verification loop with Financial Aid Bureau to extract payment clearance & release dates.",
    query: "A student's scholarship is delayed. Find out the status, release date, and resolve it.",
    caller_name: "Tunga Amutenya",
    student_number: "220012345",
    phone: "+264811234567",
    country_code: "NA",
    workflow_type: "verification",
    badge: "Auto-Resolve",
  },
  {
    id: "multi_party",
    icon: "🤝",
    title: "2. 3-Way Advising Coordination",
    desc: "Sequential 3-way calling between Student, Faculty Advisor, and Dept Office to negotiate common slot.",
    query: "Schedule an academic advising meeting between the student, faculty advisor Dr. Johannes Alweendo, and FCI department office.",
    caller_name: "Maria Nghipandulwa",
    student_number: "220023456",
    phone: "+264812345678",
    country_code: "NA",
    workflow_type: "coordination",
    badge: "3-Way Matrix",
  },
  {
    id: "live_call_telangana",
    icon: "📞",
    title: "3. Live Phone Call (+917671900357)",
    desc: "Dispatches a real phone call to +917671900357 in Telangana, India to verify operational inquiry.",
    query: "Call student regarding scholarship eligibility and bursary verification in Telangana.",
    caller_name: "Operations Officer",
    student_number: "220012345",
    phone: "+917671900357",
    country_code: "IN",
    workflow_type: "verification",
    badge: "Live CALL-E",
  },
  {
    id: "escalation_flow",
    icon: "🚨",
    title: "4. Policy Hold Escalation Loop",
    desc: "Tests policy blocked verification that automatically constructs a rich human review packet.",
    query: "Verify financial aid release for student Josef Kambala regarding delayed allowance.",
    caller_name: "Josef Kambala",
    student_number: "220034567",
    phone: "+264813456789",
    country_code: "NA",
    workflow_type: "verification",
    badge: "Staff Escalation",
  },
];

export default function IntakePage() {
  const navigate = useNavigate();
  const [countries, setCountries] = useState(null);
  const [countryCode, setCountryCode] = useState("IN");
  const [phone, setPhone] = useState("+917671900357");
  const [callerName, setCallerName] = useState("Operations Officer");
  const [studentNumber, setStudentNumber] = useState("220012345");
  const [query, setQuery] = useState("Call student regarding scholarship eligibility and bursary verification in Telangana.");
  const [workflowType, setWorkflowType] = useState("verification");
  const [selectedTemplateId, setSelectedTemplateId] = useState("live_call_telangana");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listCountries()
      .then((data) => setCountries(data))
      .catch(() => {});
  }, []);

  function applyTemplate(tpl) {
    setSelectedTemplateId(tpl.id);
    setQuery(tpl.query);
    setCallerName(tpl.caller_name);
    setStudentNumber(tpl.student_number);
    setPhone(tpl.phone);
    if (tpl.country_code) {
      setCountryCode(tpl.country_code);
    }
    setWorkflowType(tpl.workflow_type);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);

    try {
      const res = await createCase({
        phone: phone.trim(),
        country_code: countryCode,
        query: query.trim(),
        caller_name: callerName.trim(),
        student_number: studentNumber.trim() || null,
        workflow_type: workflowType,
        tenant_id: "nust",
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }

      const created = await res.json();
      navigate(`/dashboard`);
    } catch (err) {
      setError(err.message || "Failed to dispatch autonomous workflow.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page--intake">
      {/* Top Bar */}
      <header className="top-bar">
        <div className="brand-row">
          <div className="brand-mark-box">
            <img src={logoMark} alt="CampusOps AI" className="brand-mark" />
          </div>
          <div className="brand-titles">
            <span className="brand-name">
              CampusOps AI
              <span className="tenant-badge">1-Click Launchpad</span>
            </span>
            <span className="brand-tagline">Autonomous Multi-Agent Phone Operations</span>
          </div>
        </div>

        <div className="top-bar__right">
          <Link to="/dashboard">
            <PillButton variant="secondary">
              ← View Operations Queue
            </PillButton>
          </Link>
        </div>
      </header>

      {/* Hero Header */}
      <div className="intake-hero">
        <h1 className="intake-hero__title">Autonomous Phone Campaign Launchpad</h1>
        <p className="intake-hero__subtitle">
          Select an institutional workflow template below or define a custom operational inquiry.
          CampusOps AI will plan multi-step calls, verify facts via CALL-E, and resolve or escalate.
        </p>
      </div>

      {/* Preset Cards Gallery */}
      <div className="template-cards-grid">
        {PRESET_TEMPLATES.map((tpl) => {
          const isSelected = selectedTemplateId === tpl.id;
          return (
            <div
              key={tpl.id}
              className={`template-card ${isSelected ? "template-card--selected" : ""}`}
              onClick={() => applyTemplate(tpl)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="template-card__icon">{tpl.icon}</div>
                <span
                  style={{
                    fontSize: "10.5px",
                    fontWeight: "700",
                    background: isSelected ? "var(--primary)" : "var(--canvas-subtle)",
                    color: isSelected ? "#ffffff" : "var(--grey600)",
                    padding: "3px 8px",
                    borderRadius: "12px",
                  }}
                >
                  {tpl.badge}
                </span>
              </div>
              <h3 className="template-card__title">{tpl.title}</h3>
              <p className="template-card__desc">{tpl.desc}</p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                <span className="template-card__pill">
                  {isSelected ? "● Selected" : "Click to select"}
                </span>
                <span style={{ fontSize: "11px", color: "var(--grey400)", fontFamily: "var(--font-mono)" }}>
                  {tpl.phone}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Intake Form Panel */}
      <div className="intake-form-panel">
        <form onSubmit={handleSubmit}>
          {error && (
            <div
              style={{
                background: "var(--red-tint)",
                border: "1px solid var(--red-border)",
                color: "var(--red-deep)",
                padding: "12px 16px",
                borderRadius: "var(--r-input)",
                marginBottom: "20px",
                fontSize: "13.5px",
              }}
            >
              <b>Error:</b> {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">1. Operational Inquiry / Task Instruction</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the institutional operational inquiry or coordination goal..."
              required
            />
          </div>

          <div className="form-row--2">
            <div className="form-group">
              <label className="form-label">2. Target Role / Caller Name</label>
              <input
                type="text"
                className="form-input"
                value={callerName}
                onChange={(e) => setCallerName(e.target.value)}
                placeholder="e.g. Maria Nghipandulwa"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">3. Student Record Number (Optional)</label>
              <input
                type="text"
                className="form-input"
                value={studentNumber}
                onChange={(e) => setStudentNumber(e.target.value)}
                placeholder="e.g. 220012345"
              />
            </div>
          </div>

          <div className="form-row--2">
            <div className="form-group">
              <label className="form-label">4. Target Phone Number (E.164)</label>
              <input
                type="text"
                className="form-input"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="e.g. +917671900357"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">5. Workflow State Machine</label>
              <select
                className="form-input"
                value={workflowType}
                onChange={(e) => setWorkflowType(e.target.value)}
              >
                <option value="verification">Verification Workflow (Financial Aid / Bursary)</option>
                <option value="coordination">Coordination Workflow (3-Way Academic Advising)</option>
                <option value="escalation">Escalation Workflow (Policy Hold / Exception)</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: "28px" }}>
            <button
              type="submit"
              className="submit-workflow-btn"
              disabled={busy}
            >
              {busy ? (
                <>
                  <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⚙️</span>
                  Planning & Dispatching Call via CALL-E...
                </>
              ) : (
                <>
                  <span>🚀</span> Dispatch Autonomous Phone Campaign
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
