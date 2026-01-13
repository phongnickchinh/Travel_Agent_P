"""
Type mapping utilities for external providers.

Centralized mapping from Google Places types to internal CategoryEnum values to
avoid scattering mappings across modules.
"""
from typing import Iterable, List, Optional, Set

from app.model.mongo.poi import CategoryEnum

# =============================================================================
# TABLE B TYPES - RESPONSE ONLY (Cannot be used in Nearby Search/Text Search)
# =============================================================================
# These types from Google Places API Table B may be returned in responses but
# CANNOT be used as includedTypes/excludedTypes in Nearby Search or Text Search.
# Only valid for includedPrimaryTypes in Autocomplete (New) requests.
# Reference: dd.txt - "Values from Table B may NOT be used as part of a request"
TABLE_B_TYPES: Set[str] = {
    "administrative_area_level_3",
    "administrative_area_level_4",
    "administrative_area_level_5",
    "administrative_area_level_6",
    "administrative_area_level_7",
    "archipelago",
    "colloquial_area",
    "continent",
    "establishment",           # Common in responses but NOT valid for requests
    "finance",
    "food",
    "general_contractor",
    "geocode",
    "health",
    "intersection",
    "landmark",                # Common in responses but NOT valid for requests
    "natural_feature",
    "neighborhood",
    "place_of_worship",
    "plus_code",
    "point_of_interest",       # Common in responses but NOT valid for requests
    "political",
    "postal_code_prefix",
    "postal_code_suffix",
    "postal_town",
    "premise",
    "route",
    "street_address",
    "sublocality",
    "sublocality_level_1",
    "sublocality_level_2",
    "sublocality_level_3",
    "sublocality_level_4",
    "sublocality_level_5",
    "subpremise",
    "town_square",             # Added as per Google API error
}

# Types that don't exist in either Table A or Table B (typos or obsolete)
INVALID_TYPES: Set[str] = {
    "nature_preserve",         # Does NOT exist - use "wildlife_refuge" instead
}

# Combined set of types that should NOT be used in API requests
NON_REQUESTABLE_TYPES: Set[str] = TABLE_B_TYPES | INVALID_TYPES


def filter_types_for_request(types: List[str]) -> List[str]:
    """Filter out types that cannot be used in Google Places API requests.
    
    Removes Table B types and invalid types from the list, as these will cause
    400 Bad Request errors when used in Nearby Search or Text Search APIs.
    
    Args:
        types: List of Google Place type strings
        
    Returns:
        Filtered list containing only Table A types (valid for requests)
        
    Example:
        >>> filter_types_for_request(['restaurant', 'point_of_interest', 'establishment'])
        ['restaurant']
    """
    return [t for t in types if t not in NON_REQUESTABLE_TYPES]


