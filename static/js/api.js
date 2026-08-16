export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  let resp;
  try {
    resp = await fetch(path, { ...options, headers });
  } catch (err) {
    throw new ApiError("Could not reach the server.", 0, null);
  }

  let body = null;
  try {
    body = await resp.json();
  } catch (err) {
    body = null;
  }

  if (!resp.ok) {
    const message = (body && body.message) || `Request failed (${resp.status})`;
    throw new ApiError(message, resp.status, body);
  }
  return body;
}

export function apiGet(path) {
  return request(path, { method: "GET" });
}
