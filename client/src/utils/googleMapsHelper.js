/**
 * Google Maps Helper - Generate directions URL from POIs
 * 
 * Purpose:
 * - Create Google Maps directions URL from list of POIs
 * - Support multiple waypoints (up to 25 per route)
 * - Handle different travel modes
 * - Detect mobile and open Google Maps app
 * 
 * Author: Travel Agent P Team
 */

/**
 * Detect if user is on mobile device
 * @returns {boolean}
 */
const isMobileDevice = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
};

/**
 * Generate Google Maps directions URL from list of POIs
 * 
 * @param {Array} pois - List of POI objects with place_id
 * @param {Object} options - Optional settings
 * @param {string} options.travelMode - Travel mode: 'driving', 'walking', 'bicycling', 'transit'
 * @param {string} options.currentLocation - Use current location as origin ('current' or null)
 * @returns {string|null} - Google Maps URL or null if invalid
 * 
 * @example
 * const url = generateGoogleMapsDirectionsURL(
 *   [{ place_id: 'ChIJ...' }, { place_id: 'ChIJ...' }],
 *   { travelMode: 'driving' }
 * );
 */
export const generateGoogleMapsDirectionsURL = (pois, options = {}) => {
  if (!pois || pois.length === 0) return null;
  
  const {
    travelMode = 'driving',  // driving, walking, bicycling, transit
    currentLocation = null   // 'current' to use user's current location
  } = options;
  
  // If only 1 POI, just show it on map
  if (pois.length === 1) {
    const poi = pois[0];
    const placeId = poi.place_id || poi.poi_id || poi.id;
    if (!placeId) return null;
    
    return `https://www.google.com/maps/search/?api=1&query=place_id:${placeId}`;
  }
  
  // Multiple POIs - create directions
  const validPois = pois.filter(poi => {
    const placeId = poi.place_id || poi.poi_id || poi.id;
    return placeId && placeId.trim().length > 0;
  });
  
  if (validPois.length < 2) return null;
  
  // Google Maps supports max 25 waypoints
  const maxPois = Math.min(validPois.length, 25);
  const selectedPois = validPois.slice(0, maxPois);
  
  // Extract place IDs
  const placeIds = selectedPois.map(poi => 
    poi.place_id || poi.poi_id || poi.id
  );
  
  // Build URL
  const origin = currentLocation === 'current' 
    ? 'My+Location'
    : `place_id:${placeIds[0]}`;
  const destination = `place_id:${placeIds[placeIds.length - 1]}`;
  
  // Waypoints (middle points)
  const waypoints = placeIds.slice(1, -1)
    .map(id => `place_id:${id}`)
    .join('|');
  
  const params = new URLSearchParams({
    api: '1',
    origin: origin,
    destination: destination,
    travelmode: travelMode
  });
  
  if (waypoints) {
    params.append('waypoints', waypoints);
  }
  
  return `https://www.google.com/maps/dir/?${params.toString()}`;
};

/**
 * Generate simple Google Maps directions URL (legacy format)
 * Simpler but less control
 * 
 * @param {Array} placeIds - Array of place IDs
 * @returns {string|null} - Google Maps URL
 */
export const generateSimpleDirectionsURL = (placeIds) => {
  if (!placeIds || placeIds.length < 2) return null;
  
  const validIds = placeIds.filter(id => id && id.trim().length > 0);
  if (validIds.length < 2) return null;
  
  const maxIds = Math.min(validIds.length, 25);
  const selectedIds = validIds.slice(0, maxIds);
  
  return `https://www.google.com/maps/dir/${selectedIds.join('/')}`;
};

/**
 * Open Google Maps in new tab
 * 
 * @param {Array} pois - List of POIs
 * @param {Object} options - Options for URL generation
 */
export const openGoogleMapsDirections = (pois, options = {}) => {
  const url = generateGoogleMapsDirectionsURL(pois, options);
  if (url) {
    window.open(url, '_blank');
  } else {
    console.error('[GoogleMaps] Failed to generate URL - invalid POIs');
  }
};

/**
 * Generate Google Maps URL for a single POI
 * 
 * @param {Object} poi - POI object with place_id or coordinates
 * @returns {string|null} - Google Maps URL
 */
