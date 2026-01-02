/**
 * Image Cache Utility
 * 
 * In-memory + localStorage cache for Google Places photos and thumbnails
 * Reduces API calls and improves performance
 * 
 * Features:
 * - In-memory cache for instant retrieval during session
 * - localStorage persistence for cross-session caching
 * - TTL expiration (default: 7 days for thumbnails, 1 day for Google Photos)
 * - Automatic cleanup of expired entries
 * - Size limit management to prevent localStorage overflow
 */

const CACHE_VERSION = 'v1';
const CACHE_PREFIX = 'img_cache_';
const MEMORY_CACHE = new Map(); // In-memory cache for current session

// Cache TTL configurations (in milliseconds)
const TTL = {
  THUMBNAIL: 7 * 24 * 60 * 60 * 1000,      // 7 days for plan thumbnails
  GOOGLE_PHOTO: 24 * 60 * 60 * 1000,       // 1 day for Google Places photos
  POI_FEATURED: 3 * 24 * 60 * 60 * 1000,   // 3 days for POI featured images
};

// Max localStorage cache size (5 MB)
const MAX_CACHE_SIZE_MB = 5;
const MAX_CACHE_SIZE_BYTES = MAX_CACHE_SIZE_MB * 1024 * 1024;

/**
 * Get cache key with version prefix
 */
const getCacheKey = (url) => {
  return `${CACHE_PREFIX}${CACHE_VERSION}_${url}`;
};

/**
 * Calculate approximate size of cached data in bytes
 */
const getStorageSize = () => {
  let size = 0;
  for (let key in localStorage) {
    if (key.startsWith(CACHE_PREFIX)) {
      size += localStorage[key].length + key.length;
    }
  }
  return size;
};

/**
 * Clean up expired cache entries
 */
const cleanupExpiredCache = () => {
  const now = Date.now();
  let removed = 0;
  
  for (let key in localStorage) {
    if (key.startsWith(CACHE_PREFIX)) {
      try {
        const cached = JSON.parse(localStorage[key]);
        if (cached.expiry < now) {
          localStorage.removeItem(key);
          removed++;
        }
      } catch (e) {
        // Invalid entry, remove it
        localStorage.removeItem(key);
        removed++;
      }
    }
  }
  
  if (removed > 0) {
    // console.log(`[ImageCache] Cleaned up ${removed} expired entries`);
  }
};

/**
 * Remove oldest cache entries if size exceeds limit
 */
const evictOldestEntries = () => {
  const entries = [];
  
  // Collect all cache entries with timestamps
  for (let key in localStorage) {
    if (key.startsWith(CACHE_PREFIX)) {
      try {
        const cached = JSON.parse(localStorage[key]);
        entries.push({ key, timestamp: cached.timestamp });
      } catch (e) {
        localStorage.removeItem(key);
      }
    }
  }
  
  // Sort by timestamp (oldest first)
  entries.sort((a, b) => a.timestamp - b.timestamp);
  
  // Remove oldest entries until size is below limit
  let currentSize = getStorageSize();
  let removed = 0;
  
  for (const entry of entries) {
    if (currentSize <= MAX_CACHE_SIZE_BYTES) break;
    
    const entrySize = localStorage[entry.key].length + entry.key.length;
    localStorage.removeItem(entry.key);
    currentSize -= entrySize;
    removed++;
  }
  
  if (removed > 0) {
    // console.log(`[ImageCache] Evicted ${removed} oldest entries to free space`);
  }
};

/**
 * Get cached image URL
 * 
 * @param {string} url - Original image URL
 * @returns {string|null} - Cached URL or null if not found/expired
 */
