"""
Demo: POI Deduplication Key
============================

Minh họa cách generate và sử dụng dedupe_key để tránh duplicate POI.

Author: Travel Agent P Team
Date: October 27, 2025
"""

import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.poi_dedupe import (
    generate_dedupe_key,
    normalize_poi_name,
    are_pois_duplicate
)


def demo_dedupe_key():
    """Demo generate dedupe_key cho các POI."""
    
    print("=" * 80)
    print("DEMO: POI DEDUPLICATION KEY")
    print("=" * 80)
    
    # Case 1: Same POI from different sources
    print("\n📍 CASE 1: Same POI từ nhiều nguồn (Google Places + TripAdvisor)")
    print("-" * 80)
    
    # Google Places data
    google_name = "Mỹ Khê Beach"
    google_lat = 16.0544
    google_lng = 108.2428
    
    # TripAdvisor data (slightly different name & coordinates)
    tripadvisor_name = "My Khe Beach"
    tripadvisor_lat = 16.0545  # 11m difference
    tripadvisor_lng = 108.2429
    
    google_key = generate_dedupe_key(google_name, google_lat, google_lng)
    tripadvisor_key = generate_dedupe_key(tripadvisor_name, tripadvisor_lat, tripadvisor_lng)
    
    print(f"Google Places:   '{google_name}' ({google_lat}, {google_lng})")
    print(f"  → dedupe_key:  {google_key}")
    print(f"\nTripAdvisor:     '{tripadvisor_name}' ({tripadvisor_lat}, {tripadvisor_lng})")
    print(f"  → dedupe_key:  {tripadvisor_key}")
    print(f"\n✅ RESULT: {'SAME ✓' if google_key == tripadvisor_key else 'DIFFERENT ✗'}")
    print(f"   → Hệ thống sẽ {'MERGE data' if google_key == tripadvisor_key else 'TẠO 2 POI riêng'}")
    
    
    # Case 2: Different POI with similar names
    print("\n\n📍 CASE 2: Different POI có tên giống nhau nhưng khác vị trí")
    print("-" * 80)
    
    beach1_name = "Bãi Biển Mỹ Khê"
    beach1_lat = 16.0544
    beach1_lng = 108.2428
    
    # Another beach with similar name (different city)
    beach2_name = "Bãi Biển Mỹ Khê"
    beach2_lat = 12.2528  # Phan Thiết
    beach2_lng = 109.1967
    
    beach1_key = generate_dedupe_key(beach1_name, beach1_lat, beach1_lng)
    beach2_key = generate_dedupe_key(beach2_name, beach2_lat, beach2_lng)
    
    print(f"Đà Nẵng:       '{beach1_name}' ({beach1_lat}, {beach1_lng})")
    print(f"  → dedupe_key:  {beach1_key}")
    print(f"\nPhan Thiết:    '{beach2_name}' ({beach2_lat}, {beach2_lng})")
    print(f"  → dedupe_key:  {beach2_key}")
    print(f"\n✅ RESULT: {'SAME ✓' if beach1_key == beach2_key else 'DIFFERENT ✗'}")
    print(f"   → Hệ thống sẽ {'MERGE (SAI!)' if beach1_key == beach2_key else 'TẠO 2 POI riêng (ĐÚNG!)'}")
    
    
    # Case 3: Name normalization
    print("\n\n📍 CASE 3: Name Normalization (remove accents, special chars)")
    print("-" * 80)
    
    test_names = [
        "Phố Cổ Hội An",
        "Pho Co Hoi An",
        "Hội An Ancient Town",
        "Hoi An Old Town",
        "Temple of Literature (Văn Miếu)",
        "Văn Miếu - Quốc Tử Giám",
        "Bãi Biển Mỹ Khê",
        "My Khe Beach!!!",
        "  MY   KHE   beach  ",  # Extra spaces
    ]
    
    for name in test_names:
        normalized = normalize_poi_name(name)
        print(f"'{name:40}' → '{normalized}'")
    
    
    # Case 4: Geohash precision
    print("\n\n📍 CASE 4: Geohash Precision (ảnh hưởng đến dedupe)")
    print("-" * 80)
    
    name = "Mỹ Khê Beach"
    lat = 16.0544
    lng = 108.2428
    
    print(f"POI: {name} ({lat}, {lng})\n")
    
    for precision in range(5, 9):
        key = generate_dedupe_key(name, lat, lng, precision=precision)
        
        # Geohash box size
        box_sizes = {
            5: "~5km",
            6: "~1.2km",
            7: "~150m",
            8: "~38m"
        }
        
        print(f"Precision {precision} ({box_sizes[precision]:>7}):  {key}")
    
    print(f"\n💡 TIP: Dùng precision=7 (~150m) là optimal cho POI du lịch")
    
    
    # Case 5: Fuzzy duplicate detection
    print("\n\n📍 CASE 5: Fuzzy Duplicate Detection")
    print("-" * 80)
    
    poi1 = {
        "name": "Phố Cổ Hội An",
        "location": {"coordinates": [108.3259, 15.8801]},
        "dedupe_key": generate_dedupe_key("Phố Cổ Hội An", 15.8801, 108.3259)
    }
    
    poi2 = {
        "name": "Hoi An Ancient Town",
        "location": {"coordinates": [108.3260, 15.8802]},  # 11m difference
        "dedupe_key": generate_dedupe_key("Hoi An Ancient Town", 15.8802, 108.3260)
    }
    
    poi3 = {
        "name": "Hội An Old Quarter",
        "location": {"coordinates": [108.3300, 15.8900]},  # 1.3km difference
        "dedupe_key": generate_dedupe_key("Hội An Old Quarter", 15.8900, 108.3300)
    }
    
    print(f"POI 1: {poi1['name']}")
    print(f"  → dedupe_key: {poi1['dedupe_key']}")
    print(f"\nPOI 2: {poi2['name']} (11m away)")
    print(f"  → dedupe_key: {poi2['dedupe_key']}")
    print(f"  → is_duplicate? {are_pois_duplicate(poi1, poi2)}")
    print(f"  → Reason: {'Same dedupe_key' if poi1['dedupe_key'] == poi2['dedupe_key'] else 'Similar name + close distance (<150m)'}")
    
    print(f"\nPOI 3: {poi3['name']} (1.3km away)")
    print(f"  → dedupe_key: {poi3['dedupe_key']}")
    print(f"  → is_duplicate? {are_pois_duplicate(poi1, poi3)}")
    print(f"  → Reason: {'Different dedupe_key' if poi1['dedupe_key'] != poi3['dedupe_key'] else 'Similar name but far distance (>150m)'}")
    
    
    # Case 6: Real-world examples
    print("\n\n📍 CASE 6: Real-World Examples (Đà Nẵng POIs)")
    print("-" * 80)
    
    danang_pois = [
        {"name": "Bãi Biển Mỹ Khê", "lat": 16.0544, "lng": 108.2428},
        {"name": "Cầu Rồng", "lat": 16.0612, "lng": 108.2272},
        {"name": "Bà Nà Hills", "lat": 15.9949, "lng": 107.9921},
        {"name": "Chùa Linh Ứng", "lat": 16.1058, "lng": 108.2710},
        {"name": "Núi Ngũ Hành Sơn", "lat": 16.0000, "lng": 108.2649},
        {"name": "Bảo tàng Điêu khắc Chăm", "lat": 16.0618, "lng": 108.2226},
    ]
    
    print(f"{'POI Name':<30} {'Coordinates':>20} {'dedupe_key'}")
    print("-" * 80)
    
    for poi in danang_pois:
        key = generate_dedupe_key(poi['name'], poi['lat'], poi['lng'])
        coords = f"({poi['lat']:.4f}, {poi['lng']:.4f})"
        print(f"{poi['name']:<30} {coords:>20} {key}")
    
    
    print("\n\n" + "=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print("\n💡 KEY TAKEAWAYS:")
    print("   1. dedupe_key = normalize(name) + geohash(lat, lng, precision=7)")
    print("   2. Same dedupe_key → MERGE data from multiple sources")
    print("   3. Different dedupe_key → Create separate POI")
    print("   4. Fuzzy match: Similar name + distance <150m → Consider duplicate")
    print("   5. Geohash precision=7 (~150m box) là optimal cho POI du lịch")
    print("\n")


if __name__ == "__main__":
    demo_dedupe_key()
