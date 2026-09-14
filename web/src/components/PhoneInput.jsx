import { useState, useRef, useEffect, useMemo } from "react";

// Backend-owned list (app/data/countries.json via GET /api/countries), not
// hardcoded here - CALL-E has already expanded its supported-region list
// once during this project, and a second frontend copy would silently
// drift from the real one the next time it does. Field names below match
// that API's shape (code, calling_code, line_region), not a local dataset.

function Flag({ code }) {
  return (
    <img
      src={`https://flagcdn.com/w40/${code.toLowerCase()}.png`}
      alt=""
      width={22}
      height={16}
      style={{ borderRadius: 2, objectFit: "cover", flexShrink: 0 }}
      onError={(e) => {
        e.currentTarget.style.visibility = "hidden";
      }}
    />
  );
}

export default function PhoneInput({
  countries,
  countryCode,
  onCountryChange,
  number,
  onNumberChange,
  error,
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(0);
  const wrapRef = useRef(null);
  const searchRef = useRef(null);
  const listRef = useRef(null);

  const country = countries.find((c) => c.code === countryCode) || countries[0];

  const results = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return countries;
    return countries.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q) ||
        c.calling_code.includes(q.replace(/^\+/, ""))
    );
  }, [search, countries]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  useEffect(() => {
    if (open && country) {
      setSearch("");
      setActive(Math.max(0, countries.findIndex((c) => c.code === country.code)));
      requestAnimationFrame(() => searchRef.current?.focus());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.children[active];
    if (el) el.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const select = (c) => {
    onCountryChange(c.code);
    setOpen(false);
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[active]) select(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  if (!country) return null;

  const rowBase = {
    display: "flex",
    alignItems: "center",
    gap: 10,
    width: "100%",
    padding: "10px 12px",
    border: "none",
    background: "transparent",
    textAlign: "left",
    cursor: "pointer",
    fontSize: 15,
    fontFamily: "var(--font-body)",
    color: "var(--ink)",
  };

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <div
        style={{
          display: "flex",
          border: `1px solid ${error ? "var(--red)" : "var(--border)"}`,
          borderRadius: "var(--r-input)",
          overflow: "hidden",
          background: "var(--card)",
        }}
      >
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={`Country: ${country.name}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            padding: "0 12px",
            border: "none",
            borderRight: "1px solid var(--border)",
            background: open ? "var(--canvas)" : "transparent",
            cursor: "pointer",
            fontSize: 14,
            fontFamily: "var(--font-body)",
            color: "var(--ink)",
            flexShrink: 0,
          }}
        >
          <Flag code={country.code} />
          <span style={{ fontFamily: "var(--font-mono)" }}>{country.code}</span>
          <svg width="10" height="6" viewBox="0 0 10 6" aria-hidden="true">
            <path d="M1 1l4 4 4-4" stroke="var(--grey600)" strokeWidth="1.5" fill="none" />
          </svg>
        </button>

        <span
          style={{
            display: "flex",
            alignItems: "center",
            paddingLeft: 12,
            fontFamily: "var(--font-mono)",
            fontSize: 15,
            color: "var(--grey600)",
            flexShrink: 0,
          }}
        >
          (+{country.calling_code})
        </span>

        <input
          type="tel"
          inputMode="tel"
          value={number}
          onChange={(e) => onNumberChange(e.target.value)}
          placeholder="000 000 000"
          aria-label="Phone number"
          style={{
            flex: 1,
            minWidth: 0,
            border: "none",
            outline: "none",
            background: "transparent",
            padding: "13px 12px",
            fontFamily: "var(--font-mono)",
            fontSize: 15,
            color: "var(--ink)",
          }}
        />
      </div>

      {country.line_region === "international" && (
        <p style={{ margin: "6px 2px 0", fontSize: 12, color: "var(--grey600)" }}>
          Calls to {country.name} arrive from an international number.
        </p>
      )}

      {error && <p style={{ margin: "6px 2px 0", fontSize: 13, color: "var(--red)" }}>{error}</p>}

      {open && (
        <div
          style={{
            position: "absolute",
            zIndex: 40,
            top: "calc(100% + 6px)",
            left: 0,
            width: 320,
            maxWidth: "100%",
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <div style={{ padding: 10, borderBottom: "1px solid var(--border)" }}>
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setActive(0);
              }}
              onKeyDown={onKeyDown}
              placeholder="Search country"
              aria-label="Search country"
              style={{
                width: "100%",
                boxSizing: "border-box",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-input)",
                outline: "none",
                padding: "9px 11px",
                fontFamily: "var(--font-body)",
                fontSize: 14,
                color: "var(--ink)",
                background: "var(--canvas)",
              }}
            />
          </div>

          <div ref={listRef} role="listbox" style={{ maxHeight: 260, overflowY: "auto", padding: 4 }}>
            {results.map((c, i) => {
              const selected = c.code === country.code;
              return (
                <button
                  key={c.code}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => select(c)}
                  onMouseEnter={() => setActive(i)}
                  style={{
                    ...rowBase,
                    borderRadius: 8,
                    background: i === active ? "var(--red-tint)" : "transparent",
                    color: i === active ? "var(--red)" : "var(--ink)",
                  }}
                >
                  <Flag code={c.code} />
                  <span style={{ flex: 1 }}>{c.name}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--grey600)" }}>
                    +{c.calling_code}
                  </span>
                </button>
              );
            })}

            {results.length === 0 && (
              <p style={{ padding: "14px 12px", margin: 0, fontSize: 14, color: "var(--grey600)" }}>
                No supported country matches that.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Strips formatting and any national trunk prefix, then returns E.164.
// "081 234 5678" with NA selected -> "+264812345678"
export function toE164(country, raw) {
  let digits = String(raw).replace(/\D/g, "");
  if (digits.startsWith("0")) digits = digits.replace(/^0+/, "");
  return `+${country.calling_code}${digits}`;
}

// Deliberately loose: national number lengths vary from 7 to 11 digits
// across these 42 countries. Catch obvious typos, don't reject valid
// foreign numbers.
export function validateNumber(raw) {
  const digits = String(raw).replace(/\D/g, "").replace(/^0+/, "");
  if (digits.length === 0) return "Enter a phone number.";
  if (digits.length < 7) return "That number looks too short.";
  if (digits.length > 12) return "That number looks too long.";
  return null;
}
