/**
 * Usage Examples for SearchAutocomplete
 * 
 * Shows different ways to integrate the autocomplete component
 */

import { useState } from 'react';
import SearchAutocomplete from '../components/SearchAutocomplete';

const SearchExamples = () => {
  const [example1Result, setExample1Result] = useState(null);
  const [example2Result, setExample2Result] = useState(null);
  const [example3Result, setExample3Result] = useState(null);

  return (
    <div className="examples-page">
      <div className="examples-container">
        <h1>SearchAutocomplete - Usage Examples</h1>

        {/* Example 1: Basic Usage */}
        <section className="example-section">
          <h2>1. Basic Usage (No Location)</h2>
          <p className="example-description">
            Simple autocomplete without geo-distance sorting. Results sorted by relevance only.
          </p>
          
          <div className="example-code">
            <pre>{`<SearchAutocomplete
  placeholder="Search places..."
  onSelect={(poi) => {}}
/>`}</pre>
          </div>

          <div className="example-demo">
            <SearchAutocomplete
              placeholder="Search places..."
              onSelect={setExample1Result}
            />
          </div>

          {example1Result && (
            <div className="example-result">
              <strong>Selected:</strong> {example1Result.name}
            </div>
          )}
        </section>

        {/* Example 2: With Geolocation */}
        <section className="example-section">
          <h2>2. With Geo-Distance Sorting</h2>
          <p className="example-description">
            Autocomplete with user location. Results sorted by distance from user.
          </p>
          
          <div className="example-code">
            <pre>{`const [location, setLocation] = useState(null);

useEffect(() => {
  navigator.geolocation.getCurrentPosition((pos) => {
    setLocation({
      lat: pos.coords.latitude,
      lng: pos.coords.longitude
    });
  });
}, []);

<SearchAutocomplete
  placeholder="Search nearby..."
  location={location}
  onSelect={handleSelect}
/>`}</pre>
          </div>

          <div className="example-demo">
            <SearchAutocomplete
              placeholder="Search nearby places..."
              location={{ lat: 16.0544, lng: 108.2428 }} // Da Nang
              onSelect={setExample2Result}
            />
          </div>

          {example2Result && (
            <div className="example-result">
              <strong>Selected:</strong> {example2Result.name}
              {example2Result._distance_km && (
                <span> ({example2Result._distance_km.toFixed(2)} km away)</span>
              )}
            </div>
          )}
        </section>

        {/* Example 3: Custom Configuration */}
        <section className="example-section">
          <h2>3. Custom Configuration</h2>
          <p className="example-description">
            Autocomplete with custom min length, max results, and auto-focus.
          </p>
          
          <div className="example-code">
            <pre>{`<SearchAutocomplete
  placeholder="Type at least 3 characters..."
  minLength={3}
  maxResults={5}
  autoFocus={true}
  onSelect={handleSelect}
  className="custom-search"
/>`}</pre>
          </div>

          <div className="example-demo">
            <SearchAutocomplete
              placeholder="Type at least 3 characters..."
              minLength={3}
              maxResults={5}
              autoFocus={false}
              onSelect={setExample3Result}
              className="custom-search"
            />
          </div>

          {example3Result && (
            <div className="example-result">
              <strong>Selected:</strong> {example3Result.name}
            </div>
          )}
        </section>

        {/* Example 4: Programmatic Usage */}
        <section className="example-section">
          <h2>4. Direct API Usage (Without Component)</h2>
          <p className="example-description">
            Use searchAPI directly for custom implementations.
          </p>
          
          <div className="example-code">
            <pre>{`import searchAPI from '../services/searchApi';

// Debounced autocomplete
const results = await searchAPI.debouncedAutocomplete(
  'restaurant',
  { location: { lat: 16.0544, lng: 108.2428 }, limit: 10 }
);

// Full search
const searchResults = await searchAPI.search({
  q: 'beach',
  lat: 16.0544,
  lng: 108.2428,
  radius: 5,
  min_rating: 4.0
});

// Nearby search
const nearby = await searchAPI.searchNearby(
  16.0544, 108.2428, 5
);

// By type
const restaurants = await searchAPI.searchByType(
  'restaurant',
  16.0544,
  108.2428
);

// Popular POIs
const popular = await searchAPI.getPopular(
  16.0544, 108.2428, 10
);`}</pre>
          </div>
        </section>

        {/* Cost Optimization Tips */}
        <section className="example-section tips-section">
          <h2>💡 Cost Optimization Features</h2>
          
          <div className="tips-grid">
            <div className="tip-card">
              <div className="tip-icon">⏱️</div>
              <h3>Debouncing (300ms)</h3>
              <p>
                Waits 300ms after user stops typing before calling API.
                Reduces calls by 80-90%.
              </p>
            </div>

            <div className="tip-card">
              <div className="tip-icon">💾</div>
              <h3>Client Caching</h3>
              <p>
                Caches results for 1 hour. Repeated searches = 0 API calls.
                Perfect for popular queries.
              </p>
            </div>

            <div className="tip-card">
              <div className="tip-icon">📝</div>
              <h3>Recent Searches</h3>
              <p>
                Stores searches in localStorage. Works offline and provides
                instant fallback.
              </p>
            </div>

            <div className="tip-card">
              <div className="tip-icon">🔢</div>
              <h3>Min Length (2 chars)</h3>
              <p>
                Prevents wasteful single-character searches. Only searches
                when meaningful.
              </p>
            </div>

            <div className="tip-card">
              <div className="tip-icon">📍</div>
              <h3>Geo-Distance Sort</h3>
              <p>
                Sorts by proximity when location available. Better user
                experience + relevance.
              </p>
            </div>

            <div className="tip-card">
              <div className="tip-icon">⌨️</div>
              <h3>Keyboard Nav</h3>
              <p>
                Arrow keys, Enter, Escape support. Professional UX without
                extra API calls.
              </p>
            </div>
          </div>
        </section>

        {/* Performance Metrics */}
        <section className="example-section metrics-section">
          <h2>📊 Expected Performance</h2>
          
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Without Optimization</th>
                <th>With Optimization</th>
                <th>Improvement</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>API Calls (10 keystrokes)</td>
                <td>10</td>
                <td>1-2</td>
                <td className="positive">80-90% ↓</td>
              </tr>
              <tr>
                <td>Cache Hit Rate</td>
                <td>0%</td>
                <td>30-50%</td>
                <td className="positive">+30-50%</td>
              </tr>
              <tr>
                <td>Response Time (cached)</td>
                <td>50-100ms</td>
                <td>&lt;5ms</td>
                <td className="positive">95% faster</td>
              </tr>
              <tr>
                <td>Cost (10K searches/mo)</td>
                <td>$283</td>
                <td>$28-32</td>
                <td className="positive">90% ↓</td>
              </tr>
              <tr>
                <td>Offline Support</td>
                <td>❌ No</td>
                <td>✅ Recent searches</td>
                <td className="positive">+Resilience</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      {/* Styles */}
      <style jsx>{`
        .examples-page {
          min-height: 100vh;
          background: #f8fafc;
          padding: 40px 20px;
        }

        .examples-container {
          max-width: 1000px;
          margin: 0 auto;
        }

        .examples-container > h1 {
          text-align: center;
          color: #1e293b;
          margin-bottom: 40px;
          font-size: 32px;
        }

        .example-section {
          background: white;
          padding: 32px;
          border-radius: 16px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
          margin-bottom: 32px;
        }

        .example-section h2 {
          margin-top: 0;
          margin-bottom: 12px;
          color: #1e293b;
          font-size: 24px;
        }

        .example-description {
          color: #64748b;
          margin-bottom: 20px;
          line-height: 1.6;
        }

        .example-code {
          background: #1e293b;
          padding: 20px;
          border-radius: 8px;
          margin-bottom: 20px;
          overflow-x: auto;
        }

        .example-code pre {
          margin: 0;
          color: #e2e8f0;
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.6;
        }

        .example-demo {
          margin-bottom: 16px;
        }

        .example-result {
          background: #f0fdf4;
          border: 2px solid #10b981;
          padding: 16px;
          border-radius: 8px;
          color: #065f46;
          font-size: 14px;
        }

        .tips-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 20px;
        }

        .tip-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 24px;
          border-radius: 12px;
          text-align: center;
        }

        .tip-icon {
          font-size: 48px;
          margin-bottom: 12px;
        }

        .tip-card h3 {
          margin: 0 0 12px 0;
          font-size: 18px;
        }

        .tip-card p {
          margin: 0;
          opacity: 0.9;
          font-size: 14px;
          line-height: 1.6;
        }

        .metrics-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
        }

        .metrics-table th,
        .metrics-table td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid #e2e8f0;
        }

        .metrics-table th {
          background: #f8fafc;
          font-weight: 600;
          color: #1e293b;
        }

        .metrics-table td {
          color: #64748b;
        }

        .metrics-table .positive {
          color: #10b981;
          font-weight: 600;
        }

        /* Mobile Responsive */
        @media (max-width: 640px) {
          .examples-container > h1 {
            font-size: 24px;
          }

          .example-section {
            padding: 20px;
          }

          .example-code {
            padding: 16px;
          }

          .example-code pre {
            font-size: 12px;
          }

          .tips-grid {
            grid-template-columns: 1fr;
          }

          .metrics-table {
            font-size: 12px;
          }

          .metrics-table th,
          .metrics-table td {
            padding: 8px;
          }
        }
      `}</style>
    </div>
  );
};

export default SearchExamples;
