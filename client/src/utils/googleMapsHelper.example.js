/**
 * Google Maps Helper - Usage Examples
 * 
 * This file demonstrates how to use googleMapsHelper.js
 */

import {
    copyGoogleMapsURL,
    generateGoogleMapsDirectionsURL,
    generatePOIMapURL,
    generateSimpleDirectionsURL,
    openGoogleMapsDirections
} from './googleMapsHelper';

// ============================================
// EXAMPLE 1: Basic Directions URL
// ============================================
const example1 = () => {
  const pois = [
    { place_id: 'ChIJN1t_tDeuEmsRUsoyG83frY4', name: 'Mỹ Khê Beach' },
    { place_id: 'ChIJAQAAAEauEmsR1qkjZ5Sm6kQ', name: 'Bà Nà Hills' },
    { place_id: 'ChIJv3W8dDauEmsRCYvFGMZmZH0', name: 'Cầu Rồng' }
  ];

  const url = generateGoogleMapsDirectionsURL(pois);
  console.log('Directions URL:', url);
  // → https://www.google.com/maps/dir/?api=1&origin=place_id:ChIJ...&destination=place_id:ChIJ...&waypoints=place_id:ChIJ...&travelmode=driving
};

// ============================================
// EXAMPLE 2: Walking Directions
// ============================================
const example2 = () => {
  const pois = [
    { place_id: 'ChIJ...', name: 'Hotel' },
    { place_id: 'ChIJ...', name: 'Restaurant' },
    { place_id: 'ChIJ...', name: 'Beach' }
  ];

  const url = generateGoogleMapsDirectionsURL(pois, { 
    travelMode: 'walking'  // walking, bicycling, transit
  });
  
  console.log('Walking URL:', url);
};

// ============================================
// EXAMPLE 3: From Current Location
// ============================================
const example3 = () => {
  const pois = [
    { place_id: 'ChIJ...', name: 'First Stop' },
    { place_id: 'ChIJ...', name: 'Second Stop' }
  ];

  const url = generateGoogleMapsDirectionsURL(pois, { 
    currentLocation: 'current'  // Use user's current location as origin
  });
  
  console.log('From current location:', url);
};

// ============================================
// EXAMPLE 4: Simple URL (No API parameter)
// ============================================
const example4 = () => {
  const placeIds = [
    'ChIJN1t_tDeuEmsRUsoyG83frY4',
    'ChIJAQAAAEauEmsR1qkjZ5Sm6kQ',
    'ChIJv3W8dDauEmsRCYvFGMZmZH0'
  ];

  const url = generateSimpleDirectionsURL(placeIds);
  console.log('Simple URL:', url);
  // → https://www.google.com/maps/dir/ChIJ.../ChIJ.../ChIJ...
};

// ============================================
// EXAMPLE 5: Open in New Tab
// ============================================
const example5 = () => {
  const pois = [
    { place_id: 'ChIJ...', name: 'Start' },
    { place_id: 'ChIJ...', name: 'End' }
  ];

  // Opens Google Maps in new tab
  openGoogleMapsDirections(pois, { travelMode: 'driving' });
};

// ============================================
// EXAMPLE 6: Single POI Map
// ============================================
const example6 = () => {
  const poi = { 
    place_id: 'ChIJN1t_tDeuEmsRUsoyG83frY4',
    name: 'Mỹ Khê Beach'
  };

  const url = generatePOIMapURL(poi);
  console.log('Single POI URL:', url);
  // → https://www.google.com/maps/search/?api=1&query=place_id:ChIJ...
};

// ============================================
// EXAMPLE 7: Copy URL to Clipboard
// ============================================
const example7 = async () => {
  const pois = [
    { place_id: 'ChIJ...', name: 'Start' },
    { place_id: 'ChIJ...', name: 'End' }
  ];

  const success = await copyGoogleMapsURL(pois, { travelMode: 'walking' });
  
  if (success) {
    alert('URL đã được copy vào clipboard!');
  } else {
    alert('Không thể copy URL');
  }
};

// ============================================
// EXAMPLE 8: From Plan Data
// ============================================
const example8 = () => {
  // Sample plan day data
  const day = {
    activities: [
      { poi_name: 'Mỹ Khê Beach', poi_id: 'ChIJN1t_tDeuEmsRUsoyG83frY4' },
      { poi_name: 'Bà Nà Hills', poi_id: 'ChIJAQAAAEauEmsR1qkjZ5Sm6kQ' },
      { poi_name: 'Cầu Rồng', poi_id: 'ChIJv3W8dDauEmsRCYvFGMZmZH0' }
    ],
    poi_ids: [
      'ChIJN1t_tDeuEmsRUsoyG83frY4',
      'ChIJAQAAAEauEmsR1qkjZ5Sm6kQ',
      'ChIJv3W8dDauEmsRCYvFGMZmZH0'
    ]
  };

  // Convert to POI format
  const pois = day.poi_ids.map((poi_id, index) => ({
    place_id: poi_id,
    name: day.activities[index]?.poi_name || `Stop ${index + 1}`
  }));

  const url = generateGoogleMapsDirectionsURL(pois);
  console.log('Plan day URL:', url);
};

// ============================================
// EXAMPLE 9: Handle Max 25 Waypoints
// ============================================
const example9 = () => {
  // Google Maps supports max 25 waypoints per route
  const manyPois = Array(30).fill(null).map((_, i) => ({
    place_id: `ChIJ_fake_id_${i}`,
    name: `Stop ${i + 1}`
  }));

  // Function automatically limits to 25
  const url = generateGoogleMapsDirectionsURL(manyPois);
  console.log('Capped at 25 POIs:', url);
};

// ============================================
// EXAMPLE 10: In React Component
// ============================================
/*
import { openGoogleMapsDirections } from '../utils/googleMapsHelper';

function DayItinerary({ day }) {
  const handleOpenMaps = () => {
    // Extract POIs from day
    const pois = day.poi_ids?.map((poi_id, index) => ({
      place_id: poi_id,
      name: day.activities[index]?.poi_name || `Stop ${index + 1}`
    })) || [];

    if (pois.length < 2) {
      alert('Cần ít nhất 2 địa điểm để tạo tuyến đường');
      return;
    }

    openGoogleMapsDirections(pois, { travelMode: 'driving' });
  };

  return (
    <button onClick={handleOpenMaps}>
      Mở Google Maps
    </button>
  );
}
*/

// ============================================
// EXAMPLE 11: Error Handling
// ============================================
const example11 = () => {
  const invalidPois = [
    { name: 'No Place ID' },  // Missing place_id
    { place_id: '' }          // Empty place_id
  ];

  const url = generateGoogleMapsDirectionsURL(invalidPois);
  console.log('Invalid POIs:', url);  // → null
};

export {
    example1, example11, example2,
    example3,
    example4,
    example5,
    example6,
    example7,
    example8,
    example9
};