export const generatePOIMapURL = (poi) => {
  if (!poi) return null;
  
  const placeId = poi.place_id || poi.poi_id || poi.id;
  
  if (placeId) {
    return `https://www.google.com/maps/search/?api=1&query=place_id:${placeId}`;
  }
  
  // Fallback to coordinates
  const lat = poi.location?.latitude || poi.lat;
  const lng = poi.location?.longitude || poi.lng;
  
  if (lat && lng) {
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  }
  
  // Fallback to name search
  if (poi.name) {
    const query = encodeURIComponent(poi.name);
    return `https://www.google.com/maps/search/?api=1&query=${query}`;
  }
  
  return null;
};

/**
 * Copy Google Maps URL to clipboard
 * 
 * @param {Array} pois - List of POIs
 * @param {Object} options - Options
 * @returns {Promise<boolean>} - Success status
 */
export const copyGoogleMapsURL = async (pois, options = {}) => {
  const url = generateGoogleMapsDirectionsURL(pois, options);
  if (!url) return false;
  
  try {
    await navigator.clipboard.writeText(url);
    return true;
  } catch (error) {
    console.error('[GoogleMaps] Failed to copy URL:', error);
    return false;
  }
};

/**
 * Generate Google Maps directions URL using POI names (simpler, no place_id needed)
 * 
 * @param {Array} pois - List of POI objects with name/poi_name
 * @param {Object} options - Optional settings
 * @param {string} options.travelMode - Travel mode: 'driving', 'walking', 'bicycling', 'transit'
 * @param {string} options.destination - Optional destination city/address to append
 * @returns {string|null} - Google Maps URL or null if invalid
 * 
 * @example
 * const url = generateDirectionsByName(
 *   [{ poi_name: 'Mỹ Khê Beach' }, { poi_name: 'Bà Nà Hills' }],
 *   { travelMode: 'driving', destination: 'Da Nang' }
 * );
 */
export const generateDirectionsByName = (pois, options = {}) => {
  if (!pois || pois.length === 0) return null;
  
  const {
    travelMode = 'driving',
    destination = null,  // Optional city/address to append to searches
    useCurrentLocation = true  // Use current location as origin
  } = options;
  
  // Extract POI names
  const names = pois
    .map(poi => {
      const name = poi.poi_name || poi.name || poi.activity;
      if (!name || typeof name !== 'string') return null;
      
      // Append destination for better accuracy
      const searchQuery = destination 
        ? `${name}, ${destination}`
        : name;
      
      return encodeURIComponent(searchQuery.trim());
    })
    .filter(name => name);
  
  if (names.length === 0) return null;
  
  // If only 1 POI, just show it on map
  if (names.length === 1) {
    return `https://www.google.com/maps/search/?api=1&query=${names[0]}`;
  }
  
  // Multiple POIs - create directions with current location as origin
  // "Current+Location" is a special keyword recognized by Google Maps
  // It tells Google Maps to use the user's ACTUAL current location when the map opens
  // We don't need to fetch location here - Google Maps does it automatically
  const waypoints = useCurrentLocation 
    ? ['Current+Location', ...names]  // Google Maps will request location permission
    : names;
  
  // Format: https://www.google.com/maps/dir/Current+Location/Name1/Name2/Name3
  // When user opens this URL:
  // 1. Google Maps detects "Current+Location" keyword
  // 2. Automatically requests user's location permission
  // 3. Uses actual GPS location as starting point
  // 4. Calculates route from current position to destinations
  return `https://www.google.com/maps/dir/${waypoints.join('/')}`;
};

/**
 * Open Google Maps directions using POI names
 * Opens in Google Maps app on mobile, web browser on desktop
 * 
 * @param {Array} pois - List of POIs with names
 * @param {Object} options - Options
 * @param {boolean} options.useCurrentLocation - Use current location as origin (default: true)
 */
export const openDirectionsByName = (pois, options = {}) => {
  const url = generateDirectionsByName(pois, options);
  if (!url) {
    console.error('[GoogleMaps] Failed to generate URL - invalid POIs');
    return;
  }
  
  const isMobile = isMobileDevice();
  
  if (isMobile) {
    // On mobile: URL will automatically prompt to open Google Maps app
    // User can choose to open in app or continue in browser
    console.log('[GoogleMaps] Opening on mobile device - will prompt for app');
    window.location.href = url;  // Use location.href instead of window.open for better app detection
  } else {
    // On desktop: Open in new tab
    console.log('[GoogleMaps] Opening in new browser tab');
    window.open(url, '_blank');
  }
};
