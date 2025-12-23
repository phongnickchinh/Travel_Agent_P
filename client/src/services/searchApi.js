/**
 * Search API Service - Hybrid Autocomplete (ES + MongoDB + Google)
 * 
 * Cost Optimization Strategy:
 * 1. Debouncing: 300ms delay to reduce API calls by 80-90%
 * 2. Client-side caching: Cache results for 1 hour
 * 3. Minimum query length: 2 characters
 * 4. Local storage backup: Reuse recent searches
 * 5. Session tokens: Google Places billing optimization
 * 
 * Migration Note (2025-01):
 * - OLD: Multi-index autocomplete (/search/autocomplete) - REMOVED
 * - NEW: Hybrid V2 autocomplete (/v2/autocomplete) with ES + MongoDB + Google
 * 
 * Expected Savings:
 * - Without optimization: 10 keystrokes = 10 API calls
 * - With optimization: 10 keystrokes = 1-2 API calls (80-90% reduction)
 */

import api from './apiClient';

class SearchAPI {
  constructor() {
    // In-memory cache for autocomplete results
    this.cache = new Map();
    this.cacheExpiry = 3600000; // 1 hour in milliseconds
    
    // Debounce timer
    this.debounceTimer = null;
    // Read AUTOCOMPLETE cost from Vite env; default to NORMAL mapping
    const costEnv = (import.meta.env.VITE_AUTOCOMPLETE_COST || 'NORMAL').toUpperCase();
    const explicitDebounce = import.meta.env.VITE_AUTOCOMPLETE_DEBOUNCE_MS;

    // Map costs to debounce delays
    const costMap = {
      CHEAP: 50,
      NORMAL: 300,
      EXPENSIVE: 500,
      NONE: 0
    };

    this.debounceDelay = explicitDebounce ? Number(explicitDebounce) : (costMap[costEnv] ?? 300);
    
    // Recent searches (localStorage backup)
    this.recentSearchesKey = 'recent_autocomplete_searches';
    this.maxRecentSearches = 20;
  }

  /**
   * Get cached autocomplete result if available and not expired
   */
  getCached(query) {
    const cached = this.cache.get(query.toLowerCase());
    
    if (!cached) return null;
    
    const now = Date.now();
    if (now - cached.timestamp > this.cacheExpiry) {
      this.cache.delete(query.toLowerCase());
      return null;
    }
    
    return cached.data;
  }

  /**
   * Save autocomplete result to cache
   */
  setCached(query, data) {
    this.cache.set(query.toLowerCase(), {
      data,
      timestamp: Date.now()
    });
  }

  // ============================================
  // NOTE: Old autocomplete() method REMOVED
  // Use autocompleteV2() instead (hybrid ES + MongoDB + Google)
  // Migration date: 2025-01
  // ============================================

  /**
   * Full search with filters (ES lexical + geo)
   */
  async search(params = {}) {
    try {
      const response = await api.get('/api/search', { params });
      return response.data;
    } catch (error) {
      console.error('[ERROR] Search failed:', error);
      throw error;
    }
  }

  /**
   * Search nearby POIs (geo-distance only)
   */
  async searchNearby(lat, lng, radius = 5, options = {}) {
    try {
      const params = {
        lat,
        lng,
        radius,
        ...options
      };
      
      const response = await api.get('/api/search/nearby', { params });
      return response.data;
    } catch (error) {
      console.error('[ERROR] Nearby search failed:', error);
      throw error;
    }
  }

  /**
   * Search by POI type/category
   */
  async searchByType(type, lat, lng, options = {}) {
    try {
      const params = {
        lat,
        lng,
        radius: options.radius || 10,
        ...options
      };
      
      const response = await api.get(`/api/search/type/${type}`, { params });
      return response.data;
    } catch (error) {
      console.error('[ERROR] Type search failed:', error);
      throw error;
    }
  }

  /**
   * Get popular POIs
   */
  async getPopular(lat, lng, limit = 10) {
    try {
      const params = { lat, lng, limit };
      const response = await api.get('/search/popular', { params });
      return response.data;
    } catch (error) {
      console.error('[ERROR] Popular search failed:', error);
      throw error;
    }
  }

  /**
   * Recent searches management (localStorage)
   */
  getRecentSearches() {
    try {
      const stored = localStorage.getItem(this.recentSearchesKey);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('[ERROR] Failed to load recent searches:', error);
      return [];
    }
  }

  addRecentSearch(query, hasResults) {
    try {
      const searches = this.getRecentSearches();
      
      // Remove duplicate
      const filtered = searches.filter(s => s.query !== query);
      
      // Add to front
      filtered.unshift({
        query,
        hasResults,
        timestamp: Date.now()
      });
      
      // Limit size
      const limited = filtered.slice(0, this.maxRecentSearches);
      
      localStorage.setItem(this.recentSearchesKey, JSON.stringify(limited));
    } catch (error) {
      console.error('[ERROR] Failed to save recent search:', error);
    }
  }

  clearRecentSearches() {
    localStorage.removeItem(this.recentSearchesKey);
    console.log('[INFO] Recent searches cleared');
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.cache.clear();
    this.clearRecentSearches();
    console.log('[INFO] All caches cleared');
  }

  /**
   * Get cache statistics (for monitoring)
   */
  getCacheStats() {
    return {
      cacheSize: this.cache.size,
      recentSearchesCount: this.getRecentSearches().length,
      cacheExpiry: `${this.cacheExpiry / 1000}s`,
      debounceDelay: `${this.debounceDelay}ms`
    };
  }

  /**
   * Return current debounce delay (ms) for diagnostic/other components
   */
  getDebounceDelay() {
    return this.debounceDelay;
  }

