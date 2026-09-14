import { Link, useLocation } from "react-router-dom";
import logoMark from "../assets/ringback-mark.png";

export default function ConfirmationPage() {
  const location = useLocation();
  const phone = location.state?.phone || "your number";

  return (
    <div className="page page--mobile page--centered">
      <img src={logoMark} alt="" className="brand-mark brand-mark--lg" />
      <h1 className="page-heading page-heading--center">We'll call you in about 2 minutes</h1>

      <div className="card confirmation-card">
        <p className="field-label" style={{ textAlign: "center" }}>Calling</p>
        <p className="mono confirmation-phone">{phone}</p>
      </div>

      <p className="confirmation-copy">You don't need to keep this page open.</p>
      <p className="confirmation-copy">
        If you miss the call, we try again — you won't have to start over.
      </p>

      <Link to="/" className="text-link">Ask something else →</Link>
    </div>
  );
}
