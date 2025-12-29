"""
POI (Point of Interest) Data Models
====================================

Purpose:
- Pydantic models for POI data validation
- Matches MongoDB poi_unified.json schema
- Type-safe data handling with validation
- Captures ALL data from Google Places API for rich AI context

Author: Travel Agent P Team
Date: October 27, 2025 (Extended December 29, 2025)
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, field_validator
from datetime import datetime
from enum import Enum


# Enums
class PriceLevelEnum(str, Enum):
    """Price level categories for POI."""
    FREE = "free"
    CHEAP = "cheap"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"
    VERY_EXPENSIVE = "very_expensive"


class BusinessStatusEnum(str, Enum):
    """Business status from Google Places."""
    OPERATIONAL = "operational"
    CLOSED_TEMPORARILY = "closed_temporarily"
    CLOSED_PERMANENTLY = "closed_permanently"
    UNKNOWN = "unknown"


class CategoryEnum(str, Enum):
    """POI categories (can be extended)."""
    BEACH = "beach"
    NATURE = "nature"
    NATURAL_FEATURE = "natural_feature"
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    ADVENTURE = "adventure"
    FOOD = "food"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    RELIGIOUS = "religious"
    MUSEUM = "museum"
    LANDMARK = "landmark"
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    CAFE = "cafe"
    BAR = "bar"
    NIGHTLIFE = "nightlife"
    SPORTS = "sports"
    WELLNESS = "wellness"
    FAMILY = "family"
    OTHER = "other"


class TimeSlotEnum(str, Enum):
    """Best time to visit."""
    EARLY_MORNING = "early_morning"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    ANYTIME = "anytime"


class SeasonEnum(str, Enum):
    """Best season to visit."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    YEAR_ROUND = "year_round"


class DataProviderEnum(str, Enum):
    """POI data source providers."""
    GOOGLE_PLACES = "google_places"
    TRIPADVISOR = "tripadvisor"
    FOURSQUARE = "foursquare"
    YELP = "yelp"
    MANUAL = "manual"
    SCRAPED = "scraped"
    USER_SUBMITTED = "user_submitted"
    OTHER = "other"


# Sub-models
class GeoJSONLocation(BaseModel):
    """GeoJSON Point for MongoDB 2dsphere index."""
    type: str = Field(default="Point", description="GeoJSON type")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        """Validate coordinates format."""
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        
        lng, lat = v
        if not (-180 <= lng <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lng}")
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        
        return v


class Address(BaseModel):
    """POI address information."""
    street: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = Field(..., description="Country name (required)")
    postal_code: Optional[str] = None
    full_address: Optional[str] = None


class NameAlternative(BaseModel):
    """Alternative names in different languages."""
    language: str = Field(..., description="Language code (e.g., 'en', 'vi')")
    name: str = Field(..., description="Name in specified language")


class RatingBreakdown(BaseModel):
    """Detailed rating breakdown by star count."""
    five_star: int = Field(default=0, ge=0)
    four_star: int = Field(default=0, ge=0)
    three_star: int = Field(default=0, ge=0)
    two_star: int = Field(default=0, ge=0)
    one_star: int = Field(default=0, ge=0)


class Ratings(BaseModel):
    """POI ratings and reviews."""
    average: float = Field(..., ge=0, le=5, description="Average rating (0-5)")
    count: int = Field(default=0, ge=0, description="Total number of ratings")
    breakdown: Optional[RatingBreakdown] = None


class EntranceFee(BaseModel):
    """Entrance fee information."""
    adult: float = Field(default=0, ge=0, description="Adult entrance fee")
    child: float = Field(default=0, ge=0, description="Child entrance fee")
    currency: str = Field(default="VND", description="Currency code")


class Pricing(BaseModel):
    """POI pricing information."""
    level: PriceLevelEnum = Field(..., description="Price level category")
    entrance_fee: Optional[EntranceFee] = None
    average_cost_per_person: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="VND", description="Currency code")


