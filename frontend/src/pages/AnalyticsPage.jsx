import { useState, useEffect } from 'react';
import { getStats, listPapers } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, Treemap,
} from 'recharts';

const COLORS = ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#1d4ed8', '#6366f1', '#818cf8', '#38bdf8'];

export default function AnalyticsPage() {
  const [stats, setStats] = useState(null);
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, papersRes] = await Promise.all([
        getStats(),
        listPapers(200, 0, 'citation_count', 'desc'),
      ]);
      setStats(statsRes.data);
      setPapers(papersRes.data);
    } catch (err) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <span className="spinner"></span>
        Loading analytics...
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="empty-state">
        <h3>No data available</h3>
        <p>Ingest papers from the Discover page first.</p>
      </div>
    );
  }

  // Year distribution chart data
  const yearData = Object.entries(stats.year_distribution || {})
    .map(([year, count]) => ({ year: parseInt(year), count }))
    .sort((a, b) => a.year - b.year);

  // Cumulative growth
  let cumulative = 0;
  const growthData = yearData.map(d => {
    cumulative += d.count;
    return { year: d.year, total: cumulative, new: d.count };
  });

  // Top cited papers
  const topCited = papers.slice(0, 10);

  // Field of study distribution
  const fieldCounts = {};
  papers.forEach(p => {
    (p.fields_of_study || []).forEach(f => {
      fieldCounts[f] = (fieldCounts[f] || 0) + 1;
    });
  });
  const fieldData = Object.entries(fieldCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  // Open access ratio
  const openAccessCount = papers.filter(p => p.is_open_access).length;
  const closedCount = papers.length - openAccessCount;
  const accessData = [
    { name: 'Open Access', value: openAccessCount },
    { name: 'Closed', value: closedCount },
  ];

  // Venue distribution
  const venueCounts = {};
  papers.forEach(p => {
    if (p.venue) {
      const v = p.venue.length > 40 ? p.venue.substring(0, 40) + '...' : p.venue;
      venueCounts[v] = (venueCounts[v] || 0) + 1;
    }
  });
  const venueData = Object.entries(venueCounts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const tooltipStyle = {
    contentStyle: {
      background: '#111125',
      border: '1px solid rgba(124,58,237,0.2)',
      borderRadius: '10px',
      color: '#eaeaf0',
      fontSize: '0.85rem',
    },
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Research Analytics</h2>
        <p>Comprehensive analysis of your indexed paper collection — trends, distributions, and key insights.</p>
      </div>

      {/* ── Stats ──────────────────────────────────────────── */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_papers.toLocaleString()}</div>
          <div className="stat-label">Papers Indexed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_authors.toLocaleString()}</div>
          <div className="stat-label">Unique Authors</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_embeddings.toLocaleString()}</div>
          <div className="stat-label">Vector Embeddings</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{Object.keys(stats.year_distribution || {}).length}</div>
          <div className="stat-label">Year Span</div>
        </div>
      </div>

      {/* ── Charts Row 1 ───────────────────────────────────── */}
      <div className="two-col" style={{ marginBottom: '1.5rem' }}>
        <div className="chart-container">
          <div className="chart-title">📊 Publication Volume by Year</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={yearData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.08)" />
              <XAxis dataKey="year" stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {yearData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <div className="chart-title">📈 Cumulative Growth</div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={growthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.08)" />
              <XAxis dataKey="year" stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} />
              <Tooltip {...tooltipStyle} />
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="total" stroke="#2563eb" strokeWidth={2.5} fill="url(#areaGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Charts Row 2 ───────────────────────────────────── */}
      <div className="two-col" style={{ marginBottom: '1.5rem' }}>
        <div className="chart-container">
          <div className="chart-title">🔬 Fields of Study</div>
          {fieldData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={fieldData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {fieldData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip {...tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No field data available</p>
            </div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
            {fieldData.map((f, i) => (
              <span key={f.name} className="badge" style={{ background: `${COLORS[i % COLORS.length]}20`, color: COLORS[i % COLORS.length] }}>
                {f.name} ({f.value})
              </span>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-title">🔓 Access Distribution</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={accessData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                <Cell fill="#34d399" />
                <Cell fill="#5a5a78" />
              </Pie>
              <Tooltip {...tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '0.5rem', fontSize: '0.85rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#34d399', display: 'inline-block' }}></span>
              Open Access ({openAccessCount})
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#5a5a78', display: 'inline-block' }}></span>
              Closed ({closedCount})
            </span>
          </div>
        </div>
      </div>

      {/* ── Top Authors + Top Venues ───────────────────────── */}
      <div className="two-col" style={{ marginBottom: '1.5rem' }}>
        <div className="chart-container">
          <div className="chart-title">👤 Top Authors by Paper Count</div>
          <div className="author-list">
            {(stats.top_authors || []).slice(0, 10).map((a, i) => (
              <div key={i} className="author-row">
                <span>
                  <span style={{ color: 'var(--text-muted)', marginRight: '0.5rem', fontSize: '0.8rem' }}>#{i + 1}</span>
                  <span className="author-name">{a.name}</span>
                </span>
                <span className="author-count">{a.paper_count} papers</span>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <div className="chart-title">🏛️ Top Venues</div>
          {venueData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={venueData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(124,58,237,0.08)" />
                <XAxis type="number" stroke="var(--text-muted)" fontSize={11} />
                <YAxis type="category" dataKey="name" width={180} stroke="var(--text-muted)" fontSize={10} tick={{ fill: 'var(--text-secondary)' }} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {venueData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>No venue data</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Most Cited Papers ──────────────────────────────── */}
      <div className="chart-container">
        <div className="chart-title">🏆 Top 10 Most Cited Papers</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {topCited.map((p, i) => (
            <div key={p.id} className="author-row" style={{ padding: '0.75rem 1rem' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span style={{ color: 'var(--accent-secondary)', fontWeight: 800, fontSize: '0.85rem' }}>#{i + 1}</span>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {p.title}
                  </span>
                </div>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {p.year} · {p.venue || 'Unknown venue'}
                </span>
              </div>
              <div style={{ textAlign: 'right', minWidth: '80px' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-secondary)' }}>
                  {p.citation_count.toLocaleString()}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>citations</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
