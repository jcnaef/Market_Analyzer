import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  // --- STATE (Think of these as variables that update the screen automatically) ---
  const [activeTab, setActiveTab] = useState('skills'); // 'skills' or 'location'
  const [inputValue, setInputValue] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- AUTOCOMPLETE STATE ---
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const debounceTimerRef = useRef(null);
  const wrapperRef = useRef(null);

  // --- THE FUNCTION TO CALL YOUR PYTHON API ---
  const fetchData = async (overrideValue) => {
    const query = typeof overrideValue === 'string' ? overrideValue : inputValue;
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // decide which URL to hit based on the tab
      // NOTE: React runs on port 5173, FastAPI on 8000
      let url = '';
      if (activeTab === 'skills') {
        url = `http://127.0.0.1:8000/skill/${query}`;
      } else {
        url = `http://127.0.0.1:8000/location/${query}`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error("Not found in database");
      }

      const data = await response.json();
      setResults(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- AUTOCOMPLETE FUNCTIONS ---
  const fetchSuggestions = async (query) => {
    const endpoint = activeTab === 'skills'
      ? `http://127.0.0.1:8000/skills/autocomplete?q=${encodeURIComponent(query)}&limit=8`
      : `http://127.0.0.1:8000/locations/autocomplete?q=${encodeURIComponent(query)}&limit=8`;
    try {
      const res = await fetch(endpoint);
      if (!res.ok) return;
      const data = await res.json();
      setSuggestions(data.suggestions);
      setShowSuggestions(data.suggestions.length > 0);
    } catch {
      // silently fail - autocomplete is non-critical
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);
    setHighlightedIndex(-1);
    if (!value) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => fetchSuggestions(value), 300);
  };

  const handleSelectSuggestion = (suggestion) => {
    setInputValue(suggestion);
    setSuggestions([]);
    setShowSuggestions(false);
    setHighlightedIndex(-1);
    clearTimeout(debounceTimerRef.current);
    fetchData(suggestion);
  };

  const handleKeyDown = (e) => {
    if (!showSuggestions) {
      if (e.key === 'Enter') fetchData();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0) {
        handleSelectSuggestion(suggestions[highlightedIndex]);
      } else {
        setShowSuggestions(false);
        fetchData();
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    }
  };

  // --- CLICK OUTSIDE TO CLOSE DROPDOWN ---
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="container">
      <h1>🚀 Job Market AI</h1>
      
      {/* NAVIGATION TABS */}
      <div className="tabs">
        <button
          className={activeTab === 'skills' ? 'active' : ''}
          onClick={() => {setActiveTab('skills'); setResults(null); setInputValue(''); setSuggestions([]); setShowSuggestions(false)}}
        >
          Skill Explorer
        </button>
        <button
          className={activeTab === 'location' ? 'active' : ''}
          onClick={() => {setActiveTab('location'); setResults(null); setInputValue('Remote'); setSuggestions([]); setShowSuggestions(false)}}
        >
          Location Trends
        </button>
      </div>

      {/* INPUT SECTION */}
      <div className="autocomplete-wrapper" ref={wrapperRef}>
        <div className="search-box">
          <input
            type="text"
            placeholder={activeTab === 'skills' ? "Enter a skill (e.g. Python)..." : "Enter a city (e.g. New York)..."}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            autoComplete="off"
          />
          <button onClick={fetchData} disabled={loading}>
            {loading ? "Scanning..." : "Search"}
          </button>
        </div>

        {showSuggestions && suggestions.length > 0 && (
          <ul className="suggestions-dropdown">
            {suggestions.map((s, i) => (
              <li
                key={s}
                className={`suggestion-item${i === highlightedIndex ? ' highlighted' : ''}`}
                onMouseDown={(e) => { e.preventDefault(); handleSelectSuggestion(s); }}
                onMouseEnter={() => setHighlightedIndex(i)}
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* RESULTS SECTION */}
      {error && <div className="error-msg">⚠️ {error}</div>}

      {results && (
        <div className="results-area">
          {activeTab === 'skills' ? (
            // RENDER SKILL RESULTS
            <>
              <h2>Related to "{results.target_skill}"</h2>
              <ul>
                {results.related_skills.map((item, index) => (
                  <li key={index}>
                    <span className="skill-name">{item.skill}</span>
                    <span className="skill-score">{(item.score * 100).toFixed(0)}% correlation</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            // RENDER LOCATION RESULTS
            <>
              <h2>Top Skills in {results.location}</h2>
              <p>Based on {results.job_count} jobs analyzed</p>
              <div className="chart-bar-container">
                {results.top_skills.map((item, index) => (
                  <div key={index} className="bar-row">
                    <span className="label">{item.skill}</span>
                    <div className="bar-bg">
                      <div 
                        className="bar-fill" 
                        style={{width: `${Math.min(item.count * 2, 100)}%`}} // Simple scaling
                      ></div>
                    </div>
                    <span className="count">{item.count} jobs</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default App