class OpeningHours(BaseModel):
    """POI opening hours - full details from Google Places."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    is_24_hours: bool = Field(default=False)
    open_now: Optional[bool] = None
    weekday_descriptions: List[str] = Field(default_factory=list, description="Human-readable weekday hours")
    periods: List[Dict[str, Any]] = Field(default_factory=list, description="Structured opening periods")
    secondary_hours: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Secondary hours (delivery, etc)")
    notes: Optional[str] = None


class Contact(BaseModel):
    """Contact information."""
    phone: Optional[str] = None
    international_phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    google_maps_uri: Optional[str] = None


class POIImage(BaseModel):
    """POI image information."""
    url: str = Field(..., description="Image URL (Firebase Storage or reference)")
    photo_reference: Optional[str] = Field(None, description="Google Places photo reference")
    caption: Optional[str] = None
    is_primary: bool = Field(default=False)
    width: Optional[int] = None
    height: Optional[int] = None
    author_attributions: Optional[List[Dict[str, str]]] = Field(default_factory=list)


class POIReview(BaseModel):
    """Individual review from Google Places."""
    author_name: str = Field(default="Anonymous")
    author_photo_url: Optional[str] = None
    author_uri: Optional[str] = None
    rating: float = Field(default=0, ge=0, le=5)
    text: Optional[str] = None
    language: Optional[str] = None
    publish_time: Optional[str] = None
    relative_publish_time: Optional[str] = None


class Description(BaseModel):
    """POI description in multiple formats."""
    short: str = Field(..., max_length=200, description="Short description (200 chars max)")
    long: Optional[str] = Field(None, max_length=2000, description="Long description (2000 chars max)")


class BestTimeToVisit(BaseModel):
    """Best time to visit information."""
    season: List[SeasonEnum] = Field(default_factory=list)
    time_of_day: Optional[TimeSlotEnum] = None
    duration_minutes: Optional[int] = Field(None, ge=0, description="Recommended visit duration")


class DataSource(BaseModel):
    """Information about data source."""
    provider: DataProviderEnum = Field(..., description="Data provider")
    external_id: Optional[str] = Field(None, description="ID in external system")
    confidence: float = Field(default=1.0, ge=0, le=1, description="Data confidence score (0-1)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class Embeddings(BaseModel):
    """POI embeddings for semantic search."""
    model: str = Field(..., description="Embedding model name")
    vector: List[float] = Field(..., description="Embedding vector (384 dims)")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('vector')
    @classmethod
    def validate_vector_dimension(cls, v):
        """Validate embedding vector dimension."""
        if len(v) != 384:
            raise ValueError(f"Embedding vector must have 384 dimensions, got {len(v)}")
        return v


class POIMetadata(BaseModel):
    """POI metadata."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = Field(default=False, description="Admin verified")
    popularity_score: float = Field(default=0, ge=0, le=100, description="Popularity score (0-100)")
    view_count: int = Field(default=0, ge=0)
    booking_count: int = Field(default=0, ge=0)
    last_synced_at: Optional[datetime] = None


# =========================================================================
# GOOGLE PLACES EXTENDED DATA MODELS
# Captures ALL data from Google Places API for rich AI context
# =========================================================================

class GooglePlaceProvider(BaseModel):
    """Google Places provider information."""
    name: str = Field(default="google_places")
    place_id: str = Field(..., description="Google Place ID")
    google_maps_uri: Optional[str] = None


class DiningOptions(BaseModel):
    """Restaurant/cafe dining options from Google Places."""
    serves_breakfast: Optional[bool] = None
    serves_brunch: Optional[bool] = None
    serves_lunch: Optional[bool] = None
    serves_dinner: Optional[bool] = None
    serves_dessert: Optional[bool] = None
    serves_coffee: Optional[bool] = None
    serves_beer: Optional[bool] = None
    serves_wine: Optional[bool] = None
    serves_cocktails: Optional[bool] = None
    serves_vegetarian_food: Optional[bool] = None


class ServiceOptions(BaseModel):
    """Service options from Google Places."""
    dine_in: Optional[bool] = None
    takeout: Optional[bool] = None
    delivery: Optional[bool] = None
    curbside_pickup: Optional[bool] = None
    reservable: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    live_music: Optional[bool] = None
    menu_for_children: Optional[bool] = None
    serves_cocktails: Optional[bool] = None
    serves_dessert: Optional[bool] = None
    serves_coffee: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None
    good_for_watching_sports: Optional[bool] = None
    allows_dogs: Optional[bool] = None
    restroom: Optional[bool] = None


