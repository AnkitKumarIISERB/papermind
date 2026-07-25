import { useState } from 'react';
import { askQuestion } from '../api';

export default function ReviewPage() {
  const [topic, setTopic] = useState('');
  const [style, setStyle] = useState('comprehensive');
  const [review, setReview] = useState('');
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);

  const generateReview = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setReview('');
    setSources([]);

    const prompt = getReviewPrompt(topic, style);

    try {
      const res = await askQuestion(prompt);
      setReview(res.data.answer || res.data.response || '');
      setSources(res.data.sources || res.data.context_papers || []);
    } catch (err) {
      console.error('Review error:', err);
      setReview('Failed to generate review. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getReviewPrompt = (topic, style) => {
    const styleMap = {
      comprehensive: `Write a comprehensive academic literature review about "${topic}". Structure it with clear sections: Introduction, Key Themes and Approaches, Analysis of Methods, Current Trends, Research Gaps, and Conclusion. Cite specific papers from the database by their titles and years.`,
      brief: `Write a brief 3-paragraph overview of the research landscape for "${topic}". Mention key papers and trends. Be concise but insightful.`,
      gaps: `Analyze the current research on "${topic}" and identify 5-7 specific research gaps or unexplored areas. For each gap, explain why it matters and what potential approaches could address it. Reference existing papers.`,
      trends: `Analyze emerging trends in "${topic}" research. What methodologies are gaining popularity? What are the shifting paradigms? Organize chronologically and cite specific papers.`,
    };
    return styleMap[style] || styleMap.comprehensive;
  };

  const formatReview = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Literature Review Generator</h2>
        <p>Generate AI-powered literature reviews grounded in your indexed papers. No hallucination — every insight is backed by real research.</p>
      </div>

      {/* ── Controls ───────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>
            Research Topic
          </label>
          <input
            type="text"
            className="input input-large"
            placeholder="e.g., 'attention mechanisms in multimodal learning'"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && generateReview()}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>
              Review Style
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {[
                { key: 'comprehensive', label: '📝 Comprehensive', desc: 'Full academic review' },
                { key: 'brief', label: '⚡ Brief Overview', desc: 'Quick summary' },
                { key: 'gaps', label: '🔍 Research Gaps', desc: 'Find unexplored areas' },
                { key: 'trends', label: '📈 Trend Analysis', desc: 'Track methodological shifts' },
              ].map(s => (
                <button
                  key={s.key}
                  className={`btn ${style === s.key ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setStyle(s.key)}
                  title={s.desc}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={generateReview}
            disabled={loading || !topic.trim()}
            style={{ minWidth: '160px', justifyContent: 'center' }}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></span>
                Generating...
              </>
            ) : (
              <>✨ Generate Review</>
            )}
          </button>
        </div>
      </div>

      {/* ── Feature Cards (when no review) ─────────────────── */}
      {!review && !loading && (
        <div className="feature-grid" style={{ marginTop: '2rem' }}>
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>RAG-Powered</h3>
            <p>Reviews are generated using Retrieval-Augmented Generation — every claim is backed by actual papers in your database.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>No Hallucination</h3>
            <p>Unlike general LLMs, PaperMind only cites papers it has actually indexed and verified from Semantic Scholar.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Multiple Styles</h3>
            <p>Choose from comprehensive reviews, quick summaries, gap analysis, or trend reports — each optimized for different needs.</p>
          </div>
        </div>
      )}

      {/* ── Loading State ──────────────────────────────────── */}
      {loading && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem', width: 32, height: 32 }}></div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Searching relevant papers and generating your literature review...
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.5rem' }}>
            This may take 15-30 seconds
          </p>
        </div>
      )}

      {/* ── Generated Review ───────────────────────────────── */}
      {review && !loading && (
        <div className="fade-in-up">
          <div className="review-output" dangerouslySetInnerHTML={{ __html: `<p>${formatReview(review)}</p>` }} />

          {/* Sources */}
          {sources.length > 0 && (
            <div className="card" style={{ marginTop: '1rem' }}>
              <div className="section-title">📚 Source Papers ({sources.length})</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {sources.map((s, i) => (
                  <div key={i} className="author-row">
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                      {typeof s === 'string' ? s : s.title || s.paper_title || `Paper ${i + 1}`}
                    </span>
                    {typeof s === 'object' && s.year && (
                      <span className="badge">{s.year}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
