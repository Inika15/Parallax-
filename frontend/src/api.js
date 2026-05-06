const API = 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API}/api/health`);
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API}/api/stats`);
  return res.json();
}

export async function fetchRecommendations(limit = 100) {
  const res = await fetch(`${API}/api/recommendations?limit=${limit}`);
  return res.json();
}

export async function fetchHeatmap() {
  const res = await fetch(`${API}/api/heatmap`);
  return res.json();
}

export async function fetchCreators() {
  const res = await fetch(`${API}/api/creators`);
  return res.json();
}

export async function fetchCreator(id) {
  const res = await fetch(`${API}/api/creators/${id}`);
  return res.json();
}

export async function fetchCreatorHeatmap(id, contentType = 'SHORT') {
  const res = await fetch(`${API}/api/creators/${id}/heatmap?content_type=${contentType}`);
  return res.json();
}

export async function runOptimizer(data) {
  const res = await fetch(`${API}/api/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchCounterfactual(contentId) {
  const res = await fetch(`${API}/api/counterfactual/${contentId}`);
  return res.json();
}
