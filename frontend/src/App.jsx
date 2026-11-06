import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import DiscoverPage from './pages/DiscoverPage';
import SearchPage from './pages/SearchPage';
import GraphPage from './pages/GraphPage';
import QAPage from './pages/QAPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ReviewPage from './pages/ReviewPage';
import './index.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <NavLink to="/" className="navbar-brand">
            <svg viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="13" stroke="url(#navGrad)" strokeWidth="2" />
              <circle cx="14" cy="14" r="5" fill="url(#navGrad)" />
              <path d="M14 1a13 13 0 0 1 4 13 13 13 0 0 1-4 13" stroke="url(#navGrad)" strokeWidth="1.5" opacity="0.6" />
              <path d="M14 1a13 13 0 0 0-4 13 13 13 0 0 0 4 13" stroke="url(#navGrad)" strokeWidth="1.5" opacity="0.6" />
              <line x1="1" y1="14" x2="27" y2="14" stroke="url(#navGrad)" strokeWidth="1.5" opacity="0.4" />
              <defs>
                <linearGradient id="navGrad" x1="0" y1="0" x2="28" y2="28">
                  <stop stopColor="#2563eb" />
                  <stop offset="1" stopColor="#60a5fa" />
                </linearGradient>
              </defs>
            </svg>
            <h1>PaperMind</h1>
          </NavLink>
          <div className="navbar-links">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
              Discover
            </NavLink>
            <NavLink to="/search" className={({ isActive }) => isActive ? 'active' : ''}>
              Search
            </NavLink>
            <NavLink to="/graph" className={({ isActive }) => isActive ? 'active' : ''}>
              Graph
            </NavLink>
            <NavLink to="/analytics" className={({ isActive }) => isActive ? 'active' : ''}>
              Analytics
            </NavLink>
            <NavLink to="/qa" className={({ isActive }) => isActive ? 'active' : ''}>
              Ask AI
            </NavLink>
            <NavLink to="/review" className={({ isActive }) => isActive ? 'active' : ''}>
              Review
            </NavLink>
          </div>
        </nav>

        <main className="page">
          <Routes>
            <Route path="/" element={<DiscoverPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/qa" element={<QAPage />} />
            <Route path="/review" element={<ReviewPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