# Google Places type -> internal CategoryEnum mapping
# Extended from Google Places API Table A & Table B (dd.txt)
# Last updated: January 2026
# NOTE: This mapping includes Table B types for RESPONSE parsing only
GOOGLE_TYPE_TO_CATEGORY = {
    # ===========================================
    # BEACH
    # ===========================================
    "beach": CategoryEnum.BEACH,
    
    # ===========================================
    # NATURE (parks, gardens, natural areas)
    # ===========================================
    "park": CategoryEnum.NATURE,
    "national_park": CategoryEnum.NATURE,
    "state_park": CategoryEnum.NATURE,
    "garden": CategoryEnum.NATURE,
    "botanical_garden": CategoryEnum.NATURE,
    # Note: "nature_preserve" does NOT exist in Google Places API - removed
    "dog_park": CategoryEnum.NATURE,
    "picnic_ground": CategoryEnum.NATURE,
    "wildlife_park": CategoryEnum.NATURE,
    "wildlife_refuge": CategoryEnum.NATURE,
    
    # ===========================================
    # NATURAL_FEATURE (geographic features)
    # ===========================================
    "natural_feature": CategoryEnum.NATURAL_FEATURE,
    "archipelago": CategoryEnum.NATURAL_FEATURE,
    
    # ===========================================
    # ADVENTURE (outdoor activities, sports adventures)
    # ===========================================
    "hiking_area": CategoryEnum.ADVENTURE,
    "adventure_sports_center": CategoryEnum.ADVENTURE,
    "off_roading_area": CategoryEnum.ADVENTURE,
    "cycling_park": CategoryEnum.ADVENTURE,
    "skateboard_park": CategoryEnum.ADVENTURE,
    "ski_resort": CategoryEnum.ADVENTURE,
    "marina": CategoryEnum.ADVENTURE,
    "fishing_charter": CategoryEnum.ADVENTURE,
    "fishing_pond": CategoryEnum.ADVENTURE,
    
    # ===========================================
    # LANDMARK (tourist attractions, points of interest)
    # ===========================================
    "tourist_attraction": CategoryEnum.LANDMARK,
    "point_of_interest": CategoryEnum.LANDMARK,
    "landmark": CategoryEnum.LANDMARK,
    "observation_deck": CategoryEnum.LANDMARK,
    "plaza": CategoryEnum.LANDMARK,
    "town_square": CategoryEnum.LANDMARK,
    "visitor_center": CategoryEnum.LANDMARK,
    "establishment": CategoryEnum.LANDMARK,
    # Transport hubs as landmarks
    "airport": CategoryEnum.LANDMARK,
    "international_airport": CategoryEnum.LANDMARK,
    "train_station": CategoryEnum.LANDMARK,
    "bus_station": CategoryEnum.LANDMARK,
    "ferry_terminal": CategoryEnum.LANDMARK,
    "transit_station": CategoryEnum.LANDMARK,
    
    # ===========================================
    # HISTORICAL (monuments, historical places)
    # ===========================================
    "monument": CategoryEnum.HISTORICAL,
    "historical_place": CategoryEnum.HISTORICAL,
    "historical_landmark": CategoryEnum.HISTORICAL,
    
    # ===========================================
    # CULTURAL (cultural centers, theaters, art)
    # ===========================================
    "cultural_landmark": CategoryEnum.CULTURAL,
    "performing_arts_theater": CategoryEnum.CULTURAL,
    "cultural_center": CategoryEnum.CULTURAL,
    "art_studio": CategoryEnum.CULTURAL,
    "auditorium": CategoryEnum.CULTURAL,
    "sculpture": CategoryEnum.CULTURAL,
    "amphitheatre": CategoryEnum.CULTURAL,
    "concert_hall": CategoryEnum.CULTURAL,
    "opera_house": CategoryEnum.CULTURAL,
    "philharmonic_hall": CategoryEnum.CULTURAL,
    "comedy_club": CategoryEnum.CULTURAL,
    "dance_hall": CategoryEnum.CULTURAL,
    
    # ===========================================
    # MUSEUM (museums, art galleries)
    # ===========================================
    "museum": CategoryEnum.MUSEUM,
    "art_gallery": CategoryEnum.MUSEUM,
    "planetarium": CategoryEnum.MUSEUM,
    
    # ===========================================
    # RELIGIOUS (places of worship)
    # ===========================================
    "church": CategoryEnum.RELIGIOUS,
    "hindu_temple": CategoryEnum.RELIGIOUS,
    "mosque": CategoryEnum.RELIGIOUS,
    "synagogue": CategoryEnum.RELIGIOUS,
    "place_of_worship": CategoryEnum.RELIGIOUS,
    
    # ===========================================
    # FOOD (all restaurants, food establishments)
    # Changed from RESTAURANT to FOOD for unified category
    # NOTE: "food" is a Table B type (response-only), NOT valid for requests
    # ===========================================
    "restaurant": CategoryEnum.FOOD,
    # Restaurant types (prioritized - most common first)
    "acai_shop": CategoryEnum.FOOD,
    "afghani_restaurant": CategoryEnum.FOOD,
    "african_restaurant": CategoryEnum.FOOD,
    "american_restaurant": CategoryEnum.FOOD,
    "asian_restaurant": CategoryEnum.FOOD,
    "bagel_shop": CategoryEnum.FOOD,
    "bakery": CategoryEnum.FOOD,
    "bar_and_grill": CategoryEnum.FOOD,
    "barbecue_restaurant": CategoryEnum.FOOD,
    "brazilian_restaurant": CategoryEnum.FOOD,
    "breakfast_restaurant": CategoryEnum.FOOD,
    "brunch_restaurant": CategoryEnum.FOOD,
    "buffet_restaurant": CategoryEnum.FOOD,
    "cafeteria": CategoryEnum.FOOD,
    "candy_store": CategoryEnum.FOOD,
    "chinese_restaurant": CategoryEnum.FOOD,
    "chocolate_factory": CategoryEnum.FOOD,
    "chocolate_shop": CategoryEnum.FOOD,
    "confectionery": CategoryEnum.FOOD,
    "deli": CategoryEnum.FOOD,
    "dessert_restaurant": CategoryEnum.FOOD,
    "dessert_shop": CategoryEnum.FOOD,
    "diner": CategoryEnum.FOOD,
    "donut_shop": CategoryEnum.FOOD,
    "fast_food_restaurant": CategoryEnum.FOOD,
    "fine_dining_restaurant": CategoryEnum.FOOD,
    "food_court": CategoryEnum.FOOD,
    "french_restaurant": CategoryEnum.FOOD,
    "greek_restaurant": CategoryEnum.FOOD,
    "hamburger_restaurant": CategoryEnum.FOOD,
    "ice_cream_shop": CategoryEnum.FOOD,
    "indian_restaurant": CategoryEnum.FOOD,
    "indonesian_restaurant": CategoryEnum.FOOD,
    "italian_restaurant": CategoryEnum.FOOD,
    "japanese_restaurant": CategoryEnum.FOOD,
    "juice_shop": CategoryEnum.FOOD,
    "korean_restaurant": CategoryEnum.FOOD,
    "lebanese_restaurant": CategoryEnum.FOOD,
    "meal_delivery": CategoryEnum.FOOD,
    "meal_takeaway": CategoryEnum.FOOD,
    "mediterranean_restaurant": CategoryEnum.FOOD,
    "mexican_restaurant": CategoryEnum.FOOD,
    "middle_eastern_restaurant": CategoryEnum.FOOD,
    "pizza_restaurant": CategoryEnum.FOOD,
    "ramen_restaurant": CategoryEnum.FOOD,
    "sandwich_shop": CategoryEnum.FOOD,
    "seafood_restaurant": CategoryEnum.FOOD,
    "spanish_restaurant": CategoryEnum.FOOD,
    "steak_house": CategoryEnum.FOOD,
    "sushi_restaurant": CategoryEnum.FOOD,
    "thai_restaurant": CategoryEnum.FOOD,
    "turkish_restaurant": CategoryEnum.FOOD,
    "vegan_restaurant": CategoryEnum.FOOD,
    "vegetarian_restaurant": CategoryEnum.FOOD,
    "vietnamese_restaurant": CategoryEnum.FOOD,
    # Food stores
    "food_store": CategoryEnum.FOOD,
    "grocery_store": CategoryEnum.FOOD,
    "asian_grocery_store": CategoryEnum.FOOD,
    "butcher_shop": CategoryEnum.FOOD,
    
    # ===========================================
    # CAFE (coffee shops, tea houses)
    # ===========================================
    "cafe": CategoryEnum.CAFE,
    "coffee_shop": CategoryEnum.CAFE,
    "tea_house": CategoryEnum.CAFE,
    "cat_cafe": CategoryEnum.CAFE,
    "dog_cafe": CategoryEnum.CAFE,
    "internet_cafe": CategoryEnum.CAFE,

    # ===========================================
    # NIGHTLIFE (nightclubs, karaoke, bars, pubs, wine bars)
    # ===========================================
    "bar": CategoryEnum.NIGHTLIFE,
    "pub": CategoryEnum.NIGHTLIFE,
    "wine_bar": CategoryEnum.NIGHTLIFE,
    "night_club": CategoryEnum.NIGHTLIFE,
    "karaoke": CategoryEnum.NIGHTLIFE,
    
    # ===========================================
    # SHOPPING (malls, stores, markets)
    # ===========================================
    "shopping_mall": CategoryEnum.SHOPPING,
    "department_store": CategoryEnum.SHOPPING,
    "market": CategoryEnum.SHOPPING,
    "supermarket": CategoryEnum.SHOPPING,
    "gift_shop": CategoryEnum.SHOPPING,
    "convenience_store": CategoryEnum.SHOPPING,
    "store": CategoryEnum.SHOPPING,
    "auto_parts_store": CategoryEnum.SHOPPING,
    "bicycle_store": CategoryEnum.SHOPPING,
    "book_store": CategoryEnum.SHOPPING,
    "cell_phone_store": CategoryEnum.SHOPPING,
    "clothing_store": CategoryEnum.SHOPPING,
    "discount_store": CategoryEnum.SHOPPING,
    "electronics_store": CategoryEnum.SHOPPING,
    "furniture_store": CategoryEnum.SHOPPING,
    "hardware_store": CategoryEnum.SHOPPING,
    "home_goods_store": CategoryEnum.SHOPPING,
    "home_improvement_store": CategoryEnum.SHOPPING,
    "jewelry_store": CategoryEnum.SHOPPING,
    "liquor_store": CategoryEnum.SHOPPING,
    "pet_store": CategoryEnum.SHOPPING,
    "shoe_store": CategoryEnum.SHOPPING,
    "sporting_goods_store": CategoryEnum.SHOPPING,
    "warehouse_store": CategoryEnum.SHOPPING,
    "wholesaler": CategoryEnum.SHOPPING,
    
    # ===========================================
    # HOTEL (lodging, accommodations)
    # ===========================================
    "hotel": CategoryEnum.HOTEL,
    "lodging": CategoryEnum.HOTEL,
    "resort_hotel": CategoryEnum.HOTEL,
    "guest_house": CategoryEnum.HOTEL,
    "hostel": CategoryEnum.HOTEL,
    "motel": CategoryEnum.HOTEL,
    "bed_and_breakfast": CategoryEnum.HOTEL,
    "budget_japanese_inn": CategoryEnum.HOTEL,
    "campground": CategoryEnum.HOTEL,
    "camping_cabin": CategoryEnum.HOTEL,
    "cottage": CategoryEnum.HOTEL,
    "extended_stay_hotel": CategoryEnum.HOTEL,
    "farmstay": CategoryEnum.HOTEL,
    "inn": CategoryEnum.HOTEL,
    "japanese_inn": CategoryEnum.HOTEL,
    "mobile_home_park": CategoryEnum.HOTEL,
    "private_guest_room": CategoryEnum.HOTEL,
    "rv_park": CategoryEnum.HOTEL,
    
    # ===========================================
    # ENTERTAINMENT (amusement, movies, casinos)
    # ===========================================
    "amusement_park": CategoryEnum.ENTERTAINMENT,
    "amusement_center": CategoryEnum.ENTERTAINMENT,
    "water_park": CategoryEnum.ENTERTAINMENT,
    "casino": CategoryEnum.ENTERTAINMENT,
    "movie_theater": CategoryEnum.ENTERTAINMENT,
    "movie_rental": CategoryEnum.ENTERTAINMENT,
    "bowling_alley": CategoryEnum.ENTERTAINMENT,
    "video_arcade": CategoryEnum.ENTERTAINMENT,
    "ferris_wheel": CategoryEnum.ENTERTAINMENT,
    "roller_coaster": CategoryEnum.ENTERTAINMENT,
    "banquet_hall": CategoryEnum.ENTERTAINMENT,
    "convention_center": CategoryEnum.ENTERTAINMENT,
    "event_venue": CategoryEnum.ENTERTAINMENT,
    "wedding_venue": CategoryEnum.ENTERTAINMENT,
    "community_center": CategoryEnum.ENTERTAINMENT,
    
    # ===========================================
    # FAMILY (family-friendly attractions)
    # ===========================================
    "zoo": CategoryEnum.FAMILY,
    "aquarium": CategoryEnum.FAMILY,
    "childrens_camp": CategoryEnum.FAMILY,
    "playground": CategoryEnum.FAMILY,
    "barbecue_area": CategoryEnum.FAMILY,
    
    # ===========================================
    # WELLNESS (spa, health, relaxation)
    # ===========================================
    "spa": CategoryEnum.WELLNESS,
    "sauna": CategoryEnum.WELLNESS,
    "massage": CategoryEnum.WELLNESS,
    "wellness_center": CategoryEnum.WELLNESS,
    "yoga_studio": CategoryEnum.WELLNESS,
    "skin_care_clinic": CategoryEnum.WELLNESS,
    "tanning_studio": CategoryEnum.WELLNESS,
    "public_bath": CategoryEnum.WELLNESS,
    
    # ===========================================
    # SPORTS (gyms, sports facilities)
    # ===========================================
    "gym": CategoryEnum.SPORTS,
    "fitness_center": CategoryEnum.SPORTS,
    "stadium": CategoryEnum.SPORTS,
    "sports_club": CategoryEnum.SPORTS,
    "arena": CategoryEnum.SPORTS,
    "athletic_field": CategoryEnum.SPORTS,
    "golf_course": CategoryEnum.SPORTS,
    "ice_skating_rink": CategoryEnum.SPORTS,
    "sports_activity_location": CategoryEnum.SPORTS,
    "sports_coaching": CategoryEnum.SPORTS,
    "sports_complex": CategoryEnum.SPORTS,
    "swimming_pool": CategoryEnum.SPORTS,
}


