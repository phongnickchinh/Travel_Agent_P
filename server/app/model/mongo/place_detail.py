"""
Place Detail Model - MongoDB Pydantic Schema
=============================================

Purpose:
- Store full place details from Google Places API
- Separate from autocomplete_cache (which is for search predictions)
- Used as destination detail for trip planning

Author: Travel Agent P Team
Date: December 24, 2025

Note: This is separate from POI collection.
- POI collection: tourist attractions, restaurants, etc. for itinerary
- PlaceDetail collection: destination details (cities, regions) for trip planning
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PlaceLocation(BaseModel):
    """Geographic location with coordinates."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class PlaceViewport(BaseModel):
    """Viewport bounds for map display."""
    northeast: PlaceLocation
    southwest: PlaceLocation


class PlaceGeometry(BaseModel):
    """Place geometry data from Google Places API."""
    location: PlaceLocation
    viewport: Optional[PlaceViewport] = None


class AddressComponent(BaseModel):
    """Address component from Google Places API."""
    long_name: str
    short_name: str
    types: List[str] = Field(default_factory=list)


class PlaceDetail(BaseModel):
    """
    Full place detail from Google Places API.
    
    Used as destination for trip planning.
    Cached in MongoDB to avoid repeated API calls.
    
    Example:
        {
            "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
            "name": "Paris",
            "formatted_address": "Paris, France",
            "geometry": {
                "location": {"latitude": 48.8566, "longitude": 2.3522}
            },
            "types": ["locality", "political"],
            ...
        }
    """
    
    # === Core Identity ===
    place_id: str = Field(..., description="Google Place ID (unique identifier)")
    
    # === Display Fields ===
    name: str = Field(..., description="Place name (e.g., 'Paris')")
    formatted_address: Optional[str] = Field(None, description="Full address string")
    
    # === Location Data ===
    geometry: PlaceGeometry = Field(..., description="Location and viewport")
    
    # === Place Classification ===
    types: List[str] = Field(default_factory=list, description="Place types from Google")
    
    # === Address Components ===
    address_components: List[AddressComponent] = Field(
        default_factory=list, 
        description="Structured address components"
    )
    
    # === Additional Details ===
    utc_offset_minutes: Optional[int] = Field(None, description="UTC offset in minutes")
    url: Optional[str] = Field(None, description="Google Maps URL")
    website: Optional[str] = Field(None, description="Official website")
    
    # === Photos ===
    photo_references: List[str] = Field(
        default_factory=list,
        description="Photo references for Google Places Photos API"
    )
    
    # === Raw Data (for debugging) ===
    raw_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Raw Google API response (for debugging)"
    )
    
    # === Cache Metadata ===
    source: str = Field(default="google", description="Data source (google, manual)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, description="Number of times accessed")
    
    # === Helpers ===
    @property
    def location(self) -> Dict[str, float]:
        """Get location as dict for compatibility."""
        return {
            "latitude": self.geometry.location.latitude,
            "longitude": self.geometry.location.longitude
        }
    
    @property
    def lat(self) -> float:
        """Get latitude."""
        return self.geometry.location.latitude
    
    @property
    def lng(self) -> float:
        """Get longitude."""
        return self.geometry.location.longitude
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to MongoDB-safe dict with GeoJSON location format.
        
        Returns location in GeoJSON format for consistency:
        {"type": "Point", "coordinates": [longitude, latitude]}
        """
        data = self.model_dump()
        
        # Convert geometry to GeoJSON format for consistency
        data['location'] = {
            'type': 'Point',
            'coordinates': [
                self.geometry.location.longitude,
                self.geometry.location.latitude
            ]
        }
        
        # Ensure datetime is properly serialized
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data
    
    @classmethod
    def from_google_response(cls, place_data: Dict[str, Any]) -> "PlaceDetail":
        """
        Create PlaceDetail from Google Places API response.
        
        Args:
            place_data: Google Places API response dict
            
        Returns:
            PlaceDetail instance
        """
        # Handle both raw Google API response AND transformed POI format
        # Check if this is already transformed (has 'provider' key)
        is_transformed = 'provider' in place_data
        
        # Get raw_data for original Google response fields
        raw_data = place_data.get('raw_data', {}) if is_transformed else place_data
        
        # === Extract place_id ===
        if is_transformed:
            place_id = place_data.get('provider', {}).get('id', '')
        else:
            place_id = place_data.get('id') or place_data.get('place_id', '')
        
        # === Extract name ===
        if is_transformed:
            name = place_data.get('name', '')
        else:
            display_name = place_data.get('displayName', {})
            name = display_name.get('text') if isinstance(display_name, dict) else place_data.get('name', '')
        
        # === Extract formatted address ===
        if is_transformed:
            formatted_address = place_data.get('address', {}).get('full_address')
        else:
            formatted_address = place_data.get('formattedAddress') or place_data.get('formatted_address')
        
        # === Extract location ===
        # Transformed format: {"type": "Point", "coordinates": [lng, lat]}
        # Raw format: {"latitude": lat, "longitude": lng}
        location_data = place_data.get('location', {})
        
        if location_data.get('type') == 'Point' and 'coordinates' in location_data:
            # GeoJSON format [lng, lat]
            coords = location_data.get('coordinates', [0, 0])
            lng = coords[0] if len(coords) > 0 else 0
            lat = coords[1] if len(coords) > 1 else 0
        elif 'latitude' in location_data:
            # Direct lat/lng format
            lat = location_data.get('latitude', 0)
            lng = location_data.get('longitude', 0)
        else:
            # Try raw_data location
            raw_location = raw_data.get('location', {})
            lat = raw_location.get('latitude', 0)
            lng = raw_location.get('longitude', 0)
        
        # === Extract viewport ===
        viewport_data = raw_data.get('viewport') or place_data.get('viewport')
        viewport = None
        if viewport_data:
            try:
                # Handle different viewport formats
                ne = viewport_data.get('northeast', viewport_data.get('high', {}))
                sw = viewport_data.get('southwest', viewport_data.get('low', {}))
                
                viewport = PlaceViewport(
                    northeast=PlaceLocation(
                        latitude=ne.get('latitude', 0),
                        longitude=ne.get('longitude', 0)
                    ),
                    southwest=PlaceLocation(
                        latitude=sw.get('latitude', 0),
                        longitude=sw.get('longitude', 0)
                    )
                )
            except (KeyError, TypeError):
                pass
        
        geometry = PlaceGeometry(
            location=PlaceLocation(latitude=lat, longitude=lng),
            viewport=viewport
        )
        
        # === Extract types ===
        types = raw_data.get('types', []) or place_data.get('types', []) or place_data.get('categories', [])
        
        # === Extract address components ===
        address_components = []
        raw_components = raw_data.get('addressComponents', raw_data.get('address_components', []))
        for comp in raw_components:
            address_components.append(AddressComponent(
                long_name=comp.get('longText') or comp.get('longName') or comp.get('long_name', ''),
                short_name=comp.get('shortText') or comp.get('shortName') or comp.get('short_name', ''),
                types=comp.get('types', [])
            ))
        
        # === Extract photo references ===
        photo_refs = []
        photos = place_data.get('images', []) or raw_data.get('photos', [])
        for photo in photos:
            if isinstance(photo, dict):
                ref = photo.get('name') or photo.get('url') or photo.get('photo_reference')
                if ref:
                    photo_refs.append(ref)
        
        # === Extract URLs ===
        url = place_data.get('google_maps_uri') or raw_data.get('googleMapsUri') or raw_data.get('url')
        website = place_data.get('contact', {}).get('website') or raw_data.get('websiteUri') or raw_data.get('website')
        
        # === Extract UTC offset ===
        utc_offset = raw_data.get('utcOffsetMinutes') or raw_data.get('utc_offset')
        
        return cls(
            place_id=place_id,
            name=name,
            formatted_address=formatted_address,
            geometry=geometry,
            types=types,
            address_components=address_components,
            utc_offset_minutes=utc_offset,
            url=url,
            website=website,
            photo_references=photo_refs,
            raw_data=raw_data if raw_data else place_data,
            source="google"
        )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "Da Nang",
                "formatted_address": "Da Nang, Vietnam",
                "geometry": {
                    "location": {"latitude": 16.0544, "longitude": 108.2022},
                    "viewport": {
                        "northeast": {"latitude": 16.1544, "longitude": 108.3022},
                        "southwest": {"latitude": 15.9544, "longitude": 108.1022}
                    }
                },
                "types": ["locality", "political"],
                "address_components": [
                    {"long_name": "Da Nang", "short_name": "Da Nang", "types": ["locality"]},
                    {"long_name": "Vietnam", "short_name": "VN", "types": ["country"]}
                ],
                "source": "google",
                "access_count": 5
            }
        }
