"""
Groq Adapter - LLM API Wrapper (FREE for Development)
======================================================

Purpose:
- Call Groq API for text generation (FREE tier)
- Support Llama-3.1-70B, Llama-3.1-8B, Mixtral-8x7B
- Provides EXACT token usage from API response
- Very fast inference (500+ tokens/sec)

Author: Travel Agent P Team
Date: Week 4 - LLM Integration

Groq Free Tier Limits:
- 30 requests/minute
- 6,000 tokens/minute
- Models: llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768

Pricing (all FREE for now):
- llama-3.1-70b-versatile: $0.00 (free tier)
- llama-3.1-8b-instant: $0.00 (free tier)
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests

from config import Config

logger = logging.getLogger(__name__)


# Groq pricing per million tokens (for future cost tracking if they start charging)
GROQ_PRICING = {
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.2-3b-preview": {"input": 0.06, "output": 0.06},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "gemma2-9b-it": {"input": 0.20, "output": 0.20},
}


@dataclass
class GroqUsage:
    """Exact usage data from Groq API response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    queue_time: float  # seconds
    prompt_time: float  # seconds
    completion_time: float  # seconds
    total_time: float  # seconds
    
    def calculate_cost(self, model: str) -> float:
        """Calculate cost based on actual token usage."""
        pricing = GROQ_PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (self.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class GroqAdapter:
    """
    Adapter for Groq API - FREE LLM inference.
    
    Features:
    - FREE tier with generous limits (30 req/min)
    - Very fast inference (500+ tokens/sec)
    - EXACT token usage from API response
    - Supports Llama-3.1-70B (best quality)
    
    Usage:
        groq = GroqAdapter()
        response = groq.generate("What is Da Nang famous for?")
        print(response['text'])
        print(f"Tokens used: {response['usage'].total_tokens}")
    """
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Recommended models (in order of quality)
    MODELS = {
        "best": "llama-3.1-70b-versatile",  # Best quality, slower
        "fast": "llama-3.1-8b-instant",      # Fastest, good quality
        "balanced": "mixtral-8x7b-32768",    # Good balance
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize Groq adapter.
        
        Args:
            api_key: Groq API key (get free at console.groq.com)
            model: Model name (default: llama-3.1-70b-versatile)
            timeout: Request timeout in seconds
            max_retries: Max retry attempts
        """
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL or self.MODELS["best"]
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError(
                "Groq API key not configured. "
                "Get FREE key at https://console.groq.com and set GROQ_API_KEY in .env"
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"[INFO] Groq adapter initialized with model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Generate text using Groq API.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction (optional)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling threshold
            
        Returns:
            Dict with keys:
                - text: Generated text
                - model: Model name
                - usage: GroqUsage with EXACT token counts
                - cost_usd: Calculated cost (currently $0)
                - generation_time: Total time in seconds
                
        Raises:
            RuntimeError: If API call fails after retries
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[INFO] Groq API call attempt {attempt}/{self.max_retries}")
                start_time = time.time()
                
                response = requests.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                total_time = time.time() - start_time
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", 2 ** attempt))
                    logger.warning(f"[WARN] Rate limited, retrying in {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Extract text
                generated_text = data["choices"][0]["message"]["content"]
                
                # Extract EXACT usage from API response
                usage_data = data.get("usage", {})
                x_groq = data.get("x_groq", {}).get("usage", {})
                
                usage = GroqUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                    queue_time=x_groq.get("queue_time", 0),
                    prompt_time=x_groq.get("prompt_time", 0),
                    completion_time=x_groq.get("completion_time", 0),
                    total_time=x_groq.get("total_time", total_time),
                )
                
                # Calculate cost (currently FREE)
                cost_usd = usage.calculate_cost(self.model)
                
                logger.info(
                    f"[INFO] Groq generation successful: "
                    f"{usage.total_tokens} tokens, "
                    f"${cost_usd:.6f}, "
                    f"{total_time:.2f}s"
                )
                
                return {
                    "text": generated_text,
                    "model": self.model,
                    "usage": usage,
                    "tokens_input": usage.prompt_tokens,
                    "tokens_output": usage.completion_tokens,
                    "tokens_total": usage.total_tokens,
                    "cost_usd": cost_usd,
                    "generation_time": total_time,
                    "raw_response": data
                }
                
            except requests.exceptions.Timeout:
                logger.error(f"[ERROR] Groq API timeout on attempt {attempt}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"Groq API timeout after {self.max_retries} attempts")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"[ERROR] Groq API request failed: {e}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"Groq API error: {e}")
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Groq generation failed after all retries")
    
    def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[ERROR] Groq health check failed: {e}")
            return False
    
    def list_models(self) -> list:
        """List available models."""
        try:
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return [m["id"] for m in response.json().get("data", [])]
        except Exception as e:
            logger.error(f"[ERROR] Failed to list models: {e}")
            return list(self.MODELS.values())


# Example usage
if __name__ == "__main__":
    groq = GroqAdapter()
    
    result = groq.generate(
        prompt="What are the top 3 attractions in Da Nang, Vietnam?",
        system_prompt="You are a helpful travel assistant.",
        max_tokens=256
    )
    
    print(f"Generated text:\n{result['text']}")
    print(f"\nModel: {result['model']}")
    print(f"Tokens (input/output/total): {result['tokens_input']}/{result['tokens_output']}/{result['tokens_total']}")
    print(f"Cost: ${result['cost_usd']:.6f}")
    print(f"Generation time: {result['generation_time']:.2f}s")
