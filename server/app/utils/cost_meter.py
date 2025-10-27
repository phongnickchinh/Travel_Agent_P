"""
Cost Meter Decorator
====================

Purpose:
- Decorator to automatically track API costs
- Measure latency and log performance
- Calculate costs based on provider pricing

Usage:
    @track_cost(provider="google_places", service="text_search")
    def search_places(query):
        response = requests.get(...)
        return response.json()

Author: Travel Agent P Team
Date: October 27, 2025
"""

import time
import logging
from functools import wraps
from typing import Callable, Optional, Dict, Any
from datetime import datetime

from ..model.cost_usage import ProviderPricing
from ..repo.postgre.interfaces.cost_usage_interface import CostUsageInterface
from ..core.di_container import DIContainer

logger = logging.getLogger(__name__)


def track_cost(
    provider: str,
    service: Optional[str] = None,
    calculate_cost: Optional[Callable] = None,
    extract_tokens: Optional[Callable] = None,
    user_id_param: Optional[str] = None,
    plan_id_param: Optional[str] = None
):
    """
    Decorator to track API call costs.
    
    Args:
        provider: Provider name (google_places, openai, etc.)
        service: Service/API name
        calculate_cost: Optional function to calculate cost from response
        extract_tokens: Optional function to extract tokens from response
        user_id_param: Parameter name containing user_id in kwargs
        plan_id_param: Parameter name containing plan_id in kwargs
    
    Example:
        # Simple usage
        @track_cost(provider="google_places", service="text_search")
        def search_places(query):
            response = requests.get(...)
            return response.json()
        
        # With custom cost calculation
        def calc_llm_cost(response):
            usage = response.get('usage', {})
            return ProviderPricing.calculate_llm_cost(
                'openai', 'gpt-4',
                usage.get('prompt_tokens', 0),
                usage.get('completion_tokens', 0)
            )
        
        @track_cost(
            provider="openai",
            service="chat_completion",
            calculate_cost=calc_llm_cost,
            extract_tokens=lambda r: r.get('usage', {}),
            user_id_param="user_id"
        )
        def generate_itinerary(prompt, user_id):
            response = openai.ChatCompletion.create(...)
            return response
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = True
            status_code = None
            error_message = None
            cost_usd = 0.0
            tokens_input = 0
            tokens_output = 0
            response = None
            
            # Extract context from kwargs
            user_id = kwargs.get(user_id_param) if user_id_param else None
            plan_id = kwargs.get(plan_id_param) if plan_id_param else None
            
            try:
                # Call the actual function
                response = func(*args, **kwargs)
                
                # Extract tokens if function provided
                if extract_tokens and response:
                    try:
                        tokens_data = extract_tokens(response)
                        tokens_input = tokens_data.get('prompt_tokens', 0)
                        tokens_output = tokens_data.get('completion_tokens', 0)
                    except Exception as e:
                        logger.warning(f"Failed to extract tokens: {e}")
                
                # Calculate cost if function provided
                if calculate_cost and response:
                    try:
                        cost_usd = calculate_cost(response)
                    except Exception as e:
                        logger.warning(f"Failed to calculate cost: {e}")
                elif service:
                    # Use default pricing
                    if provider == "google_places":
                        cost_usd = ProviderPricing.get_places_cost(service)
                    elif provider == "tripadvisor":
                        cost_usd = ProviderPricing.get_tripadvisor_cost(service)
                
                return response
            
            except Exception as e:
                success = False
                error_message = str(e)
                
                # Try to extract status code from exception
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                
                raise
            
            finally:
                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Log cost record
                try:
                    # Get repository from DI container
                    container = DIContainer.get_instance()
                    cost_repo = container.resolve(CostUsageInterface.__name__)
                    
                    cost_repo.create(
                        provider=provider,
                        service=service,
                        endpoint=func.__name__,
                        method="FUNCTION",
                        tokens_input=tokens_input,
                        tokens_output=tokens_output,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        status_code=status_code,
                        success=success,
                        user_id=user_id,
                        plan_id=plan_id,
                        request_id=None,
                        metadata={
                            'function': func.__name__,
                            'module': func.__module__
                        },
                        error_message=error_message,
                        commit=True
                    )
                except Exception as e:
                    logger.error(f"Failed to track cost: {e}")
        
        return wrapper
    return decorator


# Convenience decorators for common providers

def track_google_places_cost(service: str):
    """
    Track Google Places API costs.
    
    Usage:
        @track_google_places_cost("text_search")
        def search_places(query):
            ...
    """
    return track_cost(provider="google_places", service=service)


def track_openai_cost(model: str = "gpt-4"):
    """
    Track OpenAI API costs.
    
    Usage:
        @track_openai_cost("gpt-4")
        def generate_text(prompt):
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            return response
    """
    def calc_cost(response):
        usage = response.get('usage', {})
        return ProviderPricing.calculate_llm_cost(
            'openai',
            model,
            usage.get('prompt_tokens', 0),
            usage.get('completion_tokens', 0)
        )
    
    def extract_tokens(response):
        return response.get('usage', {})
    
    return track_cost(
        provider="openai",
        service=f"chat_completion_{model}",
        calculate_cost=calc_cost,
        extract_tokens=extract_tokens
    )


def track_huggingface_cost():
    """
    Track HuggingFace API costs.
    
    Usage:
        @track_huggingface_cost()
        def generate_embeddings(text):
            ...
    """
    def calc_cost(response):
        # Estimate tokens (rough approximation)
        if isinstance(response, list):
            tokens = len(str(response)) // 4
        else:
            tokens = len(str(response)) // 4
        
        return ProviderPricing.calculate_llm_cost(
            'huggingface',
            'default',
            tokens,
            0
        )
    
    return track_cost(
        provider="huggingface",
        service="inference",
        calculate_cost=calc_cost
    )


def track_tripadvisor_cost(service: str):
    """
    Track TripAdvisor API costs.
    
    Usage:
        @track_tripadvisor_cost("location_search")
        def search_locations(query):
            ...
    """
    return track_cost(provider="tripadvisor", service=service)


# Example usage
if __name__ == "__main__":
    import requests
    
    # Example 1: Track Google Places API
    @track_google_places_cost("text_search")
    def search_places(query: str):
        """Search places using Google Places API."""
        print(f"Searching for: {query}")
        # Simulate API call
        time.sleep(0.1)
        return {"results": [{"name": "Sample Place"}]}
    
    # Example 2: Track OpenAI API
    @track_openai_cost("gpt-4")
    def generate_itinerary(prompt: str):
        """Generate itinerary using OpenAI."""
        print(f"Generating itinerary for: {prompt}")
        # Simulate API call
        time.sleep(0.2)
        return {
            "choices": [{"text": "Day 1: Visit beach..."}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }
    
    # Test the decorators
    print("\n" + "="*80)
    print("Testing Cost Tracking Decorators")
    print("="*80)
    
    try:
        result1 = search_places("restaurants in Danang")
        print(f"✅ Places search completed: {result1}")
    except Exception as e:
        print(f"❌ Places search failed: {e}")
    
    try:
        result2 = generate_itinerary("3 days in Danang")
        print(f"✅ Itinerary generation completed: {result2}")
    except Exception as e:
        print(f"❌ Itinerary generation failed: {e}")
    
    print("\n💰 Cost records have been logged to database")
