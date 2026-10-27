// Minimal API client with token auth stored in localStorage.

// Configurable for deployment (Vercel/Docker); defaults to local dev.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getToken = () => localStorage.getItem("kinesis_token");
export const getUserId = () => localStorage.getItem("kinesis_uid");
export const isAuthed = () => !!getToken();
export function logout() {
  localStorage.removeItem("kinesis_token");
  localStorage.removeItem("kinesis_uid");
}

async function req(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

export async function login(email, password) {
  const data = await req("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem("kinesis_token", data.access_token);
  const me = await req("/users/me");
  localStorage.setItem("kinesis_uid", String(me.id));
  return me;
}

export const startSession = (exercise, target_sets = 3, reps_per_set = 10) =>
  req("/sessions/start", {
    method: "POST",
    body: JSON.stringify({ exercise, target_sets, reps_per_set }),
  });

export const getSessions = () => req("/sessions?limit=100");
export const getCommonErrors = (uid) => req(`/users/${uid}/common-errors`);
export const getTempoHistory = (uid) => req(`/users/${uid}/tempo-history`);
export const getCorrective = (code) => req(`/correctives/${code}`);
export const getSessionDetail = (id) => req(`/sessions/${id}/detail`);
