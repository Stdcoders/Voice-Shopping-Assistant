import { useState, useEffect } from 'react';

// --- API helpers --------------------------------------------------------
async function searchProducts(filters) {
  const params = new URLSearchParams();
  if (filters.query) params.set('query', filters.query);
  if (filters.brand) params.set('brand', filters.brand);
  if (filters.minPrice) params.set('min_price', filters.minPrice);
  if (filters.maxPrice) params.set('max_price', filters.maxPrice);
  if (filters.organic) params.set('organic', 'true');

  const res = await fetch(`/api/search?${params.toString()}`);
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  const data = await res.json();
  return data.results ?? [];
}

async function addProduct(product) {
  const res = await fetch('/api/parse-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript: `Add ${product.name}` }),
  });
  if (!res.ok) throw new Error(`Failed to add item (${res.status})`);
  const data = await res.json();
  return data.list;
}

// --- Component ------------------------------------------------------------
// voiceResults: results array pushed down from App.jsx when a voice/text
// command comes back with action === "search" (or null when none yet).
export default function SearchPanel({ voiceResults, onListUpdate }) {
  const [filters, setFilters] = useState({
    query: '',
    brand: '',
    minPrice: '',
    maxPrice: '',
    organic: false,
  });
  const [results, setResults] = useState(voiceResults || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(Boolean(voiceResults));
  const [addedNames, setAddedNames] = useState(() => new Set());

  // A voice/text search command landed in App.jsx — reflect it here too.
  useEffect(() => {
    if (voiceResults) {
      setResults(voiceResults);
      setHasSearched(true);
    }
  }, [voiceResults]);

  const updateFilter = (key, value) =>
    setFilters((prev) => ({ ...prev, [key]: value }));

  const runSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const data = await searchProducts(filters);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Something went wrong searching.');
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setFilters({ query: '', brand: '', minPrice: '', maxPrice: '', organic: false });
    setResults([]);
    setHasSearched(false);
    setError(null);
  };

  const handleAdd = async (product) => {
    try {
      const updatedList = await addProduct(product);
      if (onListUpdate) onListUpdate(updatedList);
      setAddedNames((prev) => new Set(prev).add(product.name));
      setTimeout(() => {
        setAddedNames((prev) => {
          const next = new Set(prev);
          next.delete(product.name);
          return next;
        });
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to add item.');
    }
  };

  return (
    <div style={styles.panel}>
      <h2 style={styles.heading}>Search Products</h2>

      <form onSubmit={runSearch} style={styles.form}>
        <input
          type="text"
          placeholder="Search by name, e.g. apples"
          value={filters.query}
          onChange={(e) => updateFilter('query', e.target.value)}
          style={styles.input}
        />
        <div style={styles.filterRow}>
          <input
            type="text"
            placeholder="Brand"
            value={filters.brand}
            onChange={(e) => updateFilter('brand', e.target.value)}
            style={{ ...styles.input, ...styles.filterInputSmall }}
          />
          <input
            type="number"
            placeholder="Min $"
            value={filters.minPrice}
            onChange={(e) => updateFilter('minPrice', e.target.value)}
            style={{ ...styles.input, ...styles.filterInputSmall }}
            min="0"
            step="0.01"
          />
          <input
            type="number"
            placeholder="Max $"
            value={filters.maxPrice}
            onChange={(e) => updateFilter('maxPrice', e.target.value)}
            style={{ ...styles.input, ...styles.filterInputSmall }}
            min="0"
            step="0.01"
          />
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={filters.organic}
              onChange={(e) => updateFilter('organic', e.target.checked)}
            />
            Organic
          </label>
        </div>
        <div style={styles.formActions}>
          <button type="submit" style={styles.searchBtn} disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
          <button type="button" style={styles.clearBtn} onClick={clearFilters}>
            Clear
          </button>
        </div>
      </form>

      {error && <p style={styles.errorText}>{error}</p>}

      {hasSearched && !loading && !error && results.length === 0 && (
        <p style={styles.muted}>No products matched. Try different filters.</p>
      )}

      {results.length > 0 && (
        <ul style={styles.list}>
          {results.map((product) => {
            const isAdded = addedNames.has(product.name);
            return (
              <li key={`${product.name}-${product.brand ?? ''}`} style={styles.card}>
                <div style={styles.cardText}>
                  <div style={styles.itemName}>
                    {product.name}
                    {product.organic && <span style={styles.badge}>Organic</span>}
                    {product.on_sale && <span style={styles.saleBadge}>On Sale</span>}
                  </div>
                  <div style={styles.details}>
                    {[product.brand, product.size].filter(Boolean).join(' · ')}
                    {product.price != null && (
                      <span style={styles.price}> · ${product.price.toFixed(2)}</span>
                    )}
                  </div>
                </div>
                <button
                  style={isAdded ? styles.addedBtn : styles.addBtn}
                  onClick={() => handleAdd(product)}
                  disabled={isAdded}
                >
                  {isAdded ? 'Added ✓' : 'Add'}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// --- Inline styles ----------------------------------------------------------
const styles = {
  panel: {
    background: '#ffffff',
    borderRadius: '12px',
    padding: '16px 18px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    marginTop: '16px',
    color: 'black'
  },
  heading: {
    margin: '0 0 12px 0',
    fontSize: '18px',
    fontWeight: 600,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '12px',
  },
  input: {
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '8px 10px',
    fontSize: '14px',
    outline: 'none',
  },
  filterRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  filterInputSmall: {
    flex: '1 1 90px',
    minWidth: '80px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '13px',
    color: 'black',
    whiteSpace: 'nowrap',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
  },
  searchBtn: {
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  clearBtn: {
    background: '#eee',
    color: '#333',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    fontSize: '14px',
    cursor: 'pointer',
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
    color: 'black',
  },
  itemName: {
    fontWeight: 500,
    fontSize: '14px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  details: {
    fontSize: '12px',
    color: '#777',
  },
  price: {
    color: '#2563eb',
    fontWeight: 500,
  },
  badge: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#166534',
    background: '#dcfce7',
    borderRadius: '4px',
    padding: '2px 6px',
  },
  saleBadge: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#9a3412',
    background: '#ffedd5',
    borderRadius: '4px',
    padding: '2px 6px',
  },
  addBtn: {
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    flexShrink: 0,
    marginLeft: '10px',
  },
  addedBtn: {
    background: '#dcfce7',
    color: '#166534',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'default',
    flexShrink: 0,
    marginLeft: '10px',
  },
  muted: {
    color: '#888',
    fontSize: '14px',
  },
  errorText: {
    color: '#c0392b',
    fontSize: '14px',
  },
};