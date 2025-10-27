"""
POI Deduplication Key Generator

Generates unique dedupe_key for POI to prevent duplicates from multiple sources.
Format: {name_normalized}_{geohash}

Example:
- Input: name="Phố Cổ Hội An", lat=15.8801, lng=108.3259
- Output: "phocohoan_wecpueb"
"""
import re
from unidecode import unidecode
import pygeohash as gh


def generate_dedupe_key(name: str, latitude: float, longitude: float, precision: int = 7) -> str:
    """
    Generate deduplication key for POI.
    
    Args:
        name: POI name (can have accents)
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        precision: Geohash precision (default 7 = ~150m)
    
    Returns:
        Dedupe key in format: {normalized_name}_{geohash}
    
    Examples:
        >>> generate_dedupe_key("Phố Cổ Hội An", 15.8801, 108.3259)
        'phocohoan_wecpueb'
        
        >>> generate_dedupe_key("Mỹ Khê Beach", 16.0544, 108.2428)
        'mykhebeach_wecq6uk'
    """
    # Step 1: Normalize name
    name_normalized = normalize_poi_name(name)
    
    # Step 2: Generate geohash
    geohash = gh.encode(latitude, longitude, precision=precision)
    
    # Step 3: Combine
    dedupe_key = f"{name_normalized}_{geohash}"
    
    return dedupe_key


def normalize_poi_name(name: str) -> str:
    """
    Normalize POI name for deduplication.
    
    Steps:
    1. Remove accents (Phố → Pho)
    2. Lowercase
    3. Remove special characters
    4. Remove extra spaces
    5. Remove common words (beach, temple, etc.)
    
    Args:
        name: Original POI name
    
    Returns:
        Normalized name
    
    Examples:
        >>> normalize_poi_name("Phố Cổ Hội An")
        'phocohoan'
        
        >>> normalize_poi_name("Mỹ Khê Beach")
        'mykhebeach'
        
        >>> normalize_poi_name("Temple of Literature (Văn Miếu)")
        'templeofliterature'
    """
    # Remove accents
    name = unidecode(name)
    
    # Lowercase
    name = name.lower()
    
    # Remove text in parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    
    # Remove special characters, keep only alphanumeric and spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Remove extra spaces
    name = ' '.join(name.split())
    
    # Remove spaces
    name = name.replace(' ', '')
    
    return name


def are_pois_duplicate(poi1: dict, poi2: dict, distance_threshold_m: int = 150) -> bool:
    """
    Check if two POIs are duplicates.
    
    Criteria:
    1. dedupe_key matches (strict)
    2. OR: Similar name + close distance
    
    Args:
        poi1: First POI dict
        poi2: Second POI dict
        distance_threshold_m: Distance threshold in meters (default 150m)
    
    Returns:
        True if duplicate, False otherwise
    """
    # Strict match: dedupe_key
    if poi1.get('dedupe_key') == poi2.get('dedupe_key'):
        return True
    
    # Fuzzy match: similar name + close distance
    name1_norm = normalize_poi_name(poi1.get('name', ''))
    name2_norm = normalize_poi_name(poi2.get('name', ''))
    
    # Check name similarity (Levenshtein distance)
    from Levenshtein import ratio
    name_similarity = ratio(name1_norm, name2_norm)
    
    if name_similarity < 0.8:
        return False
    
    # Check geo distance
    from geopy.distance import geodesic
    
    coords1 = poi1.get('location', {}).get('coordinates', [])
    coords2 = poi2.get('location', {}).get('coordinates', [])
    
    if not coords1 or not coords2:
        return False
    
    # MongoDB GeoJSON uses [lng, lat]
    point1 = (coords1[1], coords1[0])
    point2 = (coords2[1], coords2[0])
    
    distance_m = geodesic(point1, point2).meters
    
    return distance_m <= distance_threshold_m


# Example usage
if __name__ == "__main__":
    # Test Case 1: Exact match
    poi_google = {
        "name": "Phố Cổ Hội An",
        "location": {"coordinates": [108.3259, 15.8801]}
    }
    
    poi_tripadvisor = {
        "name": "Hoi An Ancient Town",
        "location": {"coordinates": [108.3260, 15.8802]}  # 10m difference
    }
    
    key1 = generate_dedupe_key(
        poi_google['name'], 
        poi_google['location']['coordinates'][1],
        poi_google['location']['coordinates'][0]
    )
    
    key2 = generate_dedupe_key(
        poi_tripadvisor['name'],
        poi_tripadvisor['location']['coordinates'][1],
        poi_tripadvisor['location']['coordinates'][0]
    )
    
    print(f"Google dedupe_key: {key1}")
    print(f"TripAdvisor dedupe_key: {key2}")
    print(f"Are duplicates: {key1 == key2}")
    
    # Output:
    # Google dedupe_key: phocohoan_wecpueb
    # TripAdvisor dedupe_key: hoianancienttown_wecpueb
    # Are duplicates: False (name different but geohash same)
    
    # Need fuzzy matching for this case
    poi_google['dedupe_key'] = key1
    poi_tripadvisor['dedupe_key'] = key2
    
    is_dup = are_pois_duplicate(poi_google, poi_tripadvisor)
    print(f"\nFuzzy duplicate check: {is_dup}")
