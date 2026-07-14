import { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../api.js';

// --- Config: section metadata per recommendation type -----------------
const SECTION_META = {
  running_low: { title: 'Running Low', emoji: '🔄' },
  frequently_bought_together: { title: 'Frequently Bought Together', emoji: '🛒' },
  seasonal: { title: 'Seasonal Picks', emoji: '🍂' },
  substitute: { title: 'Try Instead', emoji: '🔀' },
  cold_start: { title: 'You Might Need', emoji: '✨' },
};
const SECTION_ORDER = ['running_low', 'frequently_bought_together', 'seasonal', 'substitute', 'cold_start'];

// --- API helpers --------------------------------------------------------
async function fetchRecommendations() {
  const res = await fetch(`${API_BASE}/api/recommendations`);
  if (!res.ok) throw new Error(`Failed to load recommendations (${res.status})`);
  const data = await res.json();
  return data.recommendations ?? [];
}

function buildAddTranscript(rec) {
  const { suggested_quantity: qty, suggested_unit: unit } = rec;
  if (qty && unit) return `Add ${qty} ${unit} of ${rec.item}`;
  if (qty) return `Add ${qty} ${rec.item}`;
  return `Add ${rec.item}`;
}

async function addItem(rec) {
  const res = await fetch(`${API_BASE}/api/parse-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript: buildAddTranscript(rec) }),
  });
  if (!res.ok) throw new Error(`Failed to add item (${res.status})`);
  const data = await res.json();
  return data.list;
}

async function dismissRecommendation(rec) {
  const res = await fetch(`${API_BASE}/api/recommendations/dismiss`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item: rec.item }),
  });
  if (!res.ok) throw new Error(`Failed to dismiss recommendation (${res.status})`);
  return res.json();
}

// --- Component ------------------------------------------------------------
export default function RecommendationsPanel({ onListUpdate }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingKeys, setPendingKeys] = useState(() => new Set());

  const recKey = (rec) => `${rec.type}:${rec.item}`;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecommendations();
      setRecommendations(data);
    } catch (err) {
      setError(err.message || 'Something went wrong loading suggestions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const withPending = async (rec, action) => {
    const key = recKey(rec);
    setPendingKeys((prev) => new Set(prev).add(key));
    try {
      await action();
      setRecommendations((prev) => prev.filter((r) => recKey(r) !== key));
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setPendingKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  const handleAdd = (rec) =>
    withPending(rec, async () => {
      const updatedList = await addItem(rec);
      if (onListUpdate) onListUpdate(updatedList);
    });

  const handleDismiss = (rec) =>
    withPending(rec, async () => {
      await dismissRecommendation(rec);
    });

  const grouped = SECTION_ORDER
    .map((type) => ({
      type,
      meta: SECTION_META[type],
      items: recommendations.filter((r) => r.type === type),
    }))
    .filter((section) => section.items.length > 0);

  if (loading) {
    return (
      <div className="panel">
        <h2>Suggestions</h2>
        <p className="panel-muted">Loading suggestions…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <h2>Suggestions</h2>
        <p className="panel-error">{error}</p>
        <button className="btn-ghost" onClick={load}>Retry</button>
      </div>
    );
  }

  if (grouped.length === 0) {
    return (
      <div className="panel">
        <h2>Suggestions</h2>
        <p className="panel-muted">No suggestions right now — check back after a bit more shopping history.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Suggestions</h2>
      {grouped.map((section) => (
        <div key={section.type} className="panel-section">
          <h3 className="panel-section-heading">
            {section.meta.emoji} {section.meta.title}
          </h3>
          <ul className="panel-list">
            {section.items.map((rec) => {
              const key = recKey(rec);
              const isPending = pendingKeys.has(key);
              return (
                <li key={key} className="panel-item">
                  <div className="panel-item-text">
                    <div className="panel-item-name">{rec.item}</div>
                    {rec.reason && <div className="panel-item-detail">{rec.reason}</div>}
                  </div>
                  <div className="panel-item-actions">
                    <button
                      className="btn-primary"
                      disabled={isPending}
                      onClick={() => handleAdd(rec)}
                    >
                      {isPending ? '…' : 'Add'}
                    </button>
                    <button
                      className="btn-dismiss"
                      disabled={isPending}
                      onClick={() => handleDismiss(rec)}
                      aria-label={`Dismiss ${rec.item}`}
                    >
                      ✕
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
