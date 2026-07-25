import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { askQuestion, askQuestionStream } from '../api';

export default function QAPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      if (streamMode) {
        // Streaming mode
        let fullResponse = '';
        setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true, sources: [] }]);

        const stream = askQuestionStream(question);
        for await (const chunk of stream) {
          fullResponse += chunk;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: 'assistant',
              content: fullResponse,
              streaming: true,
              sources: [],
            };
            return updated;
          });
        }

        // Mark as done
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1].streaming = false;
          return updated;
        });
      } else {
        // Non-streaming mode
        const res = await askQuestion(question);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: res.data.answer,
          sources: res.data.sources || [],
        }]);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to get response. Make sure papers are indexed first.';
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ ${errorMsg}`,
        sources: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "What are the main approaches to multimodal fusion?",
    "Which papers use transformer-based models?",
    "Compare attention-based vs concatenation-based methods",
    "What datasets are commonly used in this field?",
    "What are the key research gaps identified?",
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Ask AI</h2>
        <p>Ask questions about the indexed papers. Answers are grounded in retrieved abstracts — no hallucination.</p>
      </div>

      <div className="card chat-container">
        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🧠</div>
              <h3 style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Ask anything about your papers</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                Every answer is grounded in the papers you&apos;ve indexed. The AI will cite specific papers.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center' }}>
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    className="btn btn-secondary btn-sm"
                    onClick={() => setInput(q)}
                    style={{ fontSize: '0.8rem' }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              {msg.role === 'assistant' ? (
                <>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.streaming && (
                    <span style={{ display: 'inline-block', width: 8, height: 16, background: 'var(--accent-primary)', animation: 'pulse 1s infinite', borderRadius: 2, marginLeft: 2 }}></span>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="chat-sources">
                      <h4>Sources Used</h4>
                      {msg.sources.map((s, i) => (
                        <div key={i} className="chat-source-item">
                          📄 {s.title} ({s.year}) — {s.authors}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          ))}

          {loading && !streamMode && (
            <div className="chat-message assistant">
              <div className="loading" style={{ padding: '0.5rem 0' }}>
                <span className="spinner" style={{ width: 16, height: 16 }}></span>
                Searching papers and generating answer...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <input
            type="text"
            className="input"
            placeholder="Ask a question about the indexed papers..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSubmit(e)}
            disabled={loading}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            <input
              type="checkbox"
              checked={streamMode}
              onChange={(e) => setStreamMode(e.target.checked)}
            />
            Stream
          </label>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
