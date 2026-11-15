const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function handle(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return handle(res);
}

export async function postQuery(question, language = null) {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, language }),
  });
  return handle(res);
}

export async function postUpload(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  return handle(res);
}
