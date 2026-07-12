import { useState, useEffect, useCallback } from 'react';

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
  const res = await fetch('/api/recommendations');
  if (!res.ok) throw new Error(`Failed to load recommendations (${res.status})`);
  const data = await res.json();
  return data.recommendations ?? [];
}

// There's no direct "add item" endpoint — adding only happens through the
// NLP pipeline (/api/parse-text), so we build a natural-language transcript
// and let parse_command handle it exactly like a real voice/text command.
function buildAddTranscript(rec) {
  const { suggested_quantity: qty, suggested_unit: unit } = rec;
  if (qty && unit) return `Add ${qty} ${unit} of ${rec.item}`;
  if (qty) return `Add ${qty} ${rec.item}`;
  return `Add ${rec.item}`;
}

async function addItem(rec) {
  const res = await fetch('/api/parse-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript: buildAddTranscript(rec) }),
  });
  if (!res.ok) throw new Error(`Failed to add item (${res.status})`);
  const data = await res.json();
  return data.list;
}

async function dismissRecommendation(rec) {
  const res = await fetch('/api/recommendations/dismiss', {
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
      <div style={styles.panel}>
        <h2 style={styles.heading}>Suggestions</h2>
        <p style={styles.muted}>Loading suggestions…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.panel}>
        <h2 style={styles.heading}>Suggestions</h2>
        <p style={styles.errorText}>{error}</p>
        <button style={styles.retryBtn} onClick={load}>Retry</button>
      </div>
    );
  }

  if (grouped.length === 0) {
    return (
      <div style={styles.panel}>
        <h2 style={styles.heading}>Suggestions</h2>
        <p style={styles.muted}>No suggestions right now — check back after a bit more shopping history.</p>
      </div>
    );
  }

  return (
    <div style={styles.panel}>
      <h2 style={styles.heading}>Suggestions</h2>
      {grouped.map((section) => (
        <div key={section.type} style={styles.section}>
          <h3 style={styles.sectionTitle}>
            {section.meta.emoji} {section.meta.title}
          </h3>
          <ul style={styles.list}>
            {section.items.map((rec) => {
              const key = recKey(rec);
              const isPending = pendingKeys.has(key);
              return (
                <li key={key} style={styles.card}>
                  <div style={styles.cardText}>
                    <div style={styles.itemName}>{rec.item}</div>
                    {rec.reason && <div style={styles.reason}>{rec.reason}</div>}
                  </div>
                  <div style={styles.actions}>
                    <button
                      style={styles.addBtn}
                      disabled={isPending}
                      onClick={() => handleAdd(rec)}
                    >
                      {isPending ? '…' : 'Add'}
                    </button>
                    <button
                      style={styles.dismissBtn}
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

// --- Inline styles (self-contained, no CSS file needed) -------------------
const styles = {
  panel: {
    background: '#ffffff',
    borderRadius: '12px',
    padding: '16px 18px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    marginTop: '16px',
  },
  heading: {
    margin: '0 0 12px 0',
    fontSize: '18px',
    fontWeight: 600,
    color: 'black'
  },
  section: {
    marginBottom: '14px',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'red',
    margin: '0 0 8px 0',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  list: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#f7f7f8',
    borderRadius: '8px',
    padding: '10px 12px',
  },
  cardText: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: 0,
  },
  itemName: {
    fontWeight: 500,
    fontSize: '14px',
    color: 'black',
  },
  reason: {
    fontSize: '12px',
    color: '#777',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexShrink: 0,
    marginLeft: '10px',
  },
  addBtn: {
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  dismissBtn: {
    background: 'transparent',
    color: '#999',
    border: 'none',
    fontSize: '14px',
    cursor: 'pointer',
    padding: '4px 6px',
  },
  muted: {
    color: '#888',
    fontSize: '14px',
  },
  errorText: {
    color: '#c0392b',
    fontSize: '14px',
  },
  retryBtn: {
    marginTop: '8px',
    background: '#eee',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 12px',
    cursor: 'pointer',
  },
};