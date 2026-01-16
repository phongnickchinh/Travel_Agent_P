"""
Custom Exception Hierarchy for Travel Agent P
=============================================

Provides specific exceptions for different error scenarios,
replacing generic Exception catches for better error handling.

Usage:
    from app.common.exceptions import (
        DatabaseError,
        ExternalAPIError,
        ValidationError,
        PlanGenerationError
    )
    
    try:
        result = some_db_operation()
    except PyMongoError as e:
        raise DatabaseError("Failed to fetch POIs") from e
"""


class TravelAgentError(Exception):
    """
    Base exception for all Travel Agent P errors.
    
    Attributes:
        message: Human-readable error message
        code: Error code for API responses
        details: Additional error details
    """
    
    def __init__(self, message: str, code: str = "TA000", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


# ============================================
# Database Exceptions
# ============================================

class DatabaseError(TravelAgentError):
    """Base exception for database-related errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="DB001", details=details)


class MongoDBError(DatabaseError):
    """MongoDB operation failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "DB002"


class PostgreSQLError(DatabaseError):
    """PostgreSQL operation failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "DB003"


class RedisError(DatabaseError):
    """Redis operation failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "DB004"


class ElasticsearchError(DatabaseError):
    """Elasticsearch operation failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "DB005"


# ============================================
# External API Exceptions
# ============================================

class ExternalAPIError(TravelAgentError):
    """Base exception for external API call failures."""
    
    def __init__(self, message: str, provider: str = None, details: dict = None):
        details = details or {}
        if provider:
            details["provider"] = provider
        super().__init__(message, code="API001", details=details)


class GooglePlacesAPIError(ExternalAPIError):
    """Google Places API call failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, provider="google_places", details=details)
        self.code = "API002"


class LLMAPIError(ExternalAPIError):
    """LLM API call failed (Groq, HuggingFace, etc.)."""
    
    def __init__(self, message: str, provider: str = None, details: dict = None):
        super().__init__(message, provider=provider, details=details)
        self.code = "API003"


# ============================================
# Validation Exceptions
# ============================================

class ValidationError(TravelAgentError):
    """Input validation failed."""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, code="VAL001", details=details)


class SchemaValidationError(ValidationError):
    """JSON schema validation failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "VAL002"


# ============================================
# Authentication Exceptions
# ============================================

class AuthenticationError(TravelAgentError):
    """Authentication failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="AUTH001", details=details)


class TokenError(AuthenticationError):
    """Token-related error (expired, invalid, blacklisted)."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details=details)
        self.code = "AUTH002"


class AuthorizationError(TravelAgentError):
    """User not authorized for this action."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="AUTH003", details=details)


# ============================================
# Business Logic Exceptions
# ============================================

class PlanGenerationError(TravelAgentError):
    """Plan generation failed."""
    
    def __init__(self, message: str, plan_id: str = None, details: dict = None):
        details = details or {}
        if plan_id:
            details["plan_id"] = plan_id
        super().__init__(message, code="PLAN001", details=details)


class POIFetchError(TravelAgentError):
    """POI fetching failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="POI001", details=details)


class ClusteringError(TravelAgentError):
    """POI clustering failed."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="CLUST001", details=details)


# ============================================
# Rate Limiting Exceptions
# ============================================

class RateLimitError(TravelAgentError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, details: dict = None):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, code="RATE001", details=details)


# ============================================
# Resource Exceptions
# ============================================

class NotFoundError(TravelAgentError):
    """Resource not found."""
    
    def __init__(self, resource: str, identifier: str = None, details: dict = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        details = details or {}
        details["resource"] = resource
        if identifier:
            details["identifier"] = identifier
        super().__init__(message, code="NF001", details=details)


class ConflictError(TravelAgentError):
    """Resource conflict (duplicate, etc.)."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="CONF001", details=details)