class PaymentOptions(BaseModel):
    """Payment options from Google Places."""
    accepts_credit_cards: Optional[bool] = None
    accepts_debit_cards: Optional[bool] = None
    accepts_cash_only: Optional[bool] = None
    accepts_nfc: Optional[bool] = None


class ParkingOptions(BaseModel):
    """Parking options from Google Places."""
    free_parking_lot: Optional[bool] = None
    paid_parking_lot: Optional[bool] = None
    free_street_parking: Optional[bool] = None
    paid_street_parking: Optional[bool] = None
    valet_parking: Optional[bool] = None
    free_garage_parking: Optional[bool] = None
    paid_garage_parking: Optional[bool] = None


class AccessibilityOptions(BaseModel):
    """Accessibility options from Google Places."""
    wheelchair_accessible_parking: Optional[bool] = None
    wheelchair_accessible_entrance: Optional[bool] = None
    wheelchair_accessible_restroom: Optional[bool] = None
    wheelchair_accessible_seating: Optional[bool] = None


class FuelOptions(BaseModel):
    """Fuel options for gas stations."""
    fuel_prices: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class EVChargeOptions(BaseModel):
    """EV charging options."""
    connector_count: Optional[int] = None
    connector_aggregation: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class AddressComponent(BaseModel):
    """Detailed address component from Google."""
    long_name: str
    short_name: str
    types: List[str] = Field(default_factory=list)


class Viewport(BaseModel):
    """Map viewport bounds."""
    northeast: Dict[str, float] = Field(default_factory=dict)
    southwest: Dict[str, float] = Field(default_factory=dict)


class GooglePlacesExtendedData(BaseModel):
    """
    Extended data from Google Places API.
    Contains ALL useful data for AI itinerary generation.
    """
    # === Core Google Data ===
    google_place_id: str = Field(..., description="Google Place ID")
    google_maps_uri: Optional[str] = None
    
    # === Type Information ===
    google_types: List[str] = Field(default_factory=list, description="Original Google place types")
    primary_type: Optional[str] = None
    primary_type_display_name: Optional[str] = None
    
    # === Business Info ===
    business_status: Optional[str] = None
    utc_offset_minutes: Optional[int] = None
    
    # === Viewport for Maps ===
    viewport: Optional[Viewport] = None
    
    # === Address Components ===
    address_components: List[AddressComponent] = Field(default_factory=list)
    adr_format_address: Optional[str] = None
    short_formatted_address: Optional[str] = None
    
    # === Reviews (full data) ===
    reviews: List[POIReview] = Field(default_factory=list, description="User reviews")
    
    # === Editorial ===
    editorial_summary: Optional[str] = None
    
    # === Dining Options ===
    dining_options: Optional[DiningOptions] = None
    
    # === Service Options ===
    service_options: Optional[ServiceOptions] = None
    
    # === Payment Options ===
    payment_options: Optional[PaymentOptions] = None
    
    # === Parking Options ===
    parking_options: Optional[ParkingOptions] = None
    
    # === Accessibility ===
    accessibility_options: Optional[AccessibilityOptions] = None
    
    # === Fuel/EV (for gas stations) ===
    fuel_options: Optional[FuelOptions] = None
    ev_charge_options: Optional[EVChargeOptions] = None
    
    # === Current Opening Hours (real-time) ===
    current_opening_hours: Optional[Dict[str, Any]] = None
    current_secondary_opening_hours: Optional[List[Dict[str, Any]]] = None
    
    # === AI-Relevant Signals ===
    allows_dogs: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None
    good_for_watching_sports: Optional[bool] = None
    
    # === Raw Data (for future-proofing) ===
    raw_google_response: Optional[Dict[str, Any]] = Field(
        None, 
        description="Complete raw Google API response for future data extraction"
    )


