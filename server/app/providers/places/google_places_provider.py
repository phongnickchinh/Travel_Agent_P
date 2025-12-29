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
from ..type_mapping import map_google_types_to_categories

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
    
    # =========================================================================
    # GEOCODING (for locality/political types)
    # =========================================================================
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    @track_google_places_cost("geocode")
    def geocode_by_place_id(self, place_id: str) -> Optional[Dict[str, float]]:
        """
        Get precise coordinates from Google Geocoding API using place_id.
        
        Use this when Place Details returns a locality/political type
        which may have imprecise or missing coordinates.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Dict with 'latitude' and 'longitude', or None if failed
        """
        if not self.api_key:
            raise ValueError("Google Places API key not configured")
        
        # Geocoding API URL (legacy API, different from Places New API)
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        params = {
            "place_id": place_id,
            "key": self.api_key
        }
        
        logger.info(f"[GEOCODE] Fetching coordinates for place_id: {place_id}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'OK':
                logger.warning(f"[GEOCODE] API returned status: {data.get('status')}")
                return None
            
            results = data.get('results', [])
            if not results:
                logger.warning(f"[GEOCODE] No results for place_id: {place_id}")
                return None
            
            # Get first result's geometry
            geometry = results[0].get('geometry', {})
            location = geometry.get('location', {})
            
            lat = location.get('lat')
            lng = location.get('lng')
            
            if lat is None or lng is None:
                logger.warning(f"[GEOCODE] Missing coordinates in response")
                return None
            
            logger.info(f"[GEOCODE] Got coordinates: lat={lat}, lng={lng}")
            
            return {
                'latitude': lat,
                'longitude': lng
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[GEOCODE] HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[GEOCODE] Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"[GEOCODE] Unexpected error: {e}")
            return None

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
            logger.info(f"Place details response: {place}")
            
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
    
    @CircuitBreakers.GOOGLE_PLACES
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    @track_google_places_cost("photo")
    def get_photo_url(
        self,
        photo_reference: str,
        max_width: int = 800,
        max_height: int = 600
    ) -> Optional[str]:
        """
        Get Google Places photo URL directly (without downloading/uploading).
        
        Returns a URL that frontend can use to display the image.
        This URL will trigger a Google Places API call when accessed,
        but avoids Firebase storage costs.
        
        Args:
            photo_reference: Photo name (format: "places/{place_id}/photos/{photo_id}")
            max_width: Maximum width in pixels (default: 800)
            max_height: Maximum height in pixels (default: 600)
            
        Returns:
            Google Places photo URL string or None if failed
        """
        if not self.api_key:
            logger.warning("Google Places API key not configured")
            return None
        
        # Photo reference format: places/{place_id}/photos/{photo_id}
        # Return URL that includes API key - frontend can use this directly
        url = f"{self.BASE_URL}/{photo_reference}/media"
        
        # Add query parameters
        photo_url = f"{url}?key={self.api_key}&maxHeightPx={max_height}&maxWidthPx={max_width}"
        
        logger.info(f"[PHOTO_URL] Generated URL for {photo_reference}")
        return photo_url
    
    @track_google_places_cost("photo")
    def fetch_and_upload_photo(
        self, 
        photo_reference: str, 
        firebase_helper,
        folder: str = "destinations",
        max_width: int = 800,
        max_height: int = 600
    ) -> Optional[str]:
        """
        Fetch photo from Google Places API and upload to Firebase Storage.
        
        This method fetches the actual photo bytes (not just URL) to avoid
        repeated API calls which cost $7 per 1000 requests.
        
        Args:
            photo_reference: Photo name (format: "places/{place_id}/photos/{photo_id}")
            firebase_helper: FirebaseHelper instance for uploading
            folder: Firebase Storage folder path (default: 'destinations')
            max_width: Maximum width in pixels (default: 800)
            max_height: Maximum height in pixels (default: 600)
            
        Returns:
            Firebase public URL string or None if failed
        """
        if not self.api_key:
            logger.warning("Google Places API key not configured")
            return None
        
        # Photo reference format: places/{place_id}/photos/{photo_id}
        url = f"{self.BASE_URL}/{photo_reference}/media"
        
        params = {
            "key": self.api_key,
            "maxHeightPx": max_height,
            "maxWidthPx": max_width,
            # Do NOT use skipHttpRedirect - we want the actual image bytes
        }
        
        logger.info(f"[PHOTO] Fetching photo bytes from Google: {photo_reference}")
        
        try:
            # Fetch photo bytes
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            # Extract photo ID from reference for filename
            # Format: places/ChIJxxxx/photos/AZLasHxxx
            photo_id = photo_reference.split('/')[-1]
            filename = f"{folder}/{photo_id}.jpg"
            
            # Create a file-like object from bytes
            from io import BytesIO
            file_obj = BytesIO(response.content)
            file_obj.content_type = 'image/jpeg'
            file_obj.seek(0)  # Reset pointer to beginning
            
            # Upload to Firebase
            logger.info(f"[PHOTO] Uploading to Firebase: {filename}")
            firebase_url = firebase_helper.upload_image(file_obj, filename)
            
            if firebase_url:
                logger.info(f"[PHOTO] ✓ Uploaded successfully: {firebase_url[:80]}...")
                return firebase_url
            else:
                logger.warning(f"[PHOTO] Firebase upload failed for {photo_reference}")
                return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[PHOTO] Google API error {e.response.status_code}: {photo_reference}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[PHOTO] Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"[PHOTO] Unexpected error: {e}")
            return None
    
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
            "maxResultCount": max_results
        }
        
        # Add language code if provided
        if language_code:
            payload["languageCode"] = language_code
        
        # Add types if provided
        if types:
            # Nearby Search uses includedTypes (plural) with array
            # Ref: https://developers.google.com/maps/documentation/places/web-service/nearby-search
            payload["includedTypes"] = types if isinstance(types, list) else [types]
        
        logger.info(f"Google Places Nearby Search: location={location}, radius={radius}m, types={types}")
        logger.debug(f"Request payload: {payload}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            # Log error response body for debugging
            if response.status_code != 200:
                logger.error(f"Google API error response: {response.text}")
            
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
        
        Maps Google Places fields to app/model/mongo/poi.py Pydantic models
        Captures ALL available data for rich AI context in LangChain.
        
        Args:
            raw_data: Raw place data from Google API
            
        Returns:
            Standardized POI dictionary matching POI model schema with full Google data
        """
        # =========================================================================
        # BASIC INFO
        # =========================================================================
        place_id = raw_data.get('id', '')
        display_name = raw_data.get('displayName', {})
        name = display_name.get('text', '') if isinstance(display_name, dict) else str(display_name)
        
        # Location
        location_data = raw_data.get('location', {})
        latitude = location_data.get('latitude', 0.0)
        longitude = location_data.get('longitude', 0.0)
        
        # Address
        formatted_address = raw_data.get('formattedAddress', '')
        short_formatted_address = raw_data.get('shortFormattedAddress', '')
        adr_format_address = raw_data.get('adrFormatAddress', '')
        
        # Types
        types = raw_data.get('types', [])
        primary_type = raw_data.get('primaryType', '')
        primary_type_display_name = raw_data.get('primaryTypeDisplayName', {})
        if isinstance(primary_type_display_name, dict):
            primary_type_display_name = primary_type_display_name.get('text', '')
        
        # Rating
        rating = raw_data.get('rating', 0.0)
        user_rating_count = raw_data.get('userRatingCount', 0)
        
        # Price level
        price_level = raw_data.get('priceLevel', '')
        
        # Business status
        business_status = raw_data.get('businessStatus', 'OPERATIONAL')
        
        # UTC offset
        utc_offset_minutes = raw_data.get('utcOffsetMinutes')
        
        # =========================================================================
        # CONTACT INFO
        # =========================================================================
        national_phone = raw_data.get('nationalPhoneNumber', '')
        international_phone = raw_data.get('internationalPhoneNumber', '')
        website = raw_data.get('websiteUri', '')
        google_maps_uri = raw_data.get('googleMapsUri', '')
        
        # =========================================================================
        # PHOTOS - Full capture with attributions
        # =========================================================================
        photos_data = raw_data.get('photos', [])
        photos = []
        for i, photo in enumerate(photos_data[:10]):  # Max 10 photos for detail
            if isinstance(photo, dict):
                author_attributions = []
                for attr in photo.get('authorAttributions', []):
                    author_attributions.append({
                        'displayName': attr.get('displayName', ''),
                        'uri': attr.get('uri', ''),
                        'photoUri': attr.get('photoUri', '')
                    })
                photos.append({
                    'url': photo.get('name', ''),  # Photo reference
                    'photo_reference': photo.get('name', ''),
                    'width': photo.get('widthPx', 0),
                    'height': photo.get('heightPx', 0),
                    'is_primary': i == 0,
                    'author_attributions': author_attributions
                })
        
        # =========================================================================
        # REVIEWS - Full capture with all details
        # =========================================================================
        reviews_data = raw_data.get('reviews', [])
        reviews = []
        for review in reviews_data[:10]:  # Max 10 reviews
            if isinstance(review, dict):
                author_attr = review.get('authorAttribution', {})
                original_text = review.get('originalText', {})
                text_obj = review.get('text', {})
                
                reviews.append({
                    'author_name': author_attr.get('displayName', 'Anonymous'),
                    'author_photo_url': author_attr.get('photoUri', ''),
                    'author_uri': author_attr.get('uri', ''),
                    'rating': review.get('rating', 0),
                    'text': text_obj.get('text', '') if isinstance(text_obj, dict) else str(text_obj),
                    'language': text_obj.get('languageCode', '') if isinstance(text_obj, dict) else '',
                    'publish_time': review.get('publishTime', ''),
                    'relative_publish_time': review.get('relativePublishTimeDescription', '')
                })
        
        # =========================================================================
        # OPENING HOURS - Full capture with periods
        # =========================================================================
        regular_hours = raw_data.get('regularOpeningHours', {})
        current_hours = raw_data.get('currentOpeningHours', {})
        secondary_hours = raw_data.get('regularSecondaryOpeningHours', [])
        current_secondary_hours = raw_data.get('currentSecondaryOpeningHours', [])
        
        weekday_descriptions = regular_hours.get('weekdayDescriptions', []) if regular_hours else []
        periods = regular_hours.get('periods', []) if regular_hours else []
        open_now = current_hours.get('openNow') if current_hours else None
        
        opening_hours_data = {
            'weekday_descriptions': weekday_descriptions,
            'periods': periods,
            'open_now': open_now,
            'is_24_hours': len(periods) == 1 and periods[0].get('open', {}).get('hour') == 0 if periods else False,
            'secondary_hours': secondary_hours
        }
        
        # Map weekday descriptions to individual days
        day_mapping = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, desc in enumerate(weekday_descriptions[:7]):
            if i < len(day_mapping):
                opening_hours_data[day_mapping[i]] = desc
        
        # =========================================================================
        # EDITORIAL SUMMARY (Description)
        # =========================================================================
        editorial_summary = raw_data.get('editorialSummary', {})
        description = editorial_summary.get('text', '') if isinstance(editorial_summary, dict) else ''
        
        # =========================================================================
        # DINING OPTIONS (for restaurants/cafes)
        # =========================================================================
        dining_options = {}
        dining_fields = [
            ('servesBreakfast', 'serves_breakfast'),
            ('servesBrunch', 'serves_brunch'),
            ('servesLunch', 'serves_lunch'),
            ('servesDinner', 'serves_dinner'),
            ('servesDessert', 'serves_dessert'),
            ('servesCoffee', 'serves_coffee'),
            ('servesBeer', 'serves_beer'),
            ('servesWine', 'serves_wine'),
            ('servesCocktails', 'serves_cocktails'),
            ('servesVegetarianFood', 'serves_vegetarian_food'),
        ]
        for google_field, local_field in dining_fields:
            if google_field in raw_data:
                dining_options[local_field] = raw_data[google_field]
        
        # =========================================================================
        # SERVICE OPTIONS
        # =========================================================================
        service_options = {}
        service_fields = [
            ('dineIn', 'dine_in'),
            ('takeout', 'takeout'),
            ('delivery', 'delivery'),
            ('curbsidePickup', 'curbside_pickup'),
            ('reservable', 'reservable'),
            ('outdoorSeating', 'outdoor_seating'),
            ('liveMusic', 'live_music'),
            ('menuForChildren', 'menu_for_children'),
            ('goodForChildren', 'good_for_children'),
            ('goodForGroups', 'good_for_groups'),
            ('goodForWatchingSports', 'good_for_watching_sports'),
            ('allowsDogs', 'allows_dogs'),
            ('restroom', 'restroom'),
        ]
        for google_field, local_field in service_fields:
            if google_field in raw_data:
                service_options[local_field] = raw_data[google_field]
        
        # =========================================================================
        # PAYMENT OPTIONS
        # =========================================================================
        payment_raw = raw_data.get('paymentOptions', {})
        payment_options = {}
        if payment_raw:
            payment_options = {
                'accepts_credit_cards': payment_raw.get('acceptsCreditCards'),
                'accepts_debit_cards': payment_raw.get('acceptsDebitCards'),
                'accepts_cash_only': payment_raw.get('acceptsCashOnly'),
                'accepts_nfc': payment_raw.get('acceptsNfc'),
            }
        
        # =========================================================================
        # PARKING OPTIONS
        # =========================================================================
        parking_raw = raw_data.get('parkingOptions', {})
        parking_options = {}
        if parking_raw:
            parking_options = {
                'free_parking_lot': parking_raw.get('freeParkingLot'),
                'paid_parking_lot': parking_raw.get('paidParkingLot'),
                'free_street_parking': parking_raw.get('freeStreetParking'),
                'paid_street_parking': parking_raw.get('paidStreetParking'),
                'valet_parking': parking_raw.get('valetParking'),
                'free_garage_parking': parking_raw.get('freeGarageParking'),
                'paid_garage_parking': parking_raw.get('paidGarageParking'),
            }
        
        # =========================================================================
        # ACCESSIBILITY OPTIONS
        # =========================================================================
        accessibility_raw = raw_data.get('accessibilityOptions', {})
        accessibility_options = {}
        if accessibility_raw:
            accessibility_options = {
                'wheelchair_accessible_parking': accessibility_raw.get('wheelchairAccessibleParking'),
                'wheelchair_accessible_entrance': accessibility_raw.get('wheelchairAccessibleEntrance'),
                'wheelchair_accessible_restroom': accessibility_raw.get('wheelchairAccessibleRestroom'),
                'wheelchair_accessible_seating': accessibility_raw.get('wheelchairAccessibleSeating'),
            }
        
        # =========================================================================
        # VIEWPORT (for maps)
        # =========================================================================
        viewport_raw = raw_data.get('viewport', {})
        viewport = None
        if viewport_raw:
            viewport = {
                'northeast': {
                    'latitude': viewport_raw.get('high', {}).get('latitude'),
                    'longitude': viewport_raw.get('high', {}).get('longitude'),
                },
                'southwest': {
                    'latitude': viewport_raw.get('low', {}).get('latitude'),
                    'longitude': viewport_raw.get('low', {}).get('longitude'),
                }
            }
        
        # =========================================================================
        # ADDRESS COMPONENTS
        # =========================================================================
        address_components = []
        for component in raw_data.get('addressComponents', []):
            address_components.append({
                'long_name': component.get('longText', ''),
                'short_name': component.get('shortText', ''),
                'types': component.get('types', [])
            })
        
        # Extract country from address components
        country = "Vietnam"  # Default
        city = None
        district = None
        for component in address_components:
            if 'country' in component.get('types', []):
                country = component.get('long_name', country)
            if 'locality' in component.get('types', []):
                city = component.get('long_name')
            if 'administrative_area_level_2' in component.get('types', []):
                district = component.get('long_name')
        
        # =========================================================================
        # FUEL & EV OPTIONS (for gas stations)
        # =========================================================================
        fuel_options = raw_data.get('fuelOptions', {})
        ev_charge_options = raw_data.get('evChargeOptions', {})
        
        # =========================================================================
        # BUILD AMENITIES LIST (for backward compatibility)
        # =========================================================================
        amenities = []
        if dining_options:
            for key, value in dining_options.items():
                if value:
                    amenities.append(key)
        if service_options:
            for key, value in service_options.items():
                if value:
                    amenities.append(key)
        
        # =========================================================================
        # PRICE LEVEL MAPPING
        # =========================================================================
        price_level_map = {
            'PRICE_LEVEL_FREE': 'free',
            'PRICE_LEVEL_INEXPENSIVE': 'cheap',
            'PRICE_LEVEL_MODERATE': 'moderate',
            'PRICE_LEVEL_EXPENSIVE': 'expensive',
            'PRICE_LEVEL_VERY_EXPENSIVE': 'very_expensive'
        }
        price_enum = price_level_map.get(price_level, 'moderate')
        
        # =========================================================================
        # CATEGORY MAPPING
        # =========================================================================
        categories = map_google_types_to_categories(types, primary_type)
        
        # =========================================================================
        # GENERATE DEDUPE KEY & POI ID
        # =========================================================================
        from app.utils.poi_dedupe import normalize_poi_name, generate_dedupe_key
        
        dedupe_key = generate_dedupe_key(name, latitude, longitude)
        poi_id = f"poi_{dedupe_key}"
        
        # =========================================================================
        # BUILD STANDARDIZED POI WITH FULL GOOGLE DATA
        # =========================================================================
        poi = {
            # === Core Identifiers ===
            'poi_id': poi_id,
            'dedupe_key': dedupe_key,
            
            # === Basic Info ===
            'name': name,
            'name_unaccented': normalize_poi_name(name),
            'categories': categories,
            
            # === Location ===
            'location': {
                'type': 'Point',
                'coordinates': [longitude, latitude]
            },
            
            # === Address ===
            'address': {
                'full_address': formatted_address,
                'short_address': short_formatted_address,
                'country': country,
                'city': city,
                'district': district,
            },
            
            # === Description ===
            'description': {
                'short': description[:200] if description else f"{name} - {primary_type_display_name or primary_type}",
                'long': description if description else None
            },
            
            # === Ratings ===
            'ratings': {
                'average': rating if rating > 0 else 0.0,
                'count': user_rating_count
            },
            
            # === Pricing ===
            'pricing': {
                'level': price_enum,
                'currency': 'VND'
            },
            
            # === Contact ===
            'contact': {
                'phone': national_phone,
                'international_phone': international_phone,
                'website': website,
                'google_maps_uri': google_maps_uri
            },
            
            # === Opening Hours ===
            'opening_hours': opening_hours_data,
            
            # === Images ===
            'images': photos,
            
            # === Amenities (flat list for backward compatibility) ===
            'amenities': amenities,
            
            # === Metadata ===
            'metadata': {
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'popularity_score': min(user_rating_count / 10, 100) if user_rating_count else 0
            },
            
            # === Provider Reference ===
            'provider': {
                'name': 'google_places',
                'place_id': place_id,
                'google_maps_uri': google_maps_uri
            },
            
            # =========================================================================
            # GOOGLE EXTENDED DATA - ALL DATA FOR AI CONTEXT
            # =========================================================================
            'google_data': {
                # === Core Google IDs ===
                'google_place_id': place_id,
                'google_maps_uri': google_maps_uri,
                
                # === Type Information ===
                'google_types': types,
                'primary_type': primary_type,
                'primary_type_display_name': primary_type_display_name,
                
                # === Business Info ===
                'business_status': business_status,
                'utc_offset_minutes': utc_offset_minutes,
                
                # === Viewport ===
                'viewport': viewport,
                
                # === Address Components ===
                'address_components': address_components,
                'adr_format_address': adr_format_address,
                'short_formatted_address': short_formatted_address,
                
                # === Reviews (FULL DATA) ===
                'reviews': reviews,
                
                # === Editorial ===
                'editorial_summary': description,
                
                # === Dining Options ===
                'dining_options': dining_options if dining_options else None,
                
                # === Service Options ===
                'service_options': service_options if service_options else None,
                
                # === Payment Options ===
                'payment_options': payment_options if payment_options else None,
                
                # === Parking Options ===
                'parking_options': parking_options if parking_options else None,
                
                # === Accessibility ===
                'accessibility_options': accessibility_options if accessibility_options else None,
                
                # === Fuel/EV ===
                'fuel_options': fuel_options if fuel_options else None,
                'ev_charge_options': ev_charge_options if ev_charge_options else None,
                
                # === Current Opening Hours (real-time) ===
                'current_opening_hours': current_hours if current_hours else None,
                'current_secondary_opening_hours': current_secondary_hours if current_secondary_hours else None,
                
                # === AI-Relevant Signals ===
                'allows_dogs': raw_data.get('allowsDogs'),
                'good_for_children': raw_data.get('goodForChildren'),
                'good_for_groups': raw_data.get('goodForGroups'),
                'good_for_watching_sports': raw_data.get('goodForWatchingSports'),
                
                # === RAW DATA for future-proofing ===
                'raw_google_response': raw_data
            }
        }
        
        logger.debug(f"[TRANSFORM] POI '{name}' transformed with {len(reviews)} reviews, {len(photos)} photos")
        
        return poi