export const getCachedImage = (url) => {
  if (!url) return null;
  
  // Check in-memory cache first (fastest)
  if (MEMORY_CACHE.has(url)) {
    const cached = MEMORY_CACHE.get(url);
    if (cached.expiry > Date.now()) {
      return cached.url;
    }
    MEMORY_CACHE.delete(url);
  }
  
  // Check localStorage
  const cacheKey = getCacheKey(url);
  const cached = localStorage.getItem(cacheKey);
  
  if (cached) {
    try {
      const data = JSON.parse(cached);
      
      // Check if expired
      if (data.expiry > Date.now()) {
        // Restore to in-memory cache
        MEMORY_CACHE.set(url, data);
        return data.url;
      }
      
      // Expired, remove it
      localStorage.removeItem(cacheKey);
    } catch (e) {
      console.error('[ImageCache] Parse error:', e);
      localStorage.removeItem(cacheKey);
    }
  }
  
  return null;
};

/**
 * Cache an image URL
 * 
 * @param {string} url - Original image URL
 * @param {string} type - Cache type ('thumbnail', 'google_photo', 'poi_featured')
 * @returns {void}
 */
export const cacheImage = (url, type = 'google_photo') => {
  if (!url) return;
  
  const now = Date.now();
  let ttl = TTL.GOOGLE_PHOTO;
  
  // Determine TTL based on type
  switch (type) {
    case 'thumbnail':
      ttl = TTL.THUMBNAIL;
      break;
    case 'poi_featured':
      ttl = TTL.POI_FEATURED;
      break;
    default:
      ttl = TTL.GOOGLE_PHOTO;
  }
  
  const cacheData = {
    url,
    timestamp: now,
    expiry: now + ttl,
    type
  };
  
  // Store in memory cache
  MEMORY_CACHE.set(url, cacheData);
  
  // Store in localStorage
  try {
    const cacheKey = getCacheKey(url);
    localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    
    // Check storage size and evict if needed
    if (getStorageSize() > MAX_CACHE_SIZE_BYTES) {
      evictOldestEntries();
    }
  } catch (e) {
    if (e.name === 'QuotaExceededError') {
      console.warn('[ImageCache] localStorage quota exceeded, evicting old entries');
      evictOldestEntries();
      
      // Try again
      try {
        const cacheKey = getCacheKey(url);
        localStorage.setItem(cacheKey, JSON.stringify(cacheData));
      } catch (e2) {
        console.error('[ImageCache] Failed to cache after eviction:', e2);
      }
    } else {
      console.error('[ImageCache] Storage error:', e);
    }
  }
};

/**
 * Preload and cache an image
 * 
 * @param {string} url - Image URL to preload
 * @param {string} type - Cache type
 * @returns {Promise<string>} - Resolves with URL when loaded
 */
export const preloadAndCacheImage = (url, type = 'google_photo') => {
  return new Promise((resolve, reject) => {
    if (!url) {
      reject(new Error('No URL provided'));
      return;
    }
    
    // Check if already cached
    const cached = getCachedImage(url);
    if (cached) {
      resolve(cached);
      return;
    }
    
    // Preload image
    const img = new Image();
    img.onload = () => {
      cacheImage(url, type);
      resolve(url);
    };
    img.onerror = (e) => {
      console.error('[ImageCache] Failed to load image:', url, e);
      reject(e);
    };
    img.src = url;
  });
};

/**
 * Clear all cached images
 */
export const clearImageCache = () => {
  // Clear memory cache
  MEMORY_CACHE.clear();
  
  // Clear localStorage cache
  for (let key in localStorage) {
    if (key.startsWith(CACHE_PREFIX)) {
      localStorage.removeItem(key);
    }
  }
  
  // console.log('[ImageCache] All cached images cleared');
};

/**
 * Get cache statistics
 */
export const getCacheStats = () => {
  const memorySize = MEMORY_CACHE.size;
  let localStorageCount = 0;
  let totalSize = 0;
  
  for (let key in localStorage) {
    if (key.startsWith(CACHE_PREFIX)) {
      localStorageCount++;
      totalSize += localStorage[key].length + key.length;
    }
  }
  
  return {
    memoryEntries: memorySize,
    localStorageEntries: localStorageCount,
    totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
    maxSizeMB: MAX_CACHE_SIZE_MB
  };
};

// Run cleanup on module load
cleanupExpiredCache();

// Setup periodic cleanup (every 30 minutes)
setInterval(() => {
  cleanupExpiredCache();
}, 30 * 60 * 1000);
