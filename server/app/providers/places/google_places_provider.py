"""
Google Places Provider Implementation
Integrates with Google Places API (New) for POI data
"""

import os
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

from ..base_provider import BaseProvider
from ...utils.cost_meter import track_google_places_cost
from ...utils.retry_backoff import retry_with_backoff
from ...utils.circuit_breaker import CircuitBreakers

logger = logging.getLogger(__name__)


class GooglePlacesProvider(BaseProvider):
    """
    Google Places API (New) provider implementation
    
    APIs used:
    - Text Search: Find places by query
    - Place Details: Get full details of a place
    - Place Photos: Get photo URLs
    - Nearby Search: Find places near a location
    - Autocomplete: Search suggestions
    
    Docs: https://developers.google.com/maps/documentation/places/web-service/overview
    """
    
    BASE_URL = "https://places.googleapis.com/v1"
    
    # Minimal fields for cost-effective search (reduce API cost by ~70%)
    TEXT_SEARCH_FIELDS_MINIMAL = [
        "places.id",
        "places.displayName",
        "places.location",
        "places.photos",
        "places.types",
        "places.primaryType",
    ]
    
    # All available fields for maximum data extraction
    TEXT_SEARCH_FIELDS = [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.addressComponents",
        "places.location",
        "places.viewport",
        "places.rating",
        "places.googleMapsUri",
        "places.websiteUri",
        "places.regularOpeningHours",
        "places.utcOffsetMinutes",
        "places.businessStatus",
        "places.priceLevel",
        "places.userRatingCount",
        "places.types",
        "places.primaryType",
        "places.primaryTypeDisplayName",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.editorialSummary",
        "places.photos",
        "places.reviews",
        "places.goodForChildren",
        "places.goodForGroups",
        "places.servesBeer",
        "places.servesBreakfast",
        "places.servesBrunch",
        "places.servesCocktails",
        "places.servesCoffee",
        "places.servesDessert",
        "places.servesDinner",
        "places.servesLunch",
        "places.servesVegetarianFood",
        "places.servesWine",
        "places.takeout",
        "places.delivery",
        "places.dineIn",
        "places.curbsidePickup",
        "places.reservable",
        "places.outdoorSeating",
        "places.paymentOptions",
        "places.parkingOptions",
        "places.accessibilityOptions",
        "places.allowsDogs",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Places Provider
        
        Args:
            api_key: Google Places API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        
        if not self.api_key:
            logger.warning("GOOGLE_PLACES_API_KEY not found in environment")
        else:
            logger.info("[INFO] GooglePlacesProvider initialized with API key")
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "google_places"
    
    @CircuitBreakers.GOOGLE_PLACES
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    @track_google_places_cost("text_search")
    def search(self, query: str, location: Dict[str, float], **kwargs) -> List[Dict]:
        """
        Search for places using Google Places Text Search API
        
        Args:
            query: Search query (e.g., "restaurants in Da Nang")
            location: Dict with 'latitude' and 'longitude'
            **kwargs:
                - radius: Search radius in meters (default: 5000)
                - max_results: Max results to return (default: 20, max: 20)
                - types: List of place types to filter
                - min_rating: Minimum rating (0-5)
                - price_level: Price level filter (FREE, INEXPENSIVE, MODERATE, EXPENSIVE, VERY_EXPENSIVE)
                - open_now: Only return open places
                - language_code: Language for results (default: 'vi')
                - field_mode: 'minimal' or 'full' (default: 'minimal' for cost saving)
                
        Returns:
            List of standardized POI dictionaries
        """
        if not self.api_key:
            raise ValueError("Google Places API key not configured")
        
        url = f"{self.BASE_URL}/places:searchText"
        
        # Extract parameters
        radius = kwargs.get('radius', 5000)
        max_results = min(kwargs.get('max_results', 20), 20)  # Max 20 per API
        types = kwargs.get('types', [])
        min_rating = kwargs.get('min_rating')
        price_level = kwargs.get('price_level')
        open_now = kwargs.get('open_now', False)
        language_code = kwargs.get('language_code', 'vi')
        field_mode = kwargs.get('field_mode', 'minimal')  # Default to minimal for cost saving
        
        # Choose field list based on mode
        fields = self.TEXT_SEARCH_FIELDS_MINIMAL if field_mode == 'minimal' else self.TEXT_SEARCH_FIELDS
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(fields)
        }
        
        # Build request payload
        payload = {
            "textQuery": query,
            "languageCode": language_code,
            "maxResultCount": max_results,
        }
        
        # Add location bias (prefer results near this location)
        if location:
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": location.get('latitude'),
                        "longitude": location.get('longitude')
                    },
                    "radius": radius
                }
            }
        
        # Add filters
        # Note: Google Places API (New) only supports SINGLE type filter (not array)
        # Documentation: https://developers.google.com/maps/documentation/places/web-service/text-search#includedtype
        if types and len(types) > 0:
            # Text Search only accepts ONE type - use first type from list
            payload["includedType"] = types[0] if isinstance(types, list) else types
        
        if min_rating:
            payload["minRating"] = float(min_rating)
        
        if price_level:
            # Price levels in new API: PRICE_LEVEL_FREE, PRICE_LEVEL_INEXPENSIVE, 
            # PRICE_LEVEL_MODERATE, PRICE_LEVEL_EXPENSIVE, PRICE_LEVEL_VERY_EXPENSIVE
            payload["priceLevels"] = [price_level] if isinstance(price_level, str) else price_level
        
        if open_now:
            payload["openNow"] = True
        
        logger.info(f"Google Places Text Search: query='{query}', location={location}, radius={radius}m")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            places = data.get('places', [])
            
            logger.info(f"Google Places returned {len(places)} places for query: {query}")
            
            # Transform to standardized POI format
            standardized_places = [self.transform_to_poi(place) for place in places]
            
            return standardized_places
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Google Places API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places API request failed: {e}")
            raise
    
    @CircuitBreakers.GOOGLE_PLACES
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    @track_google_places_cost("place_details")
    def get_details(self, place_id: str) -> Dict:
        """
        Get detailed information about a specific place
        
        Args:
            place_id: Google Place ID (from search results)
            
        Returns:
            Detailed POI dictionary
        """
        if not self.api_key:
            raise ValueError("Google Places API key not configured")
        
        url = f"{self.BASE_URL}/places/{place_id}"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "*"  # Get all available fields
        }
        
        logger.info(f"Fetching Google Place details for ID: {place_id}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            place = response.json()
            
            logger.info(f"Retrieved details for place: {place.get('displayName', {}).get('text', 'Unknown')}")
            
            # Transform to standardized POI format
            standardized_place = self.transform_to_poi(place)
            
            return standardized_place
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Google Places Details API error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places Details API request failed: {e}")
            raise
    
    @CircuitBreakers.GOOGLE_PLACES
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    @track_google_places_cost("photo")
    def get_photos(self, photo_reference: str, max_width: int = 400, max_height: int = 400) -> str:
        """
        Get photo URL from photo reference
        
        Args:
            photo_reference: Photo name from place data (format: "places/{place_id}/photos/{photo_id}")
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            Photo URL string
        """
        if not self.api_key:
            raise ValueError("Google Places API key not configured")
        
        # Photo reference format: places/{place_id}/photos/{photo_id}
        url = f"{self.BASE_URL}/{photo_reference}/media"
        
        params = {
            "key": self.api_key,
            "maxHeightPx": max_height,
            "maxWidthPx": max_width,
            "skipHttpRedirect": True  # Get URL instead of binary
        }
        
        logger.debug(f"Fetching photo URL for: {photo_reference}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            photo_url = data.get('photoUri', '')
            
            logger.debug(f"Retrieved photo URL: {photo_url[:100]}...")
            
            return photo_url
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Google Places Photo API error: {e.response.status_code}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places Photo API request failed: {e}")
            raise
    
    def nearby_search(self, location: Dict[str, float], radius: float = 5000, **kwargs) -> List[Dict]:
        """
        Search for places near a location using Nearby Search API
        
        Args:
            location: Dict with 'latitude' and 'longitude'
            radius: Search radius in meters (default: 5000, max: 50000)
            **kwargs:
                - types: List of place types (e.g., ['restaurant', 'cafe'])
                - max_results: Max results (default: 20, max: 20)
                - language_code: Language (default: 'vi')
                
        Returns:
            List of standardized POI dictionaries
        """
        if not self.api_key:
            raise ValueError("Google Places API key not configured")
        
        url = f"{self.BASE_URL}/places:searchNearby"
        
        max_results = min(kwargs.get('max_results', 20), 20)
        types = kwargs.get('types', [])
        language_code = kwargs.get('language_code', 'vi')
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(self.TEXT_SEARCH_FIELDS)
        }
        
        payload = {
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": location.get('latitude'),
                        "longitude": location.get('longitude')
                    },
                    "radius": min(radius, 50000)  # Max 50km
                }
            },
            "maxResultCount": max_results,
            "languageCode": language_code
        }
        
        if types:
            # Nearby Search also only accepts ONE type
            payload["includedType"] = types[0] if isinstance(types, list) else types
        
        logger.info(f"Google Places Nearby Search: location={location}, radius={radius}m")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            places = data.get('places', [])
            
            logger.info(f"Nearby search returned {len(places)} places")
            
            standardized_places = [self.transform_to_poi(place) for place in places]
            
            return standardized_places
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places Nearby Search failed: {e}")
            raise
    
    def transform_to_poi(self, raw_data: Dict) -> Dict:
        """
        Transform Google Places API response to standardized POI schema
        
        Maps Google Places fields to app/model/poi.py Pydantic models
        
        Args:
            raw_data: Raw place data from Google API
            
        Returns:
            Standardized POI dictionary matching POI model schema
        """
        # Extract basic info
        place_id = raw_data.get('id', '')
        display_name = raw_data.get('displayName', {})
        name = display_name.get('text', '') if isinstance(display_name, dict) else str(display_name)
        
        # Location
        location_data = raw_data.get('location', {})
        latitude = location_data.get('latitude', 0.0)
        longitude = location_data.get('longitude', 0.0)
        
        # Address
        formatted_address = raw_data.get('formattedAddress', '')
        
        # Types
        types = raw_data.get('types', [])
        primary_type = raw_data.get('primaryType', '')
        
        # Rating
        rating = raw_data.get('rating', 0.0)
        user_rating_count = raw_data.get('userRatingCount', 0)
        
        # Price level
        price_level = raw_data.get('priceLevel', '')
        
        # Contact
        phone = raw_data.get('nationalPhoneNumber') or raw_data.get('internationalPhoneNumber', '')
        website = raw_data.get('websiteUri', '')
        
        # Photos
        photos_data = raw_data.get('photos', [])
        photos = []
        for photo in photos_data[:5]:  # Max 5 photos
            if isinstance(photo, dict):
                photos.append({
                    'reference': photo.get('name', ''),
                    'width': photo.get('widthPx', 0),
                    'height': photo.get('heightPx', 0)
                })
        
        # Reviews
        reviews_data = raw_data.get('reviews', [])
        reviews = []
        for review in reviews_data[:5]:  # Max 5 reviews
            if isinstance(review, dict):
                reviews.append({
                    'author': review.get('authorAttribution', {}).get('displayName', 'Anonymous'),
                    'rating': review.get('rating', 0),
                    'text': review.get('text', {}).get('text', ''),
                    'time': review.get('publishTime', '')
                })
        
        # Opening hours
        opening_hours = raw_data.get('regularOpeningHours', {})
        
        # Business status
        business_status = raw_data.get('businessStatus', 'OPERATIONAL')
        
        # Editorial summary (description)
        editorial_summary = raw_data.get('editorialSummary', {})
        description = editorial_summary.get('text', '') if isinstance(editorial_summary, dict) else ''
        
        # Amenities (dining options for restaurants)
        amenities = {}
        if 'servesBeer' in raw_data:
            amenities['serves_beer'] = raw_data['servesBeer']
        if 'servesBreakfast' in raw_data:
            amenities['serves_breakfast'] = raw_data['servesBreakfast']
        if 'servesLunch' in raw_data:
            amenities['serves_lunch'] = raw_data['servesLunch']
        if 'servesDinner' in raw_data:
            amenities['serves_dinner'] = raw_data['servesDinner']
        if 'servesVegetarianFood' in raw_data:
            amenities['vegetarian_options'] = raw_data['servesVegetarianFood']
        if 'takeout' in raw_data:
            amenities['takeout'] = raw_data['takeout']
        if 'delivery' in raw_data:
            amenities['delivery'] = raw_data['delivery']
        if 'dineIn' in raw_data:
            amenities['dine_in'] = raw_data['dineIn']
        if 'reservable' in raw_data:
            amenities['reservable'] = raw_data['reservable']
        if 'goodForChildren' in raw_data:
            amenities['good_for_children'] = raw_data['goodForChildren']
        if 'goodForGroups' in raw_data:
            amenities['good_for_groups'] = raw_data['goodForGroups']
        
        # Build standardized POI
        from app.utils.poi_dedupe import normalize_poi_name, generate_dedupe_key
        
        # Extract country from address components
        country = "Vietnam"  # Default
        for component in raw_data.get('addressComponents', []):
            if 'country' in component.get('types', []):
                country = component.get('longText', country)
                break
        
        # Map Google price level to our enum
        price_level_map = {
            'PRICE_LEVEL_FREE': 'free',
            'PRICE_LEVEL_INEXPENSIVE': 'cheap',
            'PRICE_LEVEL_MODERATE': 'moderate',
            'PRICE_LEVEL_EXPENSIVE': 'expensive',
            'PRICE_LEVEL_VERY_EXPENSIVE': 'expensive'
        }
        price_enum = price_level_map.get(price_level, 'moderate')
        
        # Map types to categories
        category_map = {
            'tourist_attraction': 'landmark',
            'natural_feature': 'nature',
            'beach': 'beach',
            'restaurant': 'restaurant',
            'cafe': 'cafe',
            'bar': 'bar',
            'museum': 'museum',
            'historical_landmark': 'historical',
            'church': 'religious',
            'temple': 'religious',
            'mosque': 'religious',
            'park': 'nature',
            'shopping_mall': 'shopping',
            'hotel': 'hotel',
            'lodging': 'hotel'
        }
        categories = []
        for t in types:
            if t in category_map:
                cat = category_map[t]
                if cat not in categories:
                    categories.append(cat)
        if not categories:
            categories = ['other']
        
        # Generate dedupe_key and poi_id
        dedupe_key = generate_dedupe_key(name, latitude, longitude)
        poi_id = f"poi_{dedupe_key}"
        
        poi = {
            'poi_id': poi_id,
            'dedupe_key': dedupe_key,
            'name': name,
            'name_unaccented': normalize_poi_name(name),
            'categories': categories,  # Required
            'location': {
                'type': 'Point',
                'coordinates': [longitude, latitude]
            },
            'address': {
                'full_address': formatted_address,
                'country': country  # Required
            },
            'description': {
                'short': description[:200] if description else f"{name} - {primary_type}",  # Required, max 200 chars
                'long': description if description else None
            },
            'ratings': {
                'average': rating if rating > 0 else 0.0,  # Required
                'count': user_rating_count
            },
            'pricing': {
                'level': price_enum,  # Required
                'currency': 'VND'
            },
            'contact': {
                'phone': phone,
                'website': website
            },
            'images': [{'url': photo.get('reference', ''), 'is_primary': i == 0} for i, photo in enumerate(photos)],
            'amenities': list(amenities.keys()),
            'metadata': {
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'popularity_score': min(user_rating_count / 10, 100) if user_rating_count else 0
            },
            # Extra fields for reference
            'provider': {
                'name': 'google_places',
                'id': place_id
            },
            'google_maps_uri': raw_data.get('googleMapsUri', ''),
            'raw_data': raw_data  # Keep original data for debugging
        }
        
        return poi
