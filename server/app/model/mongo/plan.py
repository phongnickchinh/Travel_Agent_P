"""
Plan Model - MongoDB Pydantic Schema
=====================================

Purpose:
- Define travel plan schema for MongoDB storage
- Validate LLM-generated itineraries
- Support multi-day trip planning with POIs

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timedelta
from enum import Enum


class PlanStatusEnum(str, Enum):
    """Plan status lifecycle."""
    PENDING = "pending"      # Celery task queued
    PROCESSING = "processing"  # LLM generating
    COMPLETED = "completed"   # Success
    FAILED = "failed"        # Error occurred


class Location(BaseModel):
    """Geographic location with coordinates."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class Origin(BaseModel):
    """Trip origin/starting point."""
    location: Optional[Location] = Field(None, description="Coordinates")
    address: Optional[str] = Field(None, max_length=500, description="Full address")
    transport_mode: str = Field(
        default="driving",
        description="Transport mode: driving, walking, transit"
    )
    
    @field_validator('transport_mode')
    @classmethod
    def validate_transport_mode(cls, v):
        valid_modes = ['driving', 'walking', 'transit', 'bicycling']
        if v.lower() not in valid_modes:
            raise ValueError(f"Transport mode must be one of: {valid_modes}")
        return v.lower()


class TripPreferences(BaseModel):
    """
    Structured user preferences for trip planning.
    Used for validation and LLM prompt construction.
    """
    interests: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="User interests: beach, culture, food, nightlife, etc."
    )
    budget: Optional[float] = Field(
        None,
        ge=0,
        description="Budget amount in local currency"
    )
    budget_level: Optional[str] = Field(
        None,
        description="Budget level: low, medium, high, luxury"
    )
    pace: str = Field(
        default="moderate",
        description="Travel pace: relaxed, moderate, intensive"
    )
    dietary: Optional[str] = Field(None, description="Dietary restrictions")
    accessibility: Optional[str] = Field(None, description="Accessibility requirements")
    
    @field_validator('pace')
    @classmethod
    def validate_pace(cls, v):
        valid_paces = ['relaxed', 'moderate', 'intensive']
        if v.lower() not in valid_paces:
            return 'moderate'
        return v.lower()
    
    @field_validator('budget_level')
    @classmethod
    def validate_budget_level(cls, v):
        if v is None:
            return None
        valid_levels = ['low', 'medium', 'high', 'luxury']
        if v.lower() not in valid_levels:
            return 'medium'
        return v.lower()


class DayPlan(BaseModel):
    """Single day itinerary."""
    day: int = Field(..., ge=1, description="Day number (1-based)")
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    poi_ids: List[str] = Field(default_factory=list, description="POI IDs in visit order")
    types: Optional[List[List[str]]] = Field(
        default_factory=list,
        description="POI types array (one array per POI). e.g., [['beach', 'nature'], ['restaurant']]"
    )
    activities: List[str] = Field(default_factory=list, description="LLM-generated activities")
    notes: Optional[str] = Field(None, description="Daily notes or tips")
    
    # Time and cost fields from LLM
    opening_hours: Optional[List[str]] = Field(
        default_factory=list, 
        description="Opening hours for each POI in format HH:MM-HH:MM"
    )
    estimated_times: Optional[List[str]] = Field(
        default_factory=list, 
        description="Estimated visit times for each POI in format HH:MM-HH:MM"
    )
    estimated_cost_vnd: Optional[int] = Field(
        None, ge=0, description="Estimated daily cost in VND"
    )
    estimated_travel_time_min: Optional[int] = Field(
        None, ge=0, description="Estimated travel time in minutes"
    )
    estimated_cost: Optional[float] = Field(
        None, ge=0, description="Estimated cost for the day (legacy)"
    )
    
    # Map display fields - featured_images array (one per POI)
    featured_images: Optional[List[str]] = Field(
        default_factory=list, 
        description="Featured image URLs, one per POI in visit order"
    )
    viewport: Optional[Dict[str, Dict[str, float]]] = Field(
        None, 
        description="Map viewport bounds {'northeast': {'lat': float, 'lng': float}, 'southwest': {...}}"
    )
    location: Optional[List[float]] = Field(
        None,
        description="Central point [latitude, longitude] for the day's activities"
    )
    
    # Accommodation fields
    accommodation_id: Optional[str] = Field(
        None,
        description="POI ID of the accommodation (hotel/hostel/resort)"
    )
    accommodation_name: Optional[str] = Field(
        None,
        description="Name of the accommodation"
    )
    accommodation_address: Optional[str] = Field(
        None,
        description="Address of the accommodation"
    )
    accommodation_location: Optional[List[float]] = Field(
        None,
        description="Accommodation coordinates [latitude, longitude]"
    )
    check_in_time: Optional[str] = Field(
        None,
        description="Check-in time in format HH:MM"
    )
    check_out_time: Optional[str] = Field(
        None,
        description="Check-out time in format HH:MM (usually on day of departure)"
    )
    accommodation_changed: Optional[bool] = Field(
        False,
        description="True if accommodation changed from previous day"
    )
    accommodation_change_reason: Optional[str] = Field(
        None,
        description="Reason for accommodation change (e.g., 'closer to next cluster')"
    )
    
    @field_validator('poi_ids')
    @classmethod
    def validate_poi_ids(cls, v):
        """Ensure at least 1 POI per day."""
        if not v or len(v) == 0:
            raise ValueError("Each day must have at least 1 POI")
        return v


