const API = 'http://localhost:8000';

// ── Safe fetch wrapper with error handling ──────────────
async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      console.error(`API Error: ${res.status} for ${url}`);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error(`Fetch failed for ${url}:`, err.message);
    return null;
  }
}

export async function fetchHealth() {
  return safeFetch(`${API}/api/health`);
}

export async function fetchStats() {
  return safeFetch(`${API}/api/stats`);
}

export async function fetchRecommendations(limit = 100) {
  const data = await safeFetch(`${API}/api/recommendations?limit=${limit}`);
  return data || [];
}

export async function fetchHeatmap() {
  return safeFetch(`${API}/api/heatmap`);
}

export async function fetchCreators() {
  const data = await safeFetch(`${API}/api/creators`);
  return data || [];
}

export async function fetchCreator(id) {
  return safeFetch(`${API}/api/creators/${id}`);
}

export async function fetchCreatorHeatmap(id, contentType = 'SHORT') {
  return safeFetch(`${API}/api/creators/${id}/heatmap?content_type=${contentType}`);
}

export async function runOptimizer(data) {
  try {
    const res = await fetch(`${API}/api/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return await res.json();
  } catch (err) {
    console.error('Optimizer failed:', err.message);
    return { error: err.message };
  }
}

export async function fetchCounterfactual(contentId) {
  return safeFetch(`${API}/api/counterfactual/${contentId}`);
}

// ── Analytics Endpoints ──────────────────────────────────

export async function fetchAnalyticsScorecard(creatorId) {
  return safeFetch(`${API}/api/analytics/scorecard/${creatorId}`);
}

export async function fetchAnalyticsHeatmap(creatorId) {
  return safeFetch(`${API}/api/analytics/heatmap/${creatorId}`);
}

export async function fetchAnalyticsPlatformBreakdown(creatorId) {
  return safeFetch(`${API}/api/analytics/platform-breakdown/${creatorId}`);
}

export async function fetchAnalyticsContentHistory(creatorId) {
  const data = await safeFetch(`${API}/api/analytics/content-history/${creatorId}`);
  return data || [];
}

export async function fetchAnalyticsTimingAudit(creatorId) {
  return safeFetch(`${API}/api/analytics/timing-audit/${creatorId}`);
}

export async function fetchAnalyticsOptimizerImpact(creatorId) {
  return safeFetch(`${API}/api/analytics/optimizer-impact/${creatorId}`);
}
