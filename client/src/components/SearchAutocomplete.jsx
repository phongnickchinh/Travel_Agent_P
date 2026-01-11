/**
 * SearchAutocomplete Component
 * 
 * Features:
 * - Debounced input (300ms) - reduces API calls by 80-90%
 * - Client-side caching - reuses results for 1 hour
 * - Recent searches fallback
 * - Loading states
 * - Keyboard navigation (↑↓ arrows, Enter, Esc)
 * - Responsive design
 * - Hybrid V2 API: ES + MongoDB + Google Places
 * 
 * Migration Note (2025-01):
 * - OLD: Multi-index v1 API - REMOVED
 * - NEW: Hybrid v2 API exclusively
 * 
 * Cost Impact:
 * - User types "restaurant" (10 keystrokes)
 * - Without optimization: 10 API calls
 * - With this component: 1-2 API calls (80-90% savings)
 */

import {
    Beer,
    Clock,
    Coffee,
    Hotel,
    Landmark,
    Loader2,
    MapPin,
    Palmtree,
    RefreshCw,
    Search,
    ShoppingBag,
    TreePine,
    Utensils,
    X,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import searchAPI from '../services/searchApi';

const SearchAutocomplete = ({ 
  placeholder = "Tìm địa điểm, nhà hàng, khách sạn...",
  onSelect,
  location = null, // {lat, lng} for geo-distance sorting
  className = "",
  autoFocus = false,
  minLength = 2,
  maxResults = 10
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [showRecent, setShowRecent] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);  // Track pending resolution
  
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  const searchAbortController = useRef(null);

  /**
   * Handle input change with debouncing
   */
  // Read autocomplete cost from Vite env to adjust keyboard/input behavior
  const autocompleteCost = (import.meta.env.VITE_AUTOCOMPLETE_COST || 'NORMAL').toUpperCase();
  const effectiveMinLength = (autocompleteCost === 'CHEAP') ? Math.max(1, minLength) : minLength;

  const handleInputChange = useCallback(async (value) => {
    setQuery(value);
    setSelectedIndex(-1);

    // Clear results if query too short
    if (value.trim().length < effectiveMinLength) {
      setResults([]);
      setIsOpen(false);
      setShowRecent(false);
      return;
    }

    // Show loading
    setIsLoading(true);
    setIsOpen(true);

    // Abort previous request
    if (searchAbortController.current) {
      searchAbortController.current.abort();
    }

    try {
      // Use V2 Hybrid API (ES + MongoDB + Google)
      const response = await searchAPI.debouncedAutocompleteV2(value, {
        limit: maxResults,
        lat: location?.lat,
        lng: location?.lng
      });
      
      // Debug: Log response
      // console.log('[DEBUG] AutocompleteV2 response:', response);
      
      const suggestions = response.suggestions || [];

      // Debug: Log suggestions to check structure
      // console.log('[DEBUG] Autocomplete suggestions:', suggestions);
      
      // Ensure suggestions is an array and flatten nested objects
      const validResults = Array.isArray(suggestions) 
        ? suggestions.map(item => {
            // If item.name is an object (nested incorrectly), flatten it
            if (item.name && typeof item.name === 'object' && item.name.name) {
              return {
                ...item.name,  // Spread nested properties (name, poi_id, address, rating, types)
                source_type: item.source_type  // Keep source_type from parent
              };
            }
            // Otherwise return as-is
            return item;
          })
        : [];
      
      setResults(validResults);
      setShowRecent(false);
      setIsLoading(false);

    } catch (error) {
      console.error('[ERROR] Autocomplete failed:', error);
      setResults([]);
      setIsLoading(false);
    }
  }, [location, effectiveMinLength, maxResults]);

  /**
   * Handle result selection
   * Handle pending items that need resolution
   */
  const handleSelect = useCallback(async (result) => {
    // If item is pending, resolve it first
    if (result.status === 'pending' && result.place_id) {
      try {
        setResolvingId(result.place_id);
        // console.log('[RESOLVE] Resolving pending place:', result.place_id);
        
        const resolved = await searchAPI.resolvePlace(result.place_id);
        
        setResolvingId(null);
        setQuery(resolved.place?.main_text || resolved.place?.name || result.main_text || '');
        setIsOpen(false);
        setResults([]);
        setShowRecent(false);
        
        if (onSelect) {
          // Return resolved place with full details
          onSelect({
            ...result,
            ...resolved.place,
            _resolved: true
          });
        }
        return;
      } catch (error) {
        console.error('[ERROR] Failed to resolve place:', error);
        setResolvingId(null);
        // Continue with unresolved data
      }
    }
    
    // Normal selection (cached result)
    setQuery(result.name || result.main_text || result.query || '');
    setIsOpen(false);
    setResults([]);
    setShowRecent(false);
    
    if (onSelect) {
      onSelect(result);
    }
  }, [onSelect]);

  /**
   * Handle keyboard navigation
   */
  const handleKeyDown = useCallback((e) => {
    if (!isOpen) {
      // Show recent searches on ArrowDown when dropdown closed
      if (e.key === 'ArrowDown' && query.length === 0) {
        const recent = searchAPI.getRecentSearches();
        if (recent.length > 0) {
          setResults(recent.slice(0, 5));
          setShowRecent(true);
          setIsOpen(true);
        }
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < results.length - 1 ? prev + 1 : prev
        );
        break;

      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;

      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        }
        break;

      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setResults([]);
        setShowRecent(false);
        inputRef.current?.blur();
        break;

      default:
        break;
    }
  }, [isOpen, results, selectedIndex, handleSelect, query]);

  /**
   * Handle focus - show recent searches
   */
  const handleFocus = useCallback(() => {
    if (query.length === 0) {
      const recent = searchAPI.getRecentSearches();
      if (recent.length > 0) {
        setResults(recent.slice(0, 5));
        setShowRecent(true);
        setIsOpen(true);
      }
    } else if (results.length > 0) {
      setIsOpen(true);
    }
  }, [query, results.length]);

  /**
   * Handle click outside to close dropdown
   */
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target) &&
        inputRef.current &&
        !inputRef.current.contains(event.target)
      ) {
        setIsOpen(false);
        setShowRecent(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  /**
   * Auto-focus if needed
   */
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  /**
   * Scroll selected item into view
   */
  useEffect(() => {
    if (selectedIndex >= 0 && dropdownRef.current) {
      const selectedElement = dropdownRef.current.children[selectedIndex];
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [selectedIndex]);

  /**
   * Get POI type icon component
   */
  const getTypeIcon = (type) => {
    const iconMap = {
      restaurant: Utensils,
      cafe: Coffee,
      hotel: Hotel,
      beach: Palmtree,
      museum: Landmark,
      park: TreePine,
      shopping: ShoppingBag,
      bar: Beer,
      recent: Clock,
      default: MapPin
    };

    if (type === 'recent') return iconMap.recent;
    
    // Check if type contains common keywords
    const typeStr = (type || '').toLowerCase();
    for (const [key, IconComponent] of Object.entries(iconMap)) {
      if (typeStr.includes(key)) return IconComponent;
    }
    
    return iconMap.default;
  };

  /**
   * Format distance
   */
  const formatDistance = (distanceKm) => {
    if (!distanceKm) return null;
    if (distanceKm < 1) return `${Math.round(distanceKm * 1000)}m`;
    return `${distanceKm.toFixed(1)}km`;
  };

  return (
    <div className={`search-autocomplete-container ${className}`}>
      {/* Search Input */}
      <div className="search-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          placeholder={placeholder}
          className="search-input"
          autoComplete="off"
          spellCheck="false"
        />
        
        {/* Search Icon */}
        {!isLoading && (
          <span className="search-icon"><Search className="w-4 h-4" /></span>
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <span className="loading-spinner"><Loader2 className="w-4 h-4 animate-spin" /></span>
        )}

        {/* Clear Button */}
        {query.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setResults([]);
              setIsOpen(false);
              inputRef.current?.focus();
            }}
            className="clear-button"
            aria-label="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Dropdown Results */}
      {isOpen && results.length > 0 && (
        <div ref={dropdownRef} className="search-dropdown">
          {/* Header for recent searches */}
          {showRecent && (
            <div className="dropdown-header">
              <span>Tìm kiếm gần đây</span>
              <button
                type="button"
                onClick={() => {
                  searchAPI.clearRecentSearches();
                  setResults([]);
                  setIsOpen(false);
                  setShowRecent(false);
                }}
                className="clear-recent-button"
              >
                Xóa
              </button>
            </div>
          )}

          {/* Results List */}
          <ul className="results-list">
            {results.map((result, index) => (
              <li
                key={result.id || result.poi_id || result.query || index}
                className={`result-item ${selectedIndex === index ? 'selected' : ''} ${result.source_type || ''}`}
                onClick={() => handleSelect(result)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                {/* Icon */}
                <span className="result-icon">
                  {(() => {
                    const IconComponent = getTypeIcon(
                      showRecent ? 'recent' : (
                        result.type || 
                        result.primary_type || 
                        (Array.isArray(result.types) ? result.types[0] : result.types)
                      )
                    );
                    return <IconComponent className="w-4 h-4" />;
                  })()}
                </span>

                {/* Content */}
                <div className="result-content">
                  <div className="result-name">
                    {result.name || result.main_text || result.query}
                    {result.source_type && (
                      <span className="source-badge">
                        {result.source_type === 'admin' ? 'Khu vực' : 
                         result.source_type === 'region' ? 'Vùng' : 
                         result.source_type === 'es' ? 'ES' :
                         result.source_type === 'google' ? 'Google' : 'POI'}
                      </span>
                    )}
                    {/* Pending status badge */}
                    {result.status === 'pending' && resolvingId !== result.place_id && (
                      <span className="pending-badge" title="Cần tải thêm chi tiết"><Loader2 className="w-3 h-3" /></span>
                    )}
                    {/* Resolving spinner */}
                    {resolvingId === result.place_id && (
                      <span className="resolving-spinner" title="Đang tải..."><RefreshCw className="w-3 h-3 animate-spin" /></span>
                    )}
                  </div>
                  
                  {/* Secondary text */}
                  {result.secondary_text && (
                    <div className="result-address">
                      {result.secondary_text}
                    </div>
                  )}
                  
                  {result.address && !result.secondary_text && (
                    <div className="result-address">
                      {typeof result.address === 'string' ? result.address : result.address?.formatted_address || ''}
                    </div>
                  )}

                  {(result.type || result.primary_type) && !showRecent && (
                    <div className="result-type">
                      {result.type || result.primary_type}
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div className="result-meta">
                  {result.rating && (
                    <span className="result-rating">
                      ⭐ {result.rating.toFixed(1)}
                    </span>
                  )}

                  {result._distance_km && (
                    <span className="result-distance">
                      {formatDistance(result._distance_km)}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* No Results */}
      {isOpen && !isLoading && results.length === 0 && query.length >= minLength && (
        <div className="search-dropdown">
          <div className="no-results">
            Không tìm thấy kết quả cho "{query}"
          </div>
        </div>
      )}

      {/* Inline Styles */}
      <style>{`
        .search-autocomplete-container {
          position: relative;
          width: 100%;
        }

        .search-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .search-input {
          width: 100%;
          padding: 12px 44px 12px 44px;
          font-size: 16px;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          outline: none;
          transition: all 0.2s;
        }

        .search-input:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .search-icon,
        .loading-spinner {
          position: absolute;
          left: 14px;
          font-size: 20px;
          color: #64748b;
          pointer-events: none;
        }

        .loading-spinner {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .clear-button {
          position: absolute;
          right: 12px;
          width: 24px;
          height: 24px;
          padding: 0;
          border: none;
          background: #e2e8f0;
          border-radius: 50%;
          cursor: pointer;
          font-size: 14px;
          color: #64748b;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .clear-button:hover {
          background: #cbd5e1;
          color: #1e293b;
        }

        .search-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          left: 0;
          right: 0;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
          max-height: 400px;
          overflow-y: auto;
          z-index: 1000;
        }

        .dropdown-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          border-bottom: 1px solid #e2e8f0;
          font-size: 13px;
          color: #64748b;
          font-weight: 600;
        }

        .clear-recent-button {
          border: none;
          background: none;
          color: #3b82f6;
          cursor: pointer;
          font-size: 13px;
          padding: 4px 8px;
          border-radius: 4px;
        }

        .clear-recent-button:hover {
          background: #eff6ff;
        }

        .results-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }

        .result-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          cursor: pointer;
          transition: background 0.15s;
          border-bottom: 1px solid #f1f5f9;
        }

        .result-item:last-child {
          border-bottom: none;
        }

        .result-item:hover,
        .result-item.selected {
          background: #f8fafc;
        }

        .result-icon {
          font-size: 24px;
          flex-shrink: 0;
        }

        .result-content {
          flex: 1;
          min-width: 0;
        }

        .result-name {
          font-weight: 600;
          color: #1e293b;
          margin-bottom: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .source-badge {
          display: inline-block;
          font-size: 10px;
          font-weight: 500;
          padding: 2px 6px;
          border-radius: 4px;
          background: #e0f2fe;
          color: #0369a1;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        /* V2: Pending badge for items needing resolution */
        .pending-badge {
          font-size: 12px;
          opacity: 0.7;
        }

        /* V2: Resolving spinner */
        .resolving-spinner {
          font-size: 14px;
          animation: spin 1s linear infinite;
        }

        .result-item.admin .source-badge {
          background: #fef3c7;
          color: #92400e;
        }

        .result-item.region .source-badge {
          background: #dbeafe;
          color: #1e40af;
        }

        .result-item.poi .source-badge,
        .result-item.es .source-badge {
          background: #dcfce7;
          color: #166534;
        }

        .result-item.google .source-badge {
          background: #fef3c7;
          color: #b45309;
        }

        .result-item.mongodb .source-badge {
          background: #e0e7ff;
          color: #4338ca;
        }

        .result-address,
        .result-type {
          font-size: 13px;
          color: #64748b;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .result-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
          flex-shrink: 0;
        }

        .result-rating,
        .result-distance {
          font-size: 12px;
          color: #64748b;
          white-space: nowrap;
        }

        .result-rating {
          color: #f59e0b;
        }

        .no-results {
          padding: 24px 16px;
          text-align: center;
          color: #64748b;
          font-size: 14px;
        }

        /* Mobile Responsive */
        @media (max-width: 640px) {
          .search-input {
            font-size: 16px; /* Prevent zoom on iOS */
          }

          .result-item {
            padding: 10px 12px;
          }

          .result-meta {
            display: none; /* Hide metadata on mobile */
          }
        }
      `}</style>
    </div>
  );
};

export default SearchAutocomplete;
