"""
Autocomplete Cache Data Models
==============================

Purpose:
- Pydantic models for autocomplete cache data validation
- Based on Google Places API Autocomplete response structure
- Used for both MongoDB storage and ES indexing

Author: Travel Agent P Team
Date: December 22, 2025

Google Places API Autocomplete Response Example:
{
    "description": "Paris, France",
    "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
    "structured_formatting": {
        "main_text": "Paris",
        "secondary_text": "France"
    },
    "terms": [{"offset": 0, "value": "Paris"}, {"offset": 7, "value": "France"}],
    "types": ["locality", "political", "geocode"]
}
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import unicodedata


class CacheStatus(str, Enum):
    """
    Status of cached autocomplete item.
    
    - PENDING: Basic info only (from autocomplete), needs Place Details on click
    - CACHED: Full details available in POI collection
    """
    CACHED = "cached"
    PENDING = "pending"


class AutocompleteItem(BaseModel):
    """
    Autocomplete cache item based on Google Places API Autocomplete response.
    
    This model is optimized for:
    1. Fast autocomplete search (edge n-gram on main_text)
    2. Display (description, main_text, secondary_text)
    3. Filtering (types, terms for location hierarchy)
    4. Enrichment (status tracks if full details fetched)
    
    Example Google response:
    {
        "description": "Paris, France",
        "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
        "structured_formatting": {
            "main_text": "Paris",
            "secondary_text": "France"
        },
        "terms": [{"value": "Paris"}, {"value": "France"}],
        "types": ["locality", "political", "geocode"]
    }
    """
    
    # === Core Identity ===
    place_id: str = Field(..., description="Google Place ID (unique identifier)")
    
    # === Display Fields (from structured_formatting) ===
    description: str = Field(..., description="Full display text, e.g. 'Paris, France'")
    main_text: str = Field(..., description="Primary name, e.g. 'Paris'")
    main_text_unaccented: Optional[str] = Field(None, description="Lowercase unaccented for search")
    secondary_text: Optional[str] = Field(None, description="Context/region, e.g. 'France' or 'TX, USA'")
    
    # === Hierarchical Terms ===
    terms: List[str] = Field(
        default_factory=list, 
        description="Location hierarchy extracted from terms array, e.g. ['Paris', 'TX', 'USA']"
    )
    
    # === Place Types ===
    types: List[str] = Field(
        default_factory=list, 
        description="Place types from Google, e.g. ['locality', 'political', 'geocode', 'neighborhood']"
    )
    
    # === Geo Location (enriched later from Place Details) ===
    lat: Optional[float] = Field(None, description="Latitude (populated after resolve)")
    lng: Optional[float] = Field(None, description="Longitude (populated after resolve)")
    
    # === Cache Metadata ===
    status: CacheStatus = Field(
        default=CacheStatus.PENDING,
        description="pending = basic info only, cached = full details in POI collection"
    )
    click_count: int = Field(default=0, description="Popularity metric, incremented on user click")
    
    # === Timestamps ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('main_text_unaccented', mode='before')
    @classmethod
    def auto_generate_unaccented(cls, v, info):
        """Auto-generate unaccented version if not provided."""
        if v is not None:
            return v
        # Will be set in from_google_prediction or model_post_init
        return None
    
    def model_post_init(self, __context: Any) -> None:
        """Post-init: auto-generate main_text_unaccented if not set."""
        if self.main_text_unaccented is None and self.main_text:
            object.__setattr__(self, 'main_text_unaccented', self._to_unaccented(self.main_text))
    
    @classmethod
    def from_google_prediction(cls, prediction: Dict[str, Any]) -> "AutocompleteItem":
        """
        Create AutocompleteItem from Google Places API Autocomplete prediction.
        
        Args:
            prediction: Single prediction object from Google API response['predictions']
            
        Returns:
            AutocompleteItem instance with mapped fields
            
        Example prediction:
            {
                "description": "Paris, France",
                "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                "structured_formatting": {
                    "main_text": "Paris",
                    "main_text_matched_substrings": [{"length": 5, "offset": 0}],
                    "secondary_text": "France"
                },
                "terms": [
                    {"offset": 0, "value": "Paris"},
                    {"offset": 7, "value": "France"}
                ],
                "types": ["locality", "political", "geocode"]
            }
        """
        structured = prediction.get("structured_formatting", {})
        main_text = structured.get("main_text", prediction.get("description", "").split(",")[0])
        
        # Extract term values from terms array
        terms = [t.get("value") for t in prediction.get("terms", []) if t.get("value")]
        
        return cls(
            place_id=prediction["place_id"],
            description=prediction.get("description", main_text),
            main_text=main_text,
            main_text_unaccented=cls._to_unaccented(main_text),
            secondary_text=structured.get("secondary_text"),
            terms=terms,
            types=prediction.get("types", []),
            status=CacheStatus.PENDING,
            click_count=0,
        )
    
    @staticmethod
    def _to_unaccented(text: str) -> str:
        """
        Convert text to lowercase unaccented for search.
        
        Handles Vietnamese special characters including đ/Đ.
        
        Examples:
            "Bãi biển Mỹ Khê" -> "bai bien my khe"
            "Đà Nẵng" -> "da nang"
            "Paris" -> "paris"
            "Café" -> "cafe"
        """
        if not text:
            return ""
        
        # Handle Vietnamese đ/Đ specifically (not a combining character)
        text = text.replace('đ', 'd').replace('Đ', 'D')
        
        # Normalize to NFD (decomposed form), remove combining characters, lowercase
        nfkd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()
    
    def to_es_document(self) -> Dict[str, Any]:
        """
        Convert to Elasticsearch document format.
        
        Returns:
            Dict ready for ES indexing
        """
        doc = {
            "place_id": self.place_id,
            "description": self.description,
            "main_text": self.main_text,
            "main_text_unaccented": self.main_text_unaccented,
            "secondary_text": self.secondary_text,
            "terms": self.terms,
            "types": self.types,
            "status": self.status.value,
            "click_count": self.click_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        # Add geo_point if location available
        if self.lat is not None and self.lng is not None:
            doc["location"] = {"lat": self.lat, "lon": self.lng}
        
        return doc
    
    def to_mongo_document(self) -> Dict[str, Any]:
        """
        Convert to MongoDB document format.
        
        Returns:
            Dict ready for MongoDB insertion
        """
        return self.model_dump(mode='json', exclude_none=False)
    
    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format for frontend.
        
        Returns:
            Simplified dict for autocomplete dropdown display
        """
        return {
            "place_id": self.place_id,
            "description": self.description,
            "main_text": self.main_text,
            "secondary_text": self.secondary_text,
            "types": self.types,
            "status": self.status.value,
            "has_details": self.status == CacheStatus.CACHED,
            # Include location if available
            "lat": self.lat,
            "lng": self.lng,
        }


