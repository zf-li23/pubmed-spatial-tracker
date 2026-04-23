const rawBase = import.meta.env.VITE_API_BASE || '';

// Normalize trailing slash so callers can pass path strings like '/api/articles'.
export const API_BASE = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase;

export function apiPath(path) {
  return `${API_BASE}${path}`;
}
