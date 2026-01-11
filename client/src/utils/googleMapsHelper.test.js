// 🧪 Test Google Maps Integration với POI Names
// Copy code này vào browser console khi đang ở trang plan detail

// ==========================================
// TEST 1: Generate URL với current location làm origin
// ==========================================
const testPOIs = [
  { poi_name: 'Mỹ Khê Beach' },
  { poi_name: 'Bà Nà Hills' },
  { poi_name: 'Cầu Rồng' }
];

// Import hàm (nếu đang test trong component)
// import { generateDirectionsByName, openDirectionsByName } from '../../../utils/googleMapsHelper';

// Test generate URL with current location
const url = generateDirectionsByName(testPOIs, { 
  destination: 'Da Nang',
  useCurrentLocation: true  // Bắt đầu từ vị trí hiện tại
});
console.log('Generated URL with current location:', url);
// Expected: https://www.google.com/maps/dir/Current+Location/M%E1%BB%B9%20Kh%C3%AA%20Beach,%20Da%20Nang/B%C3%A0%20N%C3%A0%20Hills,%20Da%20Nang/C%E1%BA%A7u%20R%E1%BB%93ng,%20Da%20Nang

// Test without current location
const urlNoOrigin = generateDirectionsByName(testPOIs, { 
  destination: 'Da Nang',
  useCurrentLocation: false  // Không dùng vị trí hiện tại
});
console.log('Generated URL without origin:', urlNoOrigin);
// Expected: https://www.google.com/maps/dir/M%E1%BB%B9%20Kh%C3%AA%20Beach,%20Da%20Nang/B%C3%A0%20N%C3%A0%20Hills,%20Da%20Nang/C%E1%BA%A7u%20R%E1%BB%93ng,%20Da%20Nang

// ==========================================
// TEST 2: Mở Google Maps trực tiếp (desktop vs mobile)
// ==========================================
// Desktop: Mở tab mới
// Mobile: Tự động suggest mở Google Maps app

// openDirectionsByName(testPOIs, { 
//   travelMode: 'driving', 
//   destination: 'Da Nang',
//   useCurrentLocation: true  // Bắt đầu từ vị trí hiện tại
// });

// Test mobile detection
console.log('Is mobile device:', /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));

// ==========================================
// TEST 3: Test với dữ liệu thật từ activities
// ==========================================
// Giả sử bạn có day.activities như này:
const mockActivities = [
  { activity: 'Tham quan Bà Nà Hills', poi_name: 'Bà Nà Hills', category: 'tourist_attraction' },
  { activity: 'Ăn trưa tại Madame Lân', name: 'Madame Lân Restaurant', category: 'restaurant' },
  { activity: 'Ngắm cầu Rồng phun lửa', poi_name: 'Cầu Rồng', category: 'landmark' }
];

// Extract POI names (giống logic trong handleOpenGoogleMaps)
const poisWithNames = mockActivities
  .filter(item => item.poi_name || item.name || item.activity)
  .map(item => ({
    poi_name: item.poi_name || item.name || item.activity
  }));

console.log('Extracted POIs:', poisWithNames);

const urlFromActivities = generateDirectionsByName(poisWithNames, { destination: 'Da Nang' });
console.log('URL from activities:', urlFromActivities);

// ==========================================
// TEST 4: Test edge cases
// ==========================================
// Empty array
console.log('Empty array:', generateDirectionsByName([], {})); // null

// Single POI (should use search instead of directions)
const singlePOI = [{ poi_name: 'Mỹ Khê Beach' }];
console.log('Single POI:', generateDirectionsByName(singlePOI, { destination: 'Da Nang' }));
// Expected: https://www.google.com/maps/search/?api=1&query=M%E1%BB%B9%20Kh%C3%AA%20Beach,%20Da%20Nang

// POI with special characters
const specialChars = [
  { poi_name: 'Nhà hàng Bà Nà (Buffet)' },
  { poi_name: 'Biển Mỹ Khê - Đà Nẵng' }
];
console.log('Special chars:', generateDirectionsByName(specialChars, {}));

// ==========================================
// EXPECTED BEHAVIOR:
// ==========================================
// DESKTOP:
// 1. Click "Google Maps" button trong DayItinerary
// 2. handleOpenGoogleMaps() extract names từ activities
// 3. generateDirectionsByName() tạo URL với Current Location làm origin
// 4. openDirectionsByName() mở tab mới với Google Maps
// 5. Google Maps hiển thị route bắt đầu từ vị trí hiện tại

// MOBILE (Android/iOS):
// 1. Click "Google Maps" button
// 2. generateDirectionsByName() tạo URL với Current Location
// 3. openDirectionsByName() detect mobile → dùng window.location.href
// 4. Browser tự động hỏi: "Mở trong Google Maps app?"
// 5. User chọn "Mở" → Google Maps app mở với route sẵn
// 6. Google Maps app request location permission nếu chưa có
// 7. Route bắt đầu từ vị trí hiện tại của user

// ==========================================
// URL FORMAT COMPARISON:
// ==========================================
// OLD (place_id approach):
// https://www.google.com/maps/dir/?api=1&origin=place_id:ChIJ...&destination=place_id:ChIJ...&waypoints=place_id:ChIJ...|place_id:ChIJ...&travelmode=driving

// NEW (name approach - SIMPLER!):
// https://www.google.com/maps/dir/M%E1%BB%B9%20Kh%C3%AA%20Beach,%20Da%20Nang/B%C3%A0%20N%C3%A0%20Hills,%20Da%20Nang/C%E1%BA%A7u%20R%E1%BB%93ng,%20Da%20Nang

// BENEFITS:
// ✅ Không cần google_place_id
// ✅ Không cần query MongoDB cho place_id
// ✅ Dùng data có sẵn ở frontend (poi_name/name/activity)
// ✅ URL ngắn gọn hơn
// ✅ Google Maps tự search theo tên (rất thông minh)

console.log('✅ Google Maps integration test completed!');
