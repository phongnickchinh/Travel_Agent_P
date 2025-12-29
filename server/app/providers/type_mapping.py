"""
Type mapping utilities for external providers.

Centralized mapping from Google Places types to internal CategoryEnum values to
avoid scattering mappings across modules.
"""
from typing import Iterable, List, Optional

from app.model.mongo.poi import CategoryEnum

# Google Places type -> internal CategoryEnum mapping
GOOGLE_TYPE_TO_CATEGORY = {
    # Nature & outdoors
    "beach": CategoryEnum.BEACH,
    "park": CategoryEnum.NATURE,
    "national_park": CategoryEnum.NATURE,
    "state_park": CategoryEnum.NATURE,
    "garden": CategoryEnum.NATURE,
    "botanical_garden": CategoryEnum.NATURE,
    "nature_preserve": CategoryEnum.NATURE,
    "natural_feature": CategoryEnum.NATURAL_FEATURE,
    "hiking_area": CategoryEnum.ADVENTURE,

    # Landmarks & attractions
    "tourist_attraction": CategoryEnum.LANDMARK,
    "point_of_interest": CategoryEnum.LANDMARK,
    "landmark": CategoryEnum.LANDMARK,
    "monument": CategoryEnum.HISTORICAL,
    "historical_place": CategoryEnum.HISTORICAL,
    "historical_landmark": CategoryEnum.HISTORICAL,
    "cultural_landmark": CategoryEnum.CULTURAL,

    # Culture & museums
    "museum": CategoryEnum.MUSEUM,
    "art_gallery": CategoryEnum.MUSEUM,
    "performing_arts_theater": CategoryEnum.CULTURAL,

    # Religious
    "church": CategoryEnum.RELIGIOUS,
    "temple": CategoryEnum.RELIGIOUS,
    "mosque": CategoryEnum.RELIGIOUS,
    "synagogue": CategoryEnum.RELIGIOUS,
    "hindu_temple": CategoryEnum.RELIGIOUS,

    # Food & drink
    "restaurant": CategoryEnum.RESTAURANT,
    "fast_food_restaurant": CategoryEnum.RESTAURANT,
    "seafood_restaurant": CategoryEnum.RESTAURANT,
    "barbecue_restaurant": CategoryEnum.RESTAURANT,
    "vietnamese_restaurant": CategoryEnum.RESTAURANT,
    "japanese_restaurant": CategoryEnum.RESTAURANT,
    "korean_restaurant": CategoryEnum.RESTAURANT,
    "chinese_restaurant": CategoryEnum.RESTAURANT,
    "italian_restaurant": CategoryEnum.RESTAURANT,
    "french_restaurant": CategoryEnum.RESTAURANT,
    "fine_dining_restaurant": CategoryEnum.RESTAURANT,
    "cafe": CategoryEnum.CAFE,
    "coffee_shop": CategoryEnum.CAFE,
    "bakery": CategoryEnum.FOOD,
    "food_court": CategoryEnum.FOOD,
    "meal_takeaway": CategoryEnum.FOOD,
    "meal_delivery": CategoryEnum.FOOD,
    "bar": CategoryEnum.BAR,
    "pub": CategoryEnum.BAR,
    "night_club": CategoryEnum.NIGHTLIFE,

    # Shopping
    "shopping_mall": CategoryEnum.SHOPPING,
    "department_store": CategoryEnum.SHOPPING,
    "market": CategoryEnum.SHOPPING,
    "supermarket": CategoryEnum.SHOPPING,
    "gift_shop": CategoryEnum.SHOPPING,
    "convenience_store": CategoryEnum.SHOPPING,

    # Lodging
    "hotel": CategoryEnum.HOTEL,
    "lodging": CategoryEnum.HOTEL,
    "resort_hotel": CategoryEnum.HOTEL,
    "guest_house": CategoryEnum.HOTEL,
    "hostel": CategoryEnum.HOTEL,
    "motel": CategoryEnum.HOTEL,
    "bed_and_breakfast": CategoryEnum.HOTEL,

    # Entertainment & leisure
    "amusement_park": CategoryEnum.ENTERTAINMENT,
    "water_park": CategoryEnum.ENTERTAINMENT,
    "casino": CategoryEnum.ENTERTAINMENT,
    "movie_theater": CategoryEnum.ENTERTAINMENT,
    "bowling_alley": CategoryEnum.ENTERTAINMENT,
    "zoo": CategoryEnum.FAMILY,
    "aquarium": CategoryEnum.FAMILY,
    "spa": CategoryEnum.WELLNESS,
    "gym": CategoryEnum.SPORTS,
    "fitness_center": CategoryEnum.SPORTS,

    # Sports / activities
    "stadium": CategoryEnum.SPORTS,
    "sports_club": CategoryEnum.SPORTS,

    # Transport (group to landmark/other as needed)
    "airport": CategoryEnum.LANDMARK,
    "train_station": CategoryEnum.LANDMARK,
    "bus_station": CategoryEnum.LANDMARK,
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
