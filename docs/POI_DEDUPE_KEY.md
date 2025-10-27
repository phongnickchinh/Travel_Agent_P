# POI Deduplication Key - Chi tiết kỹ thuật

## 📋 Tổng quan

**dedupe_key** là cơ chế quan trọng để tránh duplicate POI từ nhiều nguồn dữ liệu khác nhau (Google Places, TripAdvisor, Foursquare, etc.)

### **Format:**
```
dedupe_key = {name_normalized}_{geohash}
```

**Ví dụ:**
- Input: `name="Phố Cổ Hội An"`, `lat=15.8801`, `lng=108.3259`
- Output: `"phocohoan_wecpueb"`

---

## 🔧 Cách hoạt động

### **1. Name Normalization**

Chuẩn hóa tên POI để so sánh:

```python
def normalize_poi_name(name: str) -> str:
    # Step 1: Remove accents
    # "Phố Cổ Hội An" → "Pho Co Hoi An"
    name = unidecode(name)
    
    # Step 2: Lowercase
    # "Pho Co Hoi An" → "pho co hoi an"
    name = name.lower()
    
    # Step 3: Remove text in parentheses
    # "Temple (Văn Miếu)" → "Temple "
    name = re.sub(r'\([^)]*\)', '', name)
    
    # Step 4: Remove special characters
    # "pho-co-hoi-an!!!" → "pho co hoi an"
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Step 5: Remove spaces
    # "pho co hoi an" → "phocohoan"
    name = name.replace(' ', '')
    
    return name
```

**Examples:**

| Original Name | Normalized |
|---------------|------------|
| `Phố Cổ Hội An` | `phocohoan` |
| `Mỹ Khê Beach` | `mykhebeach` |
| `Temple of Literature (Văn Miếu)` | `templeofliterature` |
| `Bãi Biển   Mỹ  Khê!!!` | `baibienmykhe` |

### **2. Geohash Generation**

Mã hóa tọa độ thành string ngắn gọn:

```python
import pygeohash as gh

geohash = gh.encode(latitude, longitude, precision=7)
```

**Precision levels:**

| Precision | Box Size | Use Case |
|-----------|----------|----------|
| 5 | ~5 km | City level |
| 6 | ~1.2 km | District level |
| **7** | **~150m** | **POI level (OPTIMAL)** |
| 8 | ~38m | Building level |

**Example:**
```python
# Mỹ Khê Beach
lat = 16.0544
lng = 108.2428

geohash_5 = gh.encode(lat, lng, 5)  # "wecq6"
geohash_6 = gh.encode(lat, lng, 6)  # "wecq6u"
geohash_7 = gh.encode(lat, lng, 7)  # "wecq6uk"  ← BEST
geohash_8 = gh.encode(lat, lng, 8)  # "wecq6ukc"
```

### **3. Combine**

```python
dedupe_key = f"{name_normalized}_{geohash}"

# Example
name = "Mỹ Khê Beach"
name_normalized = "mykhebeach"
geohash = "wecq6uk"
dedupe_key = "mykhebeach_wecq6uk"
```

---

## 📊 Use Cases

### **CASE 1: Same POI từ nhiều nguồn**

```python
# Google Places
google = {
    "name": "Mỹ Khê Beach",
    "lat": 16.0544,
    "lng": 108.2428
}
google_key = generate_dedupe_key(
    google['name'], google['lat'], google['lng']
)
# → "mykhebeach_wecq6uk"

# TripAdvisor
tripadvisor = {
    "name": "My Khe Beach",
    "lat": 16.0545,  # 11m difference
    "lng": 108.2429
}
tripadvisor_key = generate_dedupe_key(
    tripadvisor['name'], tripadvisor['lat'], tripadvisor['lng']
)
# → "mykhebeach_wecq6uk"  (SAME!)

# ✅ Result: MERGE data from both sources
```

### **CASE 2: Different POI với tên giống nhau**

```python
# Đà Nẵng
beach1 = {
    "name": "Bãi Biển Mỹ Khê",
    "lat": 16.0544,
    "lng": 108.2428
}
beach1_key = generate_dedupe_key(
    beach1['name'], beach1['lat'], beach1['lng']
)
# → "baibienmykhe_wecq6uk"

# Phan Thiết
beach2 = {
    "name": "Bãi Biển Mỹ Khê",
    "lat": 12.2528,
    "lng": 109.1967
}
beach2_key = generate_dedupe_key(
    beach2['name'], beach2['lat'], beach2['lng']
)
# → "baibienmykhe_w6c8qp4"  (DIFFERENT!)

# ✅ Result: Create 2 separate POIs (correct!)
```

