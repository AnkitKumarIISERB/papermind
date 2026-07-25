import { useState } from 'react';
import { searchPapers } from '../api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [yearMin, setYearMin] = useState('');
  const [yearMax, setYearMax] = useState('');
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);

    try {
      const res = await searchPapers(
        query, 
        20,
        yearMin ? parseInt(yearMin) : null,
        yearMax ? parseInt(yearMax) : null
      );
      setResults(res.data);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Semantic Search</h2>
        <p>Search papers by meaning, not just keywords. Powered by pgvector cosine similarity.</p>
      </div>

      <form onSubmit={handleSearch} className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="input-group">
          <input
            type="text"
            className="input"
            placeholder="Search by meaning (e.g., 'methods for fusing audio and text features')"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }}></span> : '🔍'} Search
          </button>
        </div>
        <div className="input-group" style={{ marginTop: '0.75rem', maxWidth: '400px' }}>
          <input
            type="number"
            className="input"
            placeholder="Year from"
            value={yearMin}
            onChange={(e) => setYearMin(e.target.value)}
            style={{ maxWidth: '160px' }}
          />
          <input
            type="number"
            className="input"
            placeholder="Year to"
            value={yearMax}
            onChange={(e) => setYearMax(e.target.value)}
            style={{ maxWidth: '160px' }}
          />
        </div>
      </form>

      {loading && (
        <div className="loading">
          <span className="spinner"></span>
          Searching across paper embeddings...
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="search-results">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            Found {results.length} results ranked by semantic similarity
          </p>
          {results.map((paper, idx) => (
            <div key={paper.id} className="paper-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <div className="paper-title">
                    <span style={{ color: 'var(--text-muted)', marginRight: '0.5rem' }}>#{idx + 1}</span>
                    {paper.url ? (
                      <a href={paper.url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>
                        {paper.title}
                      </a>
                    ) : paper.title}
                  </div>
                  <div className="paper-meta">
                    <span>📅 {paper.year || 'N/A'}</span>
                    <span>📖 {paper.citation_count} citations</span>
                    {paper.venue && <span>🏛 {paper.venue}</span>}
                    <span>👤 {paper.authors}</span>
                    {paper.is_open_access && <span className="badge-success" style={{ padding: '0.15rem 0.5rem', borderRadius: '999px', background: 'rgba(52,211,153,0.15)', color: 'var(--success)', fontSize: '0.7rem' }}>Open Access</span>}
                  </div>
                  {paper.abstract && (
                    <div className="paper-abstract">{paper.abstract}</div>
                  )}
                </div>
                <div style={{ textAlign: 'right', minWidth: '80px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Similarity</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-secondary)' }}>
                    {(paper.similarity * 100).toFixed(1)}%
                  </div>
                  <div className="similarity-bar" style={{ marginTop: '0.25rem' }}>
                    <div className="similarity-fill" style={{ width: `${paper.similarity * 100}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="empty-state">
          <h3>No results found</h3>
          <p>Try a different query or ingest more papers from the Discover page.</p>
        </div>
      )}

      {!searched && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <h3>Enter a search query</h3>
          <p>Semantic search finds papers by meaning, not just keyword matching.</p>
        </div>
      )}
    </div>
  );
}
