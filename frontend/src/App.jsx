import { useState } from 'react'
import './App.css'

function App() {
  // --- STATE (Think of these as variables that update the screen automatically) ---
  const [activeTab, setActiveTab] = useState('skills'); // 'skills' or 'location'
  const [inputValue, setInputValue] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- THE FUNCTION TO CALL YOUR PYTHON API ---
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // decide which URL to hit based on the tab
      // NOTE: React runs on port 5173, FastAPI on 8000
      let url = '';
      if (activeTab === 'skills') {
        url = `http://127.0.0.1:8000/skill/${inputValue}`;
      } else {
        url = `http://127.0.0.1:8000/location/${inputValue}`;
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

  return (
    <div className="container">
      <h1>🚀 Job Market AI</h1>
      
      {/* NAVIGATION TABS */}
      <div className="tabs">
        <button 
          className={activeTab === 'skills' ? 'active' : ''} 
          onClick={() => {setActiveTab('skills'); setResults(null); setInputValue('')}}
        >
          Skill Explorer
        </button>
        <button 
          className={activeTab === 'location' ? 'active' : ''} 
          onClick={() => {setActiveTab('location'); setResults(null); setInputValue('Remote')}}
        >
          Location Trends
        </button>
      </div>

      {/* INPUT SECTION */}
      <div className="search-box">
        <input 
          type="text" 
          placeholder={activeTab === 'skills' ? "Enter a skill (e.g. Python)..." : "Enter a city (e.g. New York)..."}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchData()}
        />
        <button onClick={fetchData} disabled={loading}>
          {loading ? "Scanning..." : "Search"}
        </button>
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