# Main POI Model
class POI(BaseModel):
    """
    Complete POI (Point of Interest) model.
    
    Matches MongoDB poi_unified.json schema.
    Used for data validation before insert/update.
    """
    
    # Identifiers
    poi_id: str = Field(..., description="Unique POI identifier (e.g., 'poi_mykhebeach')")
    dedupe_key: str = Field(..., description="Deduplication key (normalized_name + geohash)")
    
    # Basic Information
    name: str = Field(..., min_length=1, max_length=200, description="POI name")
    name_unaccented: str = Field(..., description="Name without accents (for search)")
    name_alternatives: List[NameAlternative] = Field(default_factory=list)
    
    # Location
    location: GeoJSONLocation = Field(..., description="GeoJSON location (2dsphere)")
    address: Address = Field(..., description="Address information")
    
    # Classification
    categories: List[CategoryEnum] = Field(..., min_length=1, description="POI categories")
    
    # Description
    description: Description = Field(..., description="POI description")
    
    # Ratings & Reviews
    ratings: Ratings = Field(..., description="Ratings information")
    
    # Pricing
    pricing: Pricing = Field(..., description="Pricing information")
    
    # Operational Info
    opening_hours: Optional[OpeningHours] = None
    contact: Optional[Contact] = None
    
    # Media
    images: List[POIImage] = Field(default_factory=list)
    
    # Amenities
    amenities: List[str] = Field(default_factory=list, description="Available amenities")
    
    # Visit Information
    best_time_to_visit: Optional[BestTimeToVisit] = None
    
    # AI/ML
    embeddings: Optional[Embeddings] = None
    
    # Data Sources
    sources: List[DataSource] = Field(default_factory=list, description="Data sources")
    
    # Metadata
    metadata: POIMetadata = Field(default_factory=POIMetadata)
    
    # =========================================================================
    # GOOGLE PLACES EXTENDED DATA (NEW)
    # All additional data from Google Places API for rich AI context
    # =========================================================================
    google_data: Optional[GooglePlacesExtendedData] = Field(
        None, 
        description="Extended data from Google Places API"
    )
    
    # Provider reference (for compatibility)
    provider: Optional[GooglePlaceProvider] = Field(None, description="Google Places provider info")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True


# Request/Response Models
class POICreateRequest(BaseModel):
    """Request model for creating new POI."""
    name: str = Field(..., min_length=1, max_length=200)
    name_alternatives: List[NameAlternative] = Field(default_factory=list)
    location: GeoJSONLocation
    address: Address
    categories: List[CategoryEnum] = Field(..., min_length=1)
    description: Description
    pricing: Pricing
    opening_hours: Optional[OpeningHours] = None
    contact: Optional[Contact] = None
    images: List[POIImage] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    best_time_to_visit: Optional[BestTimeToVisit] = None
    sources: List[DataSource] = Field(default_factory=list)


class POIUpdateRequest(BaseModel):
    """Request model for updating existing POI."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    name_alternatives: Optional[List[NameAlternative]] = None
    location: Optional[GeoJSONLocation] = None
    address: Optional[Address] = None
    categories: Optional[List[CategoryEnum]] = None
    description: Optional[Description] = None
    pricing: Optional[Pricing] = None
    opening_hours: Optional[OpeningHours] = None
    contact: Optional[Contact] = None
    images: Optional[List[POIImage]] = None
    amenities: Optional[List[str]] = None
    best_time_to_visit: Optional[BestTimeToVisit] = None


class POISearchRequest(BaseModel):
    """Request model for POI search."""
    q: Optional[str] = Field(None, description="Search query")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    radius: Optional[float] = Field(None, gt=0, description="Search radius in km")
    categories: Optional[List[CategoryEnum]] = None
    price_level: Optional[PriceLevelEnum] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class POIResponse(BaseModel):
    """Response model for POI details."""
    poi_id: str
    dedupe_key: str
    name: str
    name_unaccented: str
    name_alternatives: List[NameAlternative]
    location: GeoJSONLocation
    address: Address
    categories: List[CategoryEnum]
    description: Description
    ratings: Ratings
    pricing: Pricing
    opening_hours: Optional[OpeningHours]
    contact: Optional[Contact]
    images: List[POIImage]
    amenities: List[str]
    best_time_to_visit: Optional[BestTimeToVisit]
    metadata: POIMetadata
    distance_km: Optional[float] = Field(None, description="Distance from search location (if geo search)")
