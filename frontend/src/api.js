import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ── Papers ──────────────────────────────────────────────────

export const ingestTopic = (topic, maxPapers = 200) =>
  api.post('/papers/ingest', { topic, max_papers: maxPapers });

export const getIngestionStatus = (searchId) =>
  api.get(`/papers/ingest/${searchId}/status`);

export const listPapers = (limit = 50, offset = 0, sortBy = 'citation_count', order = 'desc') =>
  api.get('/papers/', { params: { limit, offset, sort_by: sortBy, order } });

export const getPaper = (paperId) =>
  api.get(`/papers/${paperId}`);

export const getCitationGraph = (minCitations = 0, limit = 200, similarityThreshold = 0.55) =>
  api.get('/papers/graph/citation', { params: { min_citations: minCitations, limit, similarity_threshold: similarityThreshold } });

export const getStats = () =>
  api.get('/papers/stats/overview');

// ── Search ──────────────────────────────────────────────────

export const searchPapers = (query, limit = 10, yearMin = null, yearMax = null) =>
  api.post('/search', { query, limit, year_min: yearMin, year_max: yearMax });

// ── Q&A ─────────────────────────────────────────────────────

export const askQuestion = (question, topK = 8) =>
  api.post('/qa', { question, top_k: topK, stream: false });

export const askQuestionStream = async function* (question, topK = 8) {
  const response = await fetch(`${API_URL}/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK, stream: true }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        yield data;
      }
    }
  }
};

// ── Agent Mode ──────────────────────────────────────────────

export const askAgent = (question) =>
  api.post('/agent/ask', { question });

// ── Literature Review ───────────────────────────────────────

export const generateReview = (paperIds, focusTopic = null) =>
  api.post('/review', { paper_ids: paperIds, focus_topic: focusTopic });

// ── Collections ─────────────────────────────────────────────

export const createCollection = (name, description = null) =>
  api.post('/collections/', { name, description });

export const listCollections = () =>
  api.get('/collections/');

export const getCollection = (collectionId) =>
  api.get(`/collections/${collectionId}`);

export const addPaperToCollection = (collectionId, paperId, notes = null) =>
  api.post(`/collections/${collectionId}/papers`, { paper_id: paperId, user_notes: notes });

export const removePaperFromCollection = (collectionId, paperId) =>
  api.delete(`/collections/${collectionId}/papers/${paperId}`);

export const deleteCollection = (collectionId) =>
  api.delete(`/collections/${collectionId}`);

export default api;
