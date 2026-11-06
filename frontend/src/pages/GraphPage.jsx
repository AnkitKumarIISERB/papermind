import { useState, useEffect, useRef } from 'react';
import { getCitationGraph } from '../api';

export default function GraphPage() {
  const graphRef = useRef(null);
  const networkRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [minCitations, setMinCitations] = useState(0);
  const [nodeCount, setNodeCount] = useState(150);
  const [threshold, setThreshold] = useState(0.55);

  useEffect(() => {
    loadGraph();
  }, []);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const res = await getCitationGraph(minCitations, nodeCount, threshold);
      setGraphData(res.data);
      renderGraph(res.data);
    } catch (err) {
      console.error('Graph load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = async (data) => {
    if (!graphRef.current || data.nodes.length === 0) return;

    const { Network } = await import('vis-network');
    const { DataSet } = await import('vis-data');

    // Color nodes by year
    const years = data.nodes.map(n => n.year).filter(Boolean);
    const minYear = Math.min(...years) || 2000;
    const maxYear = Math.max(...years) || 2026;
    const yearRange = maxYear - minYear || 1;

    const getNodeColor = (year) => {
      if (!year) return '#5a5a78';
      const ratio = (year - minYear) / yearRange;
      // Purple → Cyan gradient for beautiful effect
      const r = Math.round(124 * (1 - ratio) + 34 * ratio);
      const g = Math.round(58 * (1 - ratio) + 211 * ratio);
      const b = Math.round(237 * (1 - ratio) + 238 * ratio);
      return `rgb(${r}, ${g}, ${b})`;
    };

    const getNodeSize = (citationCount) => {
      const base = 8;
      const scale = Math.log2((citationCount || 1) + 1) * 3;
      return Math.min(base + scale, 50);
    };

    const nodes = new DataSet(
      data.nodes.map(n => ({
        id: n.id,
        label: '',
        title: `${n.title}\n\nAuthors: ${n.authors}\nYear: ${n.year || 'N/A'}\nCitations: ${n.citationCount}`,
        size: getNodeSize(n.citationCount),
        color: {
          background: getNodeColor(n.year),
          border: getNodeColor(n.year),
          highlight: { background: '#fff', border: '#2563eb' },
          hover: { background: '#60a5fa', border: '#2563eb' },
        },
        _data: n,
      }))
    );

    const edges = new DataSet(
      data.edges.map((e, i) => ({
        id: i,
        from: e.from,
        to: e.to,
        color: {
          color: `rgba(37,99,235,${Math.min((e.similarity || 0.5) * 0.5, 0.3)})`,
          highlight: '#2563eb',
          hover: '#60a5fa',
        },
        width: (e.similarity || 0.5) * 2,
        smooth: { type: 'continuous' },
      }))
    );

    const options = {
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.008,
          springLength: 100,
          springConstant: 0.04,
          damping: 0.4,
        },
        stabilization: { iterations: 200, updateInterval: 25 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        zoomView: true,
        dragView: true,
      },
      nodes: {
        shape: 'dot',
        borderWidth: 2,
        shadow: { enabled: true, color: 'rgba(124,58,237,0.2)', size: 8 },
      },
      edges: {
        width: 0.8,
      },
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    const network = new Network(graphRef.current, { nodes, edges }, options);
    networkRef.current = network;

    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = data.nodes.find(n => n.id === nodeId);
        setSelectedNode(node);
      } else {
        setSelectedNode(null);
      }
    });
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Knowledge Graph</h2>
        <p>Semantic similarity network — papers with similar research topics are connected. Node size = citations, color = year (blue→cyan).</p>
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: '1rem', display: 'flex', gap: '1.25rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Min citations:
          <input
            type="number"
            className="input"
            style={{ width: '80px', marginLeft: '0.5rem', padding: '0.4rem 0.6rem' }}
            value={minCitations}
            onChange={(e) => setMinCitations(parseInt(e.target.value) || 0)}
            min={0}
          />
        </label>
        <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Max nodes:
          <input
            type="number"
            className="input"
            style={{ width: '80px', marginLeft: '0.5rem', padding: '0.4rem 0.6rem' }}
            value={nodeCount}
            onChange={(e) => setNodeCount(parseInt(e.target.value) || 150)}
            min={10}
            max={500}
          />
        </label>
        <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Similarity:
          <input
            type="range"
            min="0.3"
            max="0.9"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            style={{ marginLeft: '0.5rem', width: '100px', accentColor: '#2563eb' }}
          />
          <span className="mono" style={{ marginLeft: '0.35rem', color: 'var(--accent-secondary)' }}>{threshold.toFixed(2)}</span>
        </label>
        <button className="btn btn-primary btn-sm" onClick={loadGraph}>
          🔄 Refresh
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <span><strong style={{ color: 'var(--accent-secondary)' }}>{graphData.nodes.length}</strong> nodes</span>
          <span><strong style={{ color: 'var(--accent-secondary)' }}>{graphData.edges.length}</strong> edges</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        {/* Graph */}
        <div style={{ flex: 1 }}>
          <div className="graph-container" style={{ position: 'relative' }}>
            {loading && (
              <div className="loading" style={{ position: 'absolute', inset: 0, background: 'var(--bg-secondary)', zIndex: 5 }}>
                <span className="spinner"></span>
                Building knowledge graph...
              </div>
            )}
            <div ref={graphRef} style={{ width: '100%', height: '100%' }}></div>
            <div className="graph-legend">
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
                Publication Year
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#2563eb' }}></div>
                <span>Older papers</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#22d3ee' }}></div>
                <span>Recent papers</span>
              </div>
              <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Lines = semantic similarity<br />
                Size = citation count
              </div>
            </div>
          </div>
        </div>

        {/* Selected Node Details */}
        {selectedNode && (
          <div className="card fade-in" style={{ width: '320px', alignSelf: 'flex-start' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
              <span className="badge">{selectedNode.year || 'N/A'}</span>
              <button className="btn-icon" onClick={() => setSelectedNode(null)} style={{ fontSize: '0.8rem' }}>✕</button>
            </div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem', lineHeight: 1.45 }}>
              {selectedNode.title}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Authors</span>
                <div style={{ marginTop: '0.2rem' }}>{selectedNode.authors}</div>
              </div>
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Citations</span>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--accent-secondary)' }}>{selectedNode.citationCount.toLocaleString()}</div>
                </div>
                {selectedNode.year && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Year</span>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>{selectedNode.year}</div>
                  </div>
                )}
              </div>
              {selectedNode.venue && (
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Venue</span>
                  <div style={{ marginTop: '0.2rem' }}>{selectedNode.venue}</div>
                </div>
              )}
              {selectedNode.url && (
                <a href={selectedNode.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{ marginTop: '0.5rem', justifyContent: 'center' }}>
                  Open Paper ↗
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {graphData.nodes.length === 0 && !loading && (
        <div className="empty-state">
          <h3>No graph data available</h3>
          <p>Ingest papers from the Discover page first to build the knowledge graph.</p>
        </div>
      )}
    </div>
  );
}
