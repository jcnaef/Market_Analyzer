import { auth } from "./config/firebase";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function getAuthHeaders() {
  const user = auth.currentUser;
  if (!user) return {};
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, options);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function authRequest(url, options = {}) {
  const authHeaders = await getAuthHeaders();
  const headers = { ...options.headers, ...authHeaders };
  return request(url, { ...options, headers });
}

// --- Public endpoints (no auth required) ---

export function getDashboardStats() {
  return request("/api/dashboard/stats");
}

export function getJobs(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "" && v !== false) qs.set(k, v);
  }
  return request(`/api/jobs?${qs}`);
}

export function getJobById(jobId) {
  return request(`/api/jobs/${jobId}`);
}

export function getSalaryInsights(groupBy = "level", names = []) {
  const qs = new URLSearchParams({ group_by: groupBy });
  if (names.length > 0) qs.set("names", names.join(","));
  return request(`/api/salary/insights?${qs}`);
}

export function analyzeSkillGap(knownSkills) {
  return request("/api/skill-gap/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ known_skills: knownSkills }),
  });
}

export function analyzeResume(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/api/resume/analyze", { method: "POST", body: form });
}

export function getFilterLevels() {
  return request("/api/filters/levels");
}

export function getFilterLocations() {
  return request("/api/filters/locations");
}

export function getSkillCorrelations(skill) {
  return request(`/skill/${encodeURIComponent(skill)}`);
}

export function getLocationTrends(city) {
  return request(`/location/${encodeURIComponent(city)}`);
}

export function getSkillAutocomplete(q, limit = 8) {
  return request(`/skills/autocomplete?q=${encodeURIComponent(q)}&limit=${limit}`);
}

export function getLocationAutocomplete(q, limit = 8) {
  return request(`/locations/autocomplete?q=${encodeURIComponent(q)}&limit=${limit}`);
}

// --- Authenticated endpoints ---

export function getUserMe() {
  return authRequest("/api/user/me");
}

export function uploadResume(file) {
  const form = new FormData();
  form.append("file", file);
  return authRequest("/api/user/resume/upload", { method: "POST", body: form });
}

export function saveResume(resumeData) {
  return authRequest("/api/user/resume", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(resumeData),
  });
}

export function getResume() {
  return authRequest("/api/user/resume");
}

export function suggestSkills(jobDescription, userSkills) {
  return request("/api/suggest-skills", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription, user_skills: userSkills }),
  });
}

export function tailorSection(data) {
  return authRequest("/api/tailor-section", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