  // ============================================
  // V2 HYBRID AUTOCOMPLETE API (ES + MongoDB + Google)
  // ============================================

  /**
   * Session token for Google Places API billing optimization.
   * Reuse same token for autocomplete requests, reset after place selection.
   */
  _sessionToken = null;

  /**
   * Get or create session token for autocomplete session.
   * @returns {string} UUID session token
   */
  getSessionToken() {
    if (!this._sessionToken) {
      this._sessionToken = crypto.randomUUID();
    }
    return this._sessionToken;
  }

  /**
   * Reset session token after place selection (for billing optimization).
   */
  resetSessionToken() {
    this._sessionToken = null;
  }

  /**
   * V2 Hybrid Autocomplete - Uses ES + MongoDB + Google fallback
   * 
   * @param {string} query - Search query (min 2 chars)
   * @param {object} options - Optional parameters
   * @param {number} options.limit - Max results (default: 5)
   * @param {number} options.lat - Latitude for location bias
   * @param {number} options.lng - Longitude for location bias
   * @param {string[]} options.types - Filter by place types
   * @param {boolean} options.useSessionToken - Auto-manage session token (default: true)
   * @returns {Promise<object>} - {suggestions, total, sources, query_time_ms}
   */
  async autocompleteV2(query, options = {}) {
    // Validation
    if (!query || query.trim().length < 2) {
      return { suggestions: [], total: 0, sources: {} };
    }

    const cleanQuery = query.trim();
    
    // Check cache first (same cache as v1)
    const cacheKey = `v2:${cleanQuery}`;
    const cached = this.getCached(cacheKey);
    if (cached) {
      console.log('[CACHE HIT] AutocompleteV2:', cleanQuery);
      return cached;
    }

    // Build query parameters
    const params = new URLSearchParams({
      q: cleanQuery,
      limit: options.limit || 5,
    });

    // Add location for geo-biasing
    if (options.lat && options.lng) {
      params.append('lat', options.lat);
      params.append('lng', options.lng);
    }

    // Add types filter
    if (options.types && Array.isArray(options.types)) {
      params.append('types', options.types.join(','));
    }

    // Add session token (for Google Places billing optimization)
    if (options.useSessionToken !== false) {
      params.append('session_token', this.getSessionToken());
    }

    try {
      // API call to v2 hybrid endpoint
      const response = await api.get(`/v2/autocomplete?${params}`);
      const data = response.data;
      
      // Cache results
      this.setCached(cacheKey, data);
      
      // Save to recent searches
      this.addRecentSearch(cleanQuery, data.total > 0);
      
      console.log(
        '[API CALL] AutocompleteV2:', cleanQuery,
        `(${data.total || 0} results)`,
        'Sources:', data.sources || {}
      );
      
      return data;
      
    } catch (error) {
      console.error('[ERROR] AutocompleteV2 failed:', error);
      
      // Fallback to recent searches if API fails
      console.log('[FALLBACK] Using recent searches...');
      const recentResults = this.getRecentSearches()
        .filter(s => s.query.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 5)
        .map(s => ({ name: s.query, type: 'recent', source_type: 'recent', _fallback: true }));
      return {
        suggestions: recentResults,
        total: recentResults.length,
        sources: { fallback_recent: recentResults.length },
        query_time_ms: 0
      };
    }
  }

  /**
   * Debounced V2 Autocomplete - reduces API calls
   * 
   * Note: This is the primary autocomplete method.
   * For backward compatibility, debouncedAutocomplete() is an alias to this.
   */
  debouncedAutocompleteV2(query, options = {}) {
    return new Promise((resolve) => {
      // If no debounce delay, call directly
      if (!this.debounceDelay || this.debounceDelay <= 0) {
        this.autocompleteV2(query, options).then(resolve).catch((err) => {
          console.error('[ERROR] DebouncedAutocompleteV2 failed:', err);
          resolve({ suggestions: [], total: 0, sources: {} });
        });
        return;
      }

      // Clear previous timer
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
      }

      // Set new timer
      this.debounceTimer = setTimeout(async () => {
        const results = await this.autocompleteV2(query, options);
        resolve(results);
      }, this.debounceDelay);
    });
  }

  /**
   * Backward compatibility alias - points to V2
   */
  debouncedAutocomplete(query, options = {}) {
    return this.debouncedAutocompleteV2(query, options);
  }

  /**
   * Backward compatibility alias - points to V2
   */
  autocomplete(query, options = {}) {
    return this.autocompleteV2(query, options);
  }

  /**
   * Resolve pending place - Get full details for a pending autocomplete suggestion
   * 
   * @param {string} placeId - Google Place ID
   * @param {string} sessionToken - Session token (optional, uses internal if not provided)
   * @returns {Promise<object>} - {place: {...}, status: "resolved"}
   */
  async resolvePlace(placeId, sessionToken = null) {
    try {
      const token = sessionToken || this.getSessionToken();
      
      const response = await api.post(`/v2/autocomplete/resolve/${placeId}`, {
        session_token: token
      });
      
      // Reset session token after successful resolution
      this.resetSessionToken();
      
      console.log('[API CALL] ResolvePlace:', placeId, '✓');
      return response.data;
      
    } catch (error) {
      console.error('[ERROR] ResolvePlace failed:', error);
      throw error;
    }
  }

  /**
   * Get autocomplete cache statistics (for monitoring)
   */
  async getAutocompleteStats() {
    try {
      const response = await api.get('/v2/autocomplete/stats');
      return response.data;
    } catch (error) {
      console.error('[ERROR] GetAutocompleteStats failed:', error);
      return null;
    }
  }
}

// Singleton instance
const searchAPI = new SearchAPI();

export default searchAPI;