class Plan(BaseModel):
    """
    Travel plan model for MongoDB.
    
    Structure:
    - plan_id: Unique identifier (auto-generated)
    - user_id: Owner of the plan
    - destination: City/region (e.g., "Da Nang")
    - num_days: Total trip duration
    - preferences: User input (keywords, interests)
    - itinerary: List of DayPlan
    - status: PENDING → PROCESSING → COMPLETED/FAILED
    - llm_model: HuggingFace model used
    - metadata: Additional context (cost, tokens, etc.)
    - created_at, updated_at: Timestamps
    
    Example:
        plan = Plan(
            user_id="user123",
            destination="Da Nang",
            num_days=3,
            preferences={"interests": ["beach", "culture"], "budget": "medium"}
        )
    """
    
    plan_id: Optional[str] = Field(None, description="Auto-generated unique ID")
    user_id: str = Field(..., description="User ID from auth system")
    
    # Plan identification
    title: Optional[str] = Field(
        None, max_length=200, description="User-defined plan title"
    )
    
    # Thumbnail for dashboard display
    thumbnail_url: Optional[str] = Field(
        None, 
        description="Thumbnail image URL (from destination photo, uploaded to Firebase)"
    )
    
    # Trip destination (NEW: place_id based)
    destination_place_id: Optional[str] = Field(None, description="Google Place ID for destination")
    destination: str = Field(..., min_length=2, max_length=100, description="City or region name")
    destination_types: List[str] = Field(
        default_factory=list, 
        description="Place types (e.g., ['locality', 'political'])"
    )
    destination_location: Optional[Dict[str, float]] = Field(
        None, 
        description="Destination coordinates {'latitude': float, 'longitude': float}"
    )
    
    # Trip parameters
    num_days: int = Field(..., ge=1, le=30, description="Trip duration (1-30 days)")
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Trip end date (auto-calculated)")
    
    # Origin/starting point
    origin: Optional[Origin] = Field(None, description="Trip starting point")
    
    # User preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User input: interests, budget, pace, etc."
    )
    
    # Generated itinerary
    itinerary: List[DayPlan] = Field(
        default_factory=list,
        description="Day-by-day plan with POIs"
    )
    
    # Status tracking
    status: PlanStatusEnum = Field(
        default=PlanStatusEnum.PENDING,
        description="Plan generation status"
    )
    
    # Sharing & visibility
    is_public: bool = Field(default=False, description="Allow public sharing")
    share_token: Optional[str] = Field(None, description="Token for shared link access")
    
    # Soft delete (trash functionality)
    is_deleted: bool = Field(default=False, description="Soft delete flag (moved to trash)")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp when moved to trash")
    is_permanently_deleted: bool = Field(default=False, description="Permanent delete flag (cannot be restored)")
    
    # Versioning for regeneration
    version: int = Field(default=1, description="Plan version (increments on regenerate)")
    
    # Cost estimation
    estimated_total_cost: Optional[float] = Field(
        None, ge=0, description="Total estimated trip cost"
    )
    
    # LLM metadata
    llm_model: Optional[str] = Field(None, description="HuggingFace model name")
    llm_response_raw: Optional[str] = Field(None, description="Raw LLM output (for debugging)")
    error_message: Optional[str] = Field(None, description="Error details if FAILED")
    
    # Metadata
    total_pois: int = Field(default=0, description="Total POI count across all days")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional data (cost, tokens, provider, etc.)"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @model_validator(mode='after')
    def calculate_end_date(self):
        """Auto-calculate end_date from start_date and num_days."""
        if self.start_date and not self.end_date:
            try:
                start = datetime.strptime(self.start_date, '%Y-%m-%d')
                end = start + timedelta(days=self.num_days - 1)
                self.end_date = end.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return self
    
    @field_validator('itinerary')
    @classmethod
    def validate_itinerary(cls, v, info):
        """Ensure itinerary matches num_days."""
        # Only validate if plan is COMPLETED
        if info.data.get('status') == PlanStatusEnum.COMPLETED:
            num_days = info.data.get('num_days')
            if num_days and len(v) != num_days:
                raise ValueError(f"Itinerary must have exactly {num_days} days, got {len(v)}")
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "plan_id": "plan_abc123",
                "user_id": "user456",
                "destination": "Da Nang",
                "num_days": 3,
                "start_date": "2025-06-01",
                "preferences": {
                    "interests": ["beach", "culture", "food"],
                    "budget": "medium",
                    "pace": "relaxed"
                },
                "itinerary": [
                    {
                        "day": 1,
                        "date": "2025-06-01",
                        "poi_ids": ["poi_my_khe_beach", "poi_linh_ung_pagoda"],
                        "activities": ["Morning swim", "Afternoon temple visit"],
                        "notes": "Start with beach relaxation"
                    }
                ],
                "status": "completed",
                "llm_model": "meta-llama/Llama-3.2-3B-Instruct",
                "total_pois": 6,
                "metadata": {
                    "cost_usd": 0.05,
                    "tokens_used": 1200,
                    "generation_time_sec": 15.3
                }
            }
        }