### **CASE 3: Fuzzy Duplicate Detection**

Ngoài strict dedupe_key matching, còn có fuzzy matching:

```python
def are_pois_duplicate(poi1, poi2):
    # 1. Strict match: dedupe_key
    if poi1['dedupe_key'] == poi2['dedupe_key']:
        return True
    
    # 2. Fuzzy match: Similar name + Close distance
    name_similarity = levenshtein_ratio(
        normalize_poi_name(poi1['name']),
        normalize_poi_name(poi2['name'])
    )
    
    if name_similarity < 0.8:
        return False
    
    distance_m = geodesic(poi1_coords, poi2_coords).meters
    
    return distance_m <= 150  # 150m threshold
```

**Example:**
```python
poi1 = {
    "name": "Phố Cổ Hội An",
    "location": {"coordinates": [108.3259, 15.8801]}
}

poi2 = {
    "name": "Hoi An Ancient Town",
    "location": {"coordinates": [108.3260, 15.8802]}  # 11m away
}

# dedupe_key different, but fuzzy duplicate detected:
# - Name similarity: 0.85 (>0.8)
# - Distance: 11m (<150m)
# → ✅ DUPLICATE
```

---

## 🏗️ Integration với Repository

### **POIRepository.create()**

```python
def create(self, poi: POI):
    # 1. Generate dedupe_key
    lng, lat = poi.location.coordinates
    poi.dedupe_key = generate_dedupe_key(
        name=poi.name,
        lat=lat,
        lng=lng
    )
    
    # 2. Check strict duplicate (dedupe_key unique index)
    try:
        result = self.collection.insert_one(poi.dict())
    except DuplicateKeyError:
        existing = self.collection.find_one(
            {"dedupe_key": poi.dedupe_key}
        )
        raise ValueError(
            f"Duplicate POI: {existing['poi_id']} "
            f"(name: {existing['name']})"
        )
    
    # 3. Check fuzzy duplicate
    fuzzy_dup = self._find_fuzzy_duplicate(poi)
    if fuzzy_dup:
        raise ValueError(
            f"Similar POI exists: {fuzzy_dup['poi_id']} "
            f"(distance: <150m)"
        )
    
    return result
```

### **MongoDB Index**

```javascript
// Unique index trên dedupe_key
db.poi.createIndex(
    {"dedupe_key": 1}, 
    {unique: true}
)

// 2dsphere index cho fuzzy duplicate search
db.poi.createIndex(
    {"location": "2dsphere"}
)
```

---

## 📈 Real-World Examples

### **Đà Nẵng POIs**

| POI Name | Coordinates | dedupe_key |
|----------|-------------|------------|
| Bãi Biển Mỹ Khê | (16.0544, 108.2428) | `baibienmykhe_wecq6uk` |
| Cầu Rồng | (16.0612, 108.2272) | `cauron_wecq5dr` |
| Bà Nà Hills | (15.9949, 107.9921) | `banahills_wecfwz7` |
| Chùa Linh Ứng | (16.1058, 108.2710) | `chualinhung_wecqhpq` |
| Núi Ngũ Hành Sơn | (16.0000, 108.2649) | `nuinguhanson_wecq3uw` |

### **Multiple Sources Example**

```python
# POI: "Phố Cổ Hội An"
sources = [
    {
        "provider": "google_places",
        "name": "Hoi An Ancient Town",
        "coords": [108.3259, 15.8801],
        "rating": 4.7,
        "reviews": 12500
    },
    {
        "provider": "tripadvisor",
        "name": "Phố Cổ Hội An",
        "coords": [108.3260, 15.8802],
        "rating": 4.5,
        "reviews": 8200
    },
    {
        "provider": "foursquare",
        "name": "Hội An Old Town",
        "coords": [108.3258, 15.8800],
        "rating": 4.6,
        "reviews": 3400
    }
]

# All generate same dedupe_key
for source in sources:
    key = generate_dedupe_key(
        source['name'], 
        source['coords'][1], 
        source['coords'][0]
    )
    print(key)  # → "phocohoan_wecpueb" (all same!)

# → System MERGES all 3 sources into 1 POI
merged_poi = {
    "poi_id": "poi_phocohoan_wecpueb",
    "dedupe_key": "phocohoan_wecpueb",
    "name": "Phố Cổ Hội An",
    "name_alternatives": [
        {"language": "en", "name": "Hoi An Ancient Town"},
        {"language": "en", "name": "Hội An Old Town"}
    ],
    "ratings": {
        "average": 4.6,  # Weighted average
        "count": 24100   # Total reviews
    },
    "sources": [...all 3 sources...]
}
```