def map_google_types_to_categories(types: Iterable[str], primary_type: Optional[str] = None) -> List[CategoryEnum]:
    """Map Google Places types to internal CategoryEnum list with de-duplication.

    Falls back to primary_type, then to CategoryEnum.OTHER to avoid validation errors.
    """
    categories: List[CategoryEnum] = []
    for t in types or []:
        mapped = GOOGLE_TYPE_TO_CATEGORY.get(t)
        if mapped and mapped not in categories:
            categories.append(mapped)

    if not categories and primary_type:
        mapped = GOOGLE_TYPE_TO_CATEGORY.get(primary_type)
        if mapped:
            categories.append(mapped)

    if not categories:
        categories = [CategoryEnum.OTHER]

    return categories


# Frontend user interest -> CategoryEnum mapping
# Maps interests from CreatePlan.jsx to internal CategoryEnum values
USER_INTEREST_TO_CATEGORY = {
    # Direct matches
    "beach": CategoryEnum.BEACH,
    "nature": CategoryEnum.NATURE,
    "adventure": CategoryEnum.ADVENTURE,
    "food": CategoryEnum.FOOD,
    "cafe": CategoryEnum.CAFE,
    "shopping": CategoryEnum.SHOPPING,
    "nightlife": CategoryEnum.NIGHTLIFE,
    "family": CategoryEnum.FAMILY,
    
    # Mapped interests (no direct CategoryEnum match)
    "culture": CategoryEnum.CULTURAL,      # culture -> cultural
    "history": CategoryEnum.HISTORICAL,    # history -> historical
    "photography": CategoryEnum.LANDMARK,  # photography -> landmark (scenic spots)
    "romantic": CategoryEnum.FOOD,   # romantic -> restaurant (romantic dining)
    "relaxation": CategoryEnum.WELLNESS,   # relaxation -> wellness (spa, massage)
}


