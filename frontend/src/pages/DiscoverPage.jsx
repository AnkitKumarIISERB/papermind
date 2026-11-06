import { useState, useEffect } from 'react';
import { ingestTopic, getIngestionStatus, getStats, listPapers } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DiscoverPage() {
  const [topic, setTopic] = useState('');
  const [maxPapers, setMaxPapers] = useState(200);
  const [loading, setLoading] = useState(false);
  const [ingestionStatus, setIngestionStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [papers, setPapers] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStats();
    loadPapers();
  }, []);

  // Poll ingestion status
  useEffect(() => {
    if (!ingestionStatus || ingestionStatus.status === 'done' || ingestionStatus.status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const res = await getIngestionStatus(ingestionStatus.id);
        setIngestionStatus(res.data);
        if (res.data.status === 'done') {
          loadStats();
          loadPapers();
        }
      } catch (err) {
        console.error('Status poll error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [ingestionStatus]);

  const loadStats = async () => {
    try {
      const res = await getStats();
      setStats(res.data);
    } catch (err) {
      console.error('Stats load error:', err);
    }
  };

  const loadPapers = async () => {
    try {
      const res = await listPapers(20);
      setPapers(res.data);
    } catch (err) {
      console.error('Papers load error:', err);
    }
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await ingestTopic(topic, maxPapers);
      setIngestionStatus(res.data);
      setTopic('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start ingestion');
    } finally {
      setLoading(false);
    }
  };

  const yearChartData = stats?.year_distribution
    ? Object.entries(stats.year_distribution)
        .map(([year, count]) => ({ year, count }))
        .sort((a, b) => a.year - b.year)
        .slice(-20)
    : [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Discover Research</h2>
        <p>Enter a research topic to fetch, index, and analyze academic papers from Semantic Scholar.</p>
      </div>

      {/* ── Ingest Form ────────────────────────────────────── */}
      <form onSubmit={handleIngest} className="card" style={{ marginBottom: '2rem' }}>
        <div className="input-group">
          <input
            type="text"
            className="input"
            placeholder="Enter a research topic (e.g., 'multimodal learning in healthcare')"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={loading}
          />
          <input
            type="number"
            className="input"
            style={{ maxWidth: '120px' }}
            placeholder="Max papers"
            value={maxPapers}
            onChange={(e) => setMaxPapers(parseInt(e.target.value) || 200)}
            min={10}
            max={500}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !topic.trim()}>
            {loading ? (
              <><span className="spinner" style={{ width: 16, height: 16 }}></span> Starting...</>
            ) : (
              '🔍 Fetch Papers'
            )}
          </button>
        </div>
        {error && <p style={{ color: 'var(--error)', marginTop: '0.75rem', fontSize: '0.875rem' }}>{error}</p>}
      </form>

      {/* ── Ingestion Status ───────────────────────────────── */}
      {ingestionStatus && ingestionStatus.status !== 'done' && (
        <div className="card" style={{ marginBottom: '2rem', borderColor: 'var(--accent-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="spinner"></span>
            <div>
              <strong>Indexing: </strong> &quot;{ingestionStatus.topic}&quot;
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Status: <span className="badge">{ingestionStatus.status}</span>
                {ingestionStatus.papers_found > 0 && (
                  <> · {ingestionStatus.papers_found} papers found · {ingestionStatus.papers_embedded} embedded</>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {ingestionStatus && ingestionStatus.status === 'done' && (
        <div className="card" style={{ marginBottom: '2rem', borderColor: 'var(--success)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.5rem' }}>✅</span>
            <div>
              <strong>Ingestion complete!</strong>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                {ingestionStatus.papers_found} papers fetched · {ingestionStatus.papers_embedded} embedded
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Stats ──────────────────────────────────────────── */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_papers.toLocaleString()}</div>
            <div className="stat-label">Papers Indexed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_authors.toLocaleString()}</div>
            <div className="stat-label">Authors</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_citations.toLocaleString()}</div>
            <div className="stat-label">Citation Edges</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_embeddings.toLocaleString()}</div>
            <div className="stat-label">Embeddings</div>
          </div>
        </div>
      )}

      {/* ── Year Distribution Chart ────────────────────────── */}
      {yearChartData.length > 0 && (
        <div className="chart-container" style={{ marginBottom: '2rem' }}>
          <div className="chart-title">📊 Publication Volume by Year</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={yearChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(136,136,168,0.1)" />
              <XAxis dataKey="year" stroke="var(--text-muted)" fontSize={12} />
              <YAxis stroke="var(--text-muted)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                }}
              />
              <Bar dataKey="count" fill="url(#barGradient)" radius={[4, 4, 0, 0]} />
              <defs>
                <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" />
                  <stop offset="100%" stopColor="#60a5fa" />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Top Papers ─────────────────────────────────────── */}
      {papers.length > 0 && (
        <div>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>📚 Top Papers by Citations</h3>
          <div className="search-results">
            {papers.map((paper) => (
              <div key={paper.id} className="paper-card">
                <div className="paper-title">{paper.title}</div>
                <div className="paper-meta">
                  <span>📅 {paper.year || 'N/A'}</span>
                  <span>📖 {paper.citation_count} citations</span>
                  {paper.venue && <span>🏛 {paper.venue}</span>}
                </div>
                {paper.abstract && (
                  <div className="paper-abstract">{paper.abstract}</div>
                )}
                <div className="paper-meta" style={{ marginTop: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {paper.authors?.join(', ')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Empty State ────────────────────────────────────── */}
      {!stats?.total_papers && !loading && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>
          <h3>No papers indexed yet</h3>
          <p>Enter a research topic above to get started.</p>
        </div>
      )}
    </div>
  );
}
