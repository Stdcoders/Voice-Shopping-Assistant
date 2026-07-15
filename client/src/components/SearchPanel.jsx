import { useState, useEffect } from 'react';
import { API_BASE } from '../api.js';

// --- API helpers --------------------------------------------------------
async function searchProducts(filters) {
  const params = new URLSearchParams();
  if (filters.query) params.set('query', filters.query);
  if (filters.brand) params.set('brand', filters.brand);
  if (filters.minPrice) params.set('min_price', filters.minPrice);
  if (filters.maxPrice) params.set('max_price', filters.maxPrice);
  if (filters.organic) params.set('organic', 'true');

  const res = await fetch(`${API_BASE}/api/search?${params.toString()}`);
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  const data = await res.json();
  return data.results ?? [];
}

async function addProduct(product) {
  const res = await fetch(`${API_BASE}/api/parse-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript: `Add ${product.name}` }),
  });
  if (!res.ok) throw new Error(`Failed to add item (${res.status})`);
  const data = await res.json();
  return data.list;
}

// --- Component ------------------------------------------------------------
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
    <div className="panel">
      <h2>Search Products</h2>

      <form onSubmit={runSearch} className="search-form">
        <input
          type="text"
          placeholder="Search by name, e.g. apples"
          value={filters.query}
          onChange={(e) => updateFilter('query', e.target.value)}
          className="search-input"
        />
        <div className="search-filter-row">
          <input
            type="text"
            placeholder="Brand"
            value={filters.brand}
            onChange={(e) => updateFilter('brand', e.target.value)}
            className="search-input"
          />
          <input
            type="number"
            placeholder="Min $"
            value={filters.minPrice}
            onChange={(e) => updateFilter('minPrice', e.target.value)}
            className="search-input"
            min="0"
            step="0.01"
          />
          <input
            type="number"
            placeholder="Max $"
            value={filters.maxPrice}
            onChange={(e) => updateFilter('maxPrice', e.target.value)}
            className="search-input"
            min="0"
            step="0.01"
          />
          <label className="search-checkbox-label">
            <input
              type="checkbox"
              checked={filters.organic}
              onChange={(e) => updateFilter('organic', e.target.checked)}
            />
            Organic
          </label>
        </div>
        <div className="search-form-actions">
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
          <button type="button" className="btn-ghost" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </form>

      {error && <p className="panel-error">{error}</p>}

      {hasSearched && !loading && !error && results.length === 0 && (
        <p className="panel-muted">No products matched. Try different filters.</p>
      )}

      {results.length > 0 && (
        <ul className="panel-list">
          {results.map((product) => {
            const isAdded = addedNames.has(product.name);
            return (
              <li key={`${product.name}-${product.brand ?? ''}`} className="panel-item">
                <div className="panel-item-text">
                  <div className="panel-item-name">
                    {product.name}
                    {product.on_sale && <span className="badge-sale">Sale</span>}
                  </div>
                  <div className="panel-item-detail">
                    {[product.brand, product.size, product.organic && 'Organic']
                      .filter(Boolean)
                      .join(' · ')}
                    {product.price != null && ` · $${product.price.toFixed(2)}`}
                  </div>
                </div>
                <button
                  className={isAdded ? 'panel-added-label' : 'btn-primary'}
                  onClick={() => !isAdded && handleAdd(product)}
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
