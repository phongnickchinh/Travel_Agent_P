"""
POI (Point of Interest) Data Models
====================================

Purpose:
- Pydantic models for POI data validation
- Matches MongoDB poi_unified.json schema
- Type-safe data handling with validation

Author: Travel Agent P Team
Date: October 27, 2025
"""

from typing import List, Optional, Dict, Any
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
    """POI opening hours."""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    is_24_hours: bool = Field(default=False)
    notes: Optional[str] = None


class Contact(BaseModel):
    """Contact information."""
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None


class POIImage(BaseModel):
    """POI image information."""
    url: str = Field(..., description="Image URL (Firebase Storage)")
    caption: Optional[str] = None
    is_primary: bool = Field(default=False)
    width: Optional[int] = None
    height: Optional[int] = None


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