class AutocompleteSearchRequest(BaseModel):
    """
    Request model for autocomplete search endpoint.
    """
    query: str = Field(..., min_length=1, max_length=200, description="Search query string")
    limit: int = Field(default=10, ge=1, le=20, description="Max results to return")
    types: Optional[List[str]] = Field(None, description="Filter by place types, e.g. ['locality']")
    
    # Optional user location for geo-boosting
    lat: Optional[float] = Field(None, ge=-90, le=90, description="User latitude for proximity boost")
    lng: Optional[float] = Field(None, ge=-180, le=180, description="User longitude for proximity boost")
    
    # Session token for Google API billing optimization
    session_token: Optional[str] = Field(None, description="Session token for Google API request grouping")


class AutocompleteSearchResponse(BaseModel):
    """
    Response model for autocomplete search endpoint.
    """
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = Field(..., description="Data source: 'cache', 'google', 'mixed'")
    cache_hit_count: int = Field(default=0)
    google_fetch_count: int = Field(default=0)
    total_count: int = Field(default=0)


class ResolveRequest(BaseModel):
    """
    Request model for resolving place details on user click.
    """
    place_id: str = Field(..., description="Google Place ID to resolve")
    session_token: Optional[str] = Field(None, description="Session token from autocomplete")


class ResolveResponse(BaseModel):
    """
    Response model for resolved place details.
    """
    place_id: str
    name: str
    description: str
    lat: float
    lng: float
    types: List[str]
    address: Optional[str] = None
    rating: Optional[float] = None
    total_reviews: Optional[int] = None
    photos: Optional[List[str]] = None
    opening_hours: Optional[Dict[str, Any]] = None
    # Full POI data if available
    poi_id: Optional[str] = None
    has_full_details: bool = False
