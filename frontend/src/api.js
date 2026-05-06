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

// ── Analytics Endpoints ──────────────────────────────────

export async function fetchAnalyticsScorecard(creatorId) {
  const res = await fetch(`${API}/api/analytics/scorecard/${creatorId}`);
  return res.json();
}

export async function fetchAnalyticsHeatmap(creatorId) {
  const res = await fetch(`${API}/api/analytics/heatmap/${creatorId}`);
  return res.json();
}

export async function fetchAnalyticsPlatformBreakdown(creatorId) {
  const res = await fetch(`${API}/api/analytics/platform-breakdown/${creatorId}`);
  return res.json();
}

export async function fetchAnalyticsContentHistory(creatorId) {
  const res = await fetch(`${API}/api/analytics/content-history/${creatorId}`);
  return res.json();
}

export async function fetchAnalyticsTimingAudit(creatorId) {
  const res = await fetch(`${API}/api/analytics/timing-audit/${creatorId}`);
  return res.json();
}

export async function fetchAnalyticsOptimizerImpact(creatorId) {
  const res = await fetch(`${API}/api/analytics/optimizer-impact/${creatorId}`);
  return res.json();
}