class PlanCreateRequest(BaseModel):
    """Request payload for creating a plan."""
    title: Optional[str] = Field(None, max_length=200, description="Plan title")
    
    # NEW: Destination via place_id (from autocomplete selection)
    destination_place_id: str = Field(..., description="Google Place ID from autocomplete")
    destination_name: str = Field(..., min_length=2, max_length=100, description="Display name for destination")
    destination_types: List[str] = Field(
        default_factory=list, 
        description="Place types from autocomplete (e.g., ['locality', 'political'])"
    )
    
    # Legacy field for backward compatibility (optional now)
    destination: Optional[str] = Field(None, description="DEPRECATED: Use destination_name")
    
    num_days: int = Field(..., ge=1, le=30)
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    origin: Optional[Origin] = Field(None, description="Starting point")
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def sync_destination_fields(self):
        """Sync destination with destination_name for backward compatibility."""
        if not self.destination and self.destination_name:
            self.destination = self.destination_name
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Da Nang Beach Vacation",
                "destination_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "destination_name": "Da Nang",
                "destination_types": ["locality", "political"],
                "num_days": 3,
                "start_date": "2025-06-01",
                "origin": {
                    "location": {"lat": 16.0678, "lng": 108.2208},
                    "address": "173 Hoang Hoa Tham, Da Nang",
                    "transport_mode": "driving"
                },
                "preferences": {
                    "interests": ["beach", "culture"],
                    "budget": 5000000,
                    "pace": "relaxed"
                }
            }
        }


class PlanUpdateRequest(BaseModel):
    """Request payload for updating a plan (e.g., regenerate)."""
    title: Optional[str] = Field(None, max_length=200)
    preferences: Optional[Dict[str, Any]] = None
    start_date: Optional[str] = None
    origin: Optional[Origin] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Beach Trip",
                "preferences": {
                    "interests": ["adventure", "nightlife"],
                    "budget": 8000000
                }
            }
        }


# ============================================
# PATCH Request Models (Non-Core Updates)
# ============================================

class DayPlanPatch(BaseModel):
    """
    Partial update for a single day in itinerary.
    Only non-core fields that don't require AI regeneration.
    """
    day: int = Field(..., ge=1, description="Day number to update (1-based)")
    
    # User-editable text fields
    notes: Optional[str] = Field(None, max_length=2000, description="Daily notes or tips")
    activities: Optional[List[str]] = Field(None, description="Activity descriptions (user can edit text)")
    
    # Time and cost adjustments
    estimated_times: Optional[List[str]] = Field(
        None, 
        description="Visit times in format HH:MM-HH:MM (must match activities count)"
    )
    estimated_cost_vnd: Optional[int] = Field(None, ge=0, description="Daily cost estimate in VND")
    
    # Accommodation fields
    accommodation_name: Optional[str] = Field(None, max_length=200)
    accommodation_address: Optional[str] = Field(None, max_length=500)
    check_in_time: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$', description="Format: HH:MM")
    check_out_time: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$', description="Format: HH:MM")
    
    class Config:
        extra = "forbid"  # Reject unknown fields


class PlanPatchRequest(BaseModel):
    """
    Request payload for partial plan updates (non-regenerating).
    
    Use cases:
    - Change plan title
    - Update start_date (auto-recalculates end_date)
    - Edit daily notes/activities text
    - Adjust accommodation details
    - Update estimated costs
    
    Does NOT trigger AI regeneration.
    """
    
    # Plan-level editable fields
    title: Optional[str] = Field(None, max_length=200, description="User-defined plan title")
    thumbnail_url: Optional[str] = Field(None, description="Custom thumbnail URL")
    start_date: Optional[str] = Field(
        None, 
        pattern=r'^\d{4}-\d{2}-\d{2}$', 
        description="Trip start date (YYYY-MM-DD)"
    )
    estimated_total_cost: Optional[float] = Field(None, ge=0, description="User-adjusted total cost")
    
    # Nested itinerary updates (by day index)
    itinerary_updates: Optional[List[DayPlanPatch]] = Field(
        None, 
        description="Partial updates for specific days"
    )
    
    class Config:
        extra = "forbid"  # Reject unknown fields
        json_schema_extra = {
            "example": {
                "title": "Chuyến đi Đà Nẵng 2026",
                "start_date": "2026-02-01",
                "itinerary_updates": [
                    {
                        "day": 1, 
                        "notes": "Nhớ mang kem chống nắng",
                        "accommodation_name": "Khách sạn ABC"
                    },
                    {
                        "day": 2, 
                        "activities": ["Tập yoga buổi sáng", "Tham quan Bà Nà Hills"]
                    }
                ]
            }
        }