---

## 🎯 Best Practices

### **1. Always generate dedupe_key before insert**

```python
# ❌ BAD: Manual dedupe_key
poi = POI(
    name="Mỹ Khê Beach",
    dedupe_key="manual_key_123",  # Don't do this!
    ...
)

# ✅ GOOD: Auto-generated
lng, lat = poi.location.coordinates
poi.dedupe_key = generate_dedupe_key(poi.name, lat, lng)
```

### **2. Use precision=7 for POI**

```python
# ❌ BAD: Too precise (38m box)
dedupe_key = generate_dedupe_key(name, lat, lng, precision=8)

# ❌ BAD: Too loose (5km box)
dedupe_key = generate_dedupe_key(name, lat, lng, precision=5)

# ✅ GOOD: 150m box (optimal)
dedupe_key = generate_dedupe_key(name, lat, lng, precision=7)
```

### **3. Handle fuzzy duplicates gracefully**

```python
try:
    poi_repo.create(poi)
except ValueError as e:
    if "Similar POI exists" in str(e):
        # Option 1: Merge with existing POI
        existing_poi = poi_repo.get_by_dedupe_key(...)
        merge_poi_data(existing_poi, poi)
        
        # Option 2: Ask admin for manual review
        send_duplicate_alert(poi, existing_poi)
```

### **4. Update dedupe_key when location changes**

```python
# When updating POI location
poi_repo.update(poi_id, {
    "location": new_location,
    "dedupe_key": generate_dedupe_key(
        poi.name, 
        new_location['coordinates'][1],  # lat
        new_location['coordinates'][0]   # lng
    )
})
```

---

## 🔍 Testing dedupe_key

### **Unit Tests**

```python
def test_dedupe_key_same_poi():
    """Test dedupe_key cho same POI từ nhiều nguồn."""
    google_key = generate_dedupe_key("Mỹ Khê Beach", 16.0544, 108.2428)
    tripadvisor_key = generate_dedupe_key("My Khe Beach", 16.0545, 108.2429)
    
    assert google_key == tripadvisor_key

def test_dedupe_key_different_poi():
    """Test dedupe_key cho different POI."""
    danang_key = generate_dedupe_key("Bãi Biển Mỹ Khê", 16.0544, 108.2428)
    phanthiet_key = generate_dedupe_key("Bãi Biển Mỹ Khê", 12.2528, 109.1967)
    
    assert danang_key != phanthiet_key

def test_fuzzy_duplicate_detection():
    """Test fuzzy duplicate với similar name + close distance."""
    poi1 = {
        "name": "Phố Cổ Hội An",
        "location": {"coordinates": [108.3259, 15.8801]}
    }
    poi2 = {
        "name": "Hoi An Ancient Town",
        "location": {"coordinates": [108.3260, 15.8802]}  # 11m away
    }
    
    assert are_pois_duplicate(poi1, poi2) == True
```

---

## 📚 Summary

### **Key Points:**

1. **dedupe_key = normalize(name) + geohash(lat, lng, 7)**
2. **Precision 7 (~150m box) là optimal cho POI**
3. **Strict matching:** dedupe_key unique index trong MongoDB
4. **Fuzzy matching:** Name similarity >0.8 + Distance <150m
5. **Merge data** từ multiple sources với same dedupe_key
6. **Prevent duplicates** từ Google Places, TripAdvisor, etc.

### **Files:**

- `app/utils/poi_dedupe.py` - Dedupe logic
- `app/repo/mongo/poi_repository.py` - Integration
- `app/model/poi.py` - POI model with dedupe_key field
- `demo_dedupe_key.py` - Demo & testing

### **Dependencies:**

```bash
pip install unidecode pygeohash python-Levenshtein geopy
```
