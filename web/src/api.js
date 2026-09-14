const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options);
  return res;
}

export async function listCases(tenantId = "nust", workflowType = null, status = null) {
  const params = new URLSearchParams({ tenant_id: tenantId });
  if (workflowType) params.append("workflow_type", workflowType);
  if (status) params.append("status", status);

  const res = await request(`/api/cases?${params.toString()}`);
  if (!res.ok) throw new Error("Could not load operational cases.");
  return res.json();
}

export async function getCase(caseId) {
  const res = await request(`/api/cases/${caseId}`);
  if (!res.ok) throw new Error("Case not found.");
  return res.json();
}

export async function createCase(payload) {
  return request("/api/workflows/dispatch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function dispatchWorkflow(payload) {
  return createCase(payload);
}

export async function listCountries() {
  const res = await request("/api/countries");
  if (!res.ok) throw new Error("Could not load country list.");
  return res.json();
}

export async function listOffices(tenantId = "nust") {
  const res = await request(`/api/directory/offices?tenant_id=${encodeURIComponent(tenantId)}`);
  if (!res.ok) throw new Error("Could not load office list.");
  return res.json();
}

export async function listFaculty() {
  const res = await request("/api/directory/faculty");
  if (!res.ok) throw new Error("Could not load faculty directory.");
  return res.json();
}

export async function getStats(tenantId = "nust") {
  const res = await request(`/api/stats?tenant_id=${encodeURIComponent(tenantId)}`);
  if (!res.ok) throw new Error("Could not load operational metrics.");
  return res.json();
}

export async function routeCase(caseId, officeKey, reason = "") {
  const res = await request(`/api/cases/${caseId}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ office_key: officeKey, reason }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Could not route this case.");
  }
  return res.json();
}

export async function markCaseHandled(caseId, note = "") {
  const res = await request(`/api/cases/${caseId}/mark-handled`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Could not mark this case handled.");
  }
  return res.json();
}
