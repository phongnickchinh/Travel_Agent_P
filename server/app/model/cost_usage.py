"""
Cost Usage Model (PostgreSQL)
==============================

Purpose:
- Track API costs, tokens, latency for all external providers
- Monitor spending per provider (Google Places, OpenAI, TripAdvisor, etc.)
- Analyze performance and optimize costs

Table: cost_usage

Author: Travel Agent P Team
Date: October 27, 2025
"""

from sqlalchemy import String, Integer, Numeric, Boolean, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any
from datetime import datetime

from .base_model import BaseModel


class CostUsage(BaseModel):
    """
    Cost usage tracking for external API calls.
    
    Tracks:
    - Provider costs (Google Places, OpenAI, TripAdvisor)
    - Token usage (LLM APIs)
    - Latency (response time)
    - Request metadata (endpoint, status)
    
    Used for:
    - Cost monitoring and alerts
    - Performance analysis
    - Budget optimization
    - Provider comparison
    """
    
    __tablename__ = 'cost_usage'
    
    # Note: id, created_at, updated_at, is_deleted inherited from BaseModel
    
    # Provider Information
    provider: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Provider name: google_places, openai, tripadvisor, huggingface, etc."
    )
    
    service: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific service/API: places_search, text_details, chat_completion, etc."
    )
    
    # Request Information
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="API endpoint called"
    )
    
    method: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="HTTP method: GET, POST, etc."
    )
    
    # Cost Information
    tokens_input: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default='0',
        comment="Input tokens (for LLM APIs)"
    )
    
    tokens_output: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default='0',
        comment="Output tokens (for LLM APIs)"
    )
    
    tokens_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default='0',
        comment="Total tokens (input + output)"
    )
    
    cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=0.0,
        server_default='0.0',
        comment="Cost in USD (calculated from pricing)"
    )
    
    # Performance Metrics
    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Response latency in milliseconds"
    )
    
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP status code"
    )
    
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true',
        comment="Whether request was successful"
    )
    
    # Context Information
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),  # UUID from BaseModel
        nullable=True,
        comment="User who triggered the request"
    )
    
    plan_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Plan ID if request is part of plan generation"
    )
    
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Unique request ID for tracing"
    )
    
    # Extra Metadata (avoid 'metadata' - reserved by SQLAlchemy)
    extra_metadata: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional metadata (request params, response summary, etc.)"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if request failed"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_cost_usage_provider', 'provider'),
        Index('idx_cost_usage_created_at', 'created_at'),
        Index('idx_cost_usage_user_id', 'user_id'),
        Index('idx_cost_usage_plan_id', 'plan_id'),
        Index('idx_cost_usage_provider_created', 'provider', 'created_at'),
        Index('idx_cost_usage_success', 'success'),
    )
    
    def __init__(
        self,
        provider: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
        latency_ms: Optional[int] = None,
        status_code: Optional[int] = None,
        success: bool = True,
        user_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_metadata: Optional[Dict] = None,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """Initialize CostUsage instance."""
        self.provider = provider
        self.service = service
        self.endpoint = endpoint
        self.method = method
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.tokens_total = tokens_input + tokens_output
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.status_code = status_code
        self.success = success
        self.user_id = user_id
        self.plan_id = plan_id
        self.request_id = request_id
        self.extra_metadata = extra_metadata
        self.error_message = error_message
    
    def __repr__(self):
        return (
            f"<CostUsage {self.id}: {self.provider}/{self.service} "
            f"${float(self.cost_usd):.6f} {self.latency_ms}ms>"
        )
    
    def to_display_dict(self):
        """
        Convert to dictionary for JSON serialization.
        Uses as_dict() from BaseModel and adds computed fields.
        """
        data = super().as_dict()
        
        # Add computed fields
        data['tokens'] = {
            'input': self.tokens_input,
            'output': self.tokens_output,
            'total': self.tokens_total
        }
        
        return data


# Pricing constants (USD per unit)
class ProviderPricing:
    """
    Pricing information for external providers.
    
    Update these values based on current provider pricing.
    """
    
    # OpenAI GPT-4
    OPENAI_GPT4_INPUT = 0.00003  # $0.03/1K tokens
    OPENAI_GPT4_OUTPUT = 0.00006  # $0.06/1K tokens
    
    # OpenAI GPT-3.5
    OPENAI_GPT35_INPUT = 0.0000015  # $0.0015/1K tokens
    OPENAI_GPT35_OUTPUT = 0.000002  # $0.002/1K tokens
    
    # HuggingFace Inference API (approximate)
    HUGGINGFACE_INPUT = 0.000001  # $0.001/1K tokens
    HUGGINGFACE_OUTPUT = 0.000001  # $0.001/1K tokens
    
    # Google Places API
    GOOGLE_PLACES_TEXT_SEARCH = 0.032  # $0.032 per request
    GOOGLE_PLACES_NEARBY_SEARCH = 0.032  # $0.032 per request
    GOOGLE_PLACES_DETAILS = 0.017  # $0.017 per request (Basic Data)
    GOOGLE_PLACES_PHOTOS = 0.007  # $0.007 per request
    
    # TripAdvisor API (approximate, varies by plan)
    TRIPADVISOR_LOCATION_SEARCH = 0.01  # $0.01 per request
    TRIPADVISOR_LOCATION_DETAILS = 0.02  # $0.02 per request
    TRIPADVISOR_REVIEWS = 0.015  # $0.015 per request
    
    @classmethod
    def calculate_llm_cost(cls, provider: str, model: str, tokens_input: int, tokens_output: int) -> float:
        """
        Calculate LLM API cost based on token usage.
        
        Args:
            provider: Provider name (openai, huggingface)
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            
        Returns:
            Cost in USD
        """
        if provider == 'openai':
            if 'gpt-4' in model.lower():
                return (
                    (tokens_input / 1000) * cls.OPENAI_GPT4_INPUT +
                    (tokens_output / 1000) * cls.OPENAI_GPT4_OUTPUT
                )
            elif 'gpt-3.5' in model.lower():
                return (
                    (tokens_input / 1000) * cls.OPENAI_GPT35_INPUT +
                    (tokens_output / 1000) * cls.OPENAI_GPT35_OUTPUT
                )
        
        elif provider == 'huggingface':
            return (
                (tokens_input / 1000) * cls.HUGGINGFACE_INPUT +
                (tokens_output / 1000) * cls.HUGGINGFACE_OUTPUT
            )
        
        return 0.0
    
    @classmethod
    def get_places_cost(cls, service: str) -> float:
        """
        Get Google Places API cost for a service.
        
        Args:
            service: Service name (text_search, nearby_search, details, photos)
            
        Returns:
            Cost in USD
        """
        pricing = {
            'text_search': cls.GOOGLE_PLACES_TEXT_SEARCH,
            'nearby_search': cls.GOOGLE_PLACES_NEARBY_SEARCH,
            'details': cls.GOOGLE_PLACES_DETAILS,
            'photos': cls.GOOGLE_PLACES_PHOTOS
        }
        return pricing.get(service, 0.0)
    
    @classmethod
    def get_tripadvisor_cost(cls, service: str) -> float:
        """
        Get TripAdvisor API cost for a service.
        
        Args:
            service: Service name (location_search, location_details, reviews)
            
        Returns:
            Cost in USD
        """
        pricing = {
            'location_search': cls.TRIPADVISOR_LOCATION_SEARCH,
            'location_details': cls.TRIPADVISOR_LOCATION_DETAILS,
            'reviews': cls.TRIPADVISOR_REVIEWS
        }
        return pricing.get(service, 0.0)