def map_user_interests_to_categories(interests: List[str]) -> List[CategoryEnum]:
    """Map frontend user interests to internal CategoryEnum list with de-duplication.
    
    Args:
        interests: List of user interest strings from frontend (e.g., ['photography', 'romantic', 'beach'])
        
    Returns:
        List of CategoryEnum values (de-duplicated)
        
    Example:
        >>> map_user_interests_to_categories(['photography', 'romantic', 'beach'])
        [CategoryEnum.LANDMARK, CategoryEnum.RESTAURANT, CategoryEnum.BEACH]
    """
    categories: List[CategoryEnum] = []
    for interest in interests or []:
        mapped = USER_INTEREST_TO_CATEGORY.get(interest.lower())
        if mapped and mapped not in categories:
            categories.append(mapped)
    
    # If no valid mappings found, return empty list (not OTHER)
    # This allows MongoDB search to find all categories
    return categories


# Priority types per category (most common/useful first)
# Used to limit to 50 types while keeping the best ones
# IMPORTANT: Only Table A types allowed here (valid for Nearby Search requests)
PRIORITY_TYPES_PER_CATEGORY = {
    CategoryEnum.FOOD: [
        "restaurant", "bakery", "fast_food_restaurant", "cafe",
        "vietnamese_restaurant", "japanese_restaurant", "korean_restaurant",
        "chinese_restaurant", "italian_restaurant", "seafood_restaurant",
        "barbecue_restaurant", "pizza_restaurant", "sushi_restaurant",
        "ramen_restaurant", "thai_restaurant", "indian_restaurant",
        "french_restaurant", "fine_dining_restaurant", "buffet_restaurant",
        "ice_cream_shop", "coffee_shop", "dessert_shop",
    ],
    CategoryEnum.CAFE: [
        "cafe", "coffee_shop", "tea_house", "internet_cafe",
    ],
    CategoryEnum.NIGHTLIFE: [
        "bar", "night_club", "pub", "karaoke", "wine_bar",
    ],
    CategoryEnum.SHOPPING: [
        "shopping_mall", "market", "supermarket", "department_store",
        "convenience_store", "gift_shop", "clothing_store", "book_store",
    ],
    CategoryEnum.LANDMARK: [
        # Table A types only - removed: landmark, point_of_interest, town_square (Table B)
        "tourist_attraction", "observation_deck", "plaza", "visitor_center",
    ],
    CategoryEnum.CULTURAL: [
        "performing_arts_theater", "cultural_center", "art_studio",
        "concert_hall", "amphitheatre", "opera_house", "cultural_landmark",
        "auditorium", "sculpture", "philharmonic_hall", "comedy_club", "dance_hall",
    ],
    CategoryEnum.HISTORICAL: [
        "historical_landmark", "historical_place", "monument",
    ],
    CategoryEnum.MUSEUM: [
        "museum", "art_gallery", "planetarium",
    ],
    CategoryEnum.BEACH: [
        "beach",
    ],
    CategoryEnum.NATURE: [
        # Table A types only - removed: nature_preserve (invalid type)
        "park", "national_park", "botanical_garden", "garden",
        "wildlife_park", "dog_park", "state_park", "picnic_ground", "wildlife_refuge",
    ],
    CategoryEnum.ADVENTURE: [
        "hiking_area", "ski_resort", "marina", "adventure_sports_center",
        "off_roading_area", "cycling_park", "skateboard_park",
        "fishing_charter", "fishing_pond",
    ],
    CategoryEnum.WELLNESS: [
        "spa", "massage", "sauna", "yoga_studio", "wellness_center",
        "public_bath", "skin_care_clinic", "tanning_studio",
    ],
    CategoryEnum.SPORTS: [
        "gym", "fitness_center", "stadium", "sports_club",
        "golf_course", "swimming_pool", "sports_complex",
        "arena", "athletic_field", "ice_skating_rink",
        "sports_activity_location", "sports_coaching",
    ],
    CategoryEnum.FAMILY: [
        "zoo", "aquarium", "playground", "amusement_park",
        "childrens_camp", "barbecue_area",
    ],
    CategoryEnum.ENTERTAINMENT: [
        "amusement_park", "water_park", "movie_theater", "casino",
        "bowling_alley", "video_arcade", "event_venue",
        "amusement_center", "ferris_wheel", "roller_coaster",
        "banquet_hall", "convention_center", "wedding_venue", "community_center",
    ],
    CategoryEnum.RELIGIOUS: [
        # Table A types only - removed: place_of_worship (Table B)
        "church", "hindu_temple", "mosque", "synagogue",
    ],
}

