/**
 * Search API Service - Elasticsearch Autocomplete
 * 
 * Cost Optimization Strategy:
 * 1. Debouncing: 300ms delay to reduce API calls by 80-90%
 * 2. Client-side caching: Cache results for 1 hour
 * 3. Minimum query length: 2 characters
 * 4. Local storage backup: Reuse recent searches
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

  /**
   * Autocomplete search with debouncing and caching
   * 
   * @param {string} query - Search query (min 2 chars)
   * @param {object} options - Optional parameters
   * @param {number} options.limit - Max results (default: 10)
   * @param {object} options.location - User location {lat, lng}
   * @param {number} options.radius - Search radius in km (default: 20)
   * @returns {Promise<Array>} - POI suggestions
   */
  async autocomplete(query, options = {}) {
    // Validation
    if (!query || query.trim().length < 2) {
      return [];
    }

    const cleanQuery = query.trim();
    
    // Check cache first (client-side optimization)
    const cached = this.getCached(cleanQuery);
    if (cached) {
      console.log('[CACHE HIT] Autocomplete:', cleanQuery);
      return cached;
    }

    // Build query parameters
    const params = {
      q: cleanQuery,
      limit: options.limit || 10,
    };

    // Add location if provided (for geo-distance sorting)
    if (options.location) {
      params.lat = options.location.lat;
      params.lng = options.location.lng;
      params.radius = options.radius || 20;
    }

    try {
      // API call to backend Elasticsearch
      const response = await api.get('/search/autocomplete', { params });
      
      const data = response.data;
      const results = data.suggestions || [];
      
      // Cache results
      this.setCached(cleanQuery, results);
      
      // Save to recent searches
      this.addRecentSearch(cleanQuery, results.length > 0);
      
      console.log('[API CALL] Autocomplete:', cleanQuery, `(${data.count || 0} results)`);
      
      return results;
      
    } catch (error) {
      console.error('[ERROR] Autocomplete failed:', error);
      
      // Fallback to recent searches
      return this.getRecentSearches()
        .filter(s => s.query.toLowerCase().includes(cleanQuery.toLowerCase()))
        .slice(0, 5)
        .map(s => ({ name: s.query, type: 'recent', _fallback: true }));
    }
  }

  /**
   * Debounced autocomplete - reduces API calls by 80-90%
   * 
   * Usage:
   *   const results = await searchAPI.debouncedAutocomplete('cafe', {...});
   */
  debouncedAutocomplete(query, options = {}) {
    return new Promise((resolve) => {
      // If there is no debounce delay (NONE or 0), call the autocomplete directly
      if (!this.debounceDelay || this.debounceDelay <= 0) {
        this.autocomplete(query, options).then(resolve).catch((err) => {
          console.error('[ERROR] Debounced autocomplete direct call failed:', err);
          resolve([]);
        });
        return;
      }

      // Clear previous timer
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
      }

      // Set new timer
      this.debounceTimer = setTimeout(async () => {
        const results = await this.autocomplete(query, options);
        resolve(results);
      }, this.debounceDelay);
    });
  }

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
}

// Singleton instance
const searchAPI = new SearchAPI();

export default searchAPI;