# Max types allowed by Google Nearby Search API
GOOGLE_MAX_TYPES = 50


def map_user_interests_to_google_types(interests: List[str], max_types: int = GOOGLE_MAX_TYPES) -> List[str]:
    """Map frontend user interests to Google Place Types via CategoryEnum intermediate mapping.
    
    This function provides extended coverage by:
    1. Mapping user interests → CategoryEnum (using USER_INTEREST_TO_CATEGORY)
    2. Mapping CategoryEnum → Google types (using PRIORITY_TYPES_PER_CATEGORY first, then fallback)
    3. Limiting to max_types (default 50 - Google API limit)
    4. Deduplicating results
    
    Args:
        interests: List of user interest strings from frontend (e.g., ['photography', 'romantic', 'beach', 'cafe'])
        max_types: Maximum number of types to return (default: 50, Google API limit)
        
    Returns:
        List of Google Place Type strings (de-duplicated, max 50)
        
    Example:
        >>> map_user_interests_to_google_types(['photography', 'beach', 'cafe'])
        ['tourist_attraction', 'landmark', 'point_of_interest', 'beach', 'cafe', 'coffee_shop']
        
    Note:
        - Returns priority types first (most common/useful)
        - Limited to 50 types (Google Nearby Search API limit)
        - Excludes accommodation types (HOTEL category) - those are fetched separately
        - Returns empty list if no valid mappings found (fallback handled by caller)
    """
    # Step 1: Map interests to CategoryEnum
    categories = map_user_interests_to_categories(interests)
    
    # Step 2: Collect Google types with priority ordering
    google_types: List[str] = []
    seen = set()
    
    # First pass: Add priority types for each category
    for category in categories:
        # Exclude HOTEL category (handled separately for accommodations)
        if category == CategoryEnum.HOTEL:
            continue
        
        # Add priority types first
        priority_types = PRIORITY_TYPES_PER_CATEGORY.get(category, [])
        for t in priority_types:
            if t not in seen and len(google_types) < max_types:
                seen.add(t)
                google_types.append(t)
    
    # Second pass: Add remaining types from GOOGLE_TYPE_TO_CATEGORY if space available
    if len(google_types) < max_types:
        # Build reverse mapping: CategoryEnum → List[Google types]
        category_to_google_types = {}
        for google_type, category in GOOGLE_TYPE_TO_CATEGORY.items():
            if category not in category_to_google_types:
                category_to_google_types[category] = []
            category_to_google_types[category].append(google_type)
        
        for category in categories:
            if category == CategoryEnum.HOTEL:
                continue
                
            types = category_to_google_types.get(category, [])
            for t in types:
                if t not in seen and len(google_types) < max_types:
                    seen.add(t)
                    google_types.append(t)
    
    # Filter out Table B types and invalid types (not allowed in Nearby Search/Text Search)
    return filter_types_for_request(google_types)
