"""
HuggingFace Adapter - LLM API Wrapper
======================================

Purpose:
- Call HuggingFace Inference API for text generation
- Support Llama-3.2-3B-Instruct (or other models)
- Handle retries, timeouts, error handling
- Track token usage and cost

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

import logging
import time
from typing import Optional, Dict, Any
import requests
from config import Config

logger = logging.getLogger(__name__)


class HuggingFaceAdapter:
    """
    Adapter for HuggingFace Inference API.
    
    Features:
    - Text generation with prompt
    - Retry logic with exponential backoff
    - Timeout handling
    - Token usage tracking
    
    Usage:
        hf = HuggingFaceAdapter()
        response = hf.generate("What is Da Nang famous for?")
        print(response['text'])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Initialize HuggingFace adapter.
        
        Args:
            api_key: HF API key (defaults to config)
            model: Model name (defaults to Llama-3.2-3B-Instruct)
            timeout: Request timeout in seconds
            max_retries: Max retry attempts
        """
        self.api_key = api_key or Config.HUGGINGFACE_API_KEY
        self.model = model or Config.HUGGINGFACE_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("HuggingFace API key not configured. Set HUGGINGFACE_API_KEY in .env")
        
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"[INFO] HuggingFace adapter initialized with model: {self.model}")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        return_full_text: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text using HuggingFace Inference API.
        
        Args:
            prompt: Input prompt for LLM
            max_new_tokens: Max tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling threshold
            do_sample: Enable sampling (vs greedy)
            return_full_text: Include prompt in response
            
        Returns:
            Dict with keys:
                - text: Generated text
                - model: Model name
                - tokens_used: Estimated token count
                - generation_time: Time in seconds
                
        Raises:
            RuntimeError: If API call fails after retries
        """
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": do_sample,
                "return_full_text": return_full_text
            }
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[INFO] HF API call attempt {attempt}/{self.max_retries}")
                start_time = time.time()
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                generation_time = time.time() - start_time
                
                # Check for errors
                if response.status_code == 503:
                    # Model loading
                    logger.warning(f"[WARN] Model loading, retrying in {2 ** attempt}s...")
                    time.sleep(2 ** attempt)
                    continue
                
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                elif isinstance(result, dict):
                    generated_text = result.get('generated_text', '')
                else:
                    raise ValueError(f"Unexpected response format: {type(result)}")
                
                # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
                tokens_used = (len(prompt) + len(generated_text)) // 4
                
                logger.info(
                    f"[INFO] HF generation successful: {len(generated_text)} chars, "
                    f"~{tokens_used} tokens, {generation_time:.2f}s"
                )
                
                return {
                    "text": generated_text,
                    "model": self.model,
                    "tokens_used": tokens_used,
                    "generation_time": generation_time,
                    "raw_response": result
                }
                
            except requests.exceptions.Timeout:
                logger.error(f"[ERROR] HF API timeout on attempt {attempt}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"HuggingFace API timeout after {self.max_retries} attempts")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"[ERROR] HF API request failed: {e}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"HuggingFace API error: {e}")
                time.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"[ERROR] Unexpected error in HF generation: {e}")
                raise RuntimeError(f"HuggingFace generation failed: {e}")
        
        raise RuntimeError("HuggingFace generation failed after all retries")
    
    def health_check(self) -> bool:
        """
        Check if HF API is accessible.
        
        Returns:
            True if API responds successfully
        """
        try:
            response = requests.get(
                f"https://api-inference.huggingface.co/status",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[ERROR] HF health check failed: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Test HuggingFace adapter
    hf = HuggingFaceAdapter()
    
    prompt = "What are the top 3 attractions in Da Nang, Vietnam?"
    result = hf.generate(prompt, max_new_tokens=256)
    
    print(f"Generated text:\n{result['text']}")
    print(f"\nModel: {result['model']}")
    print(f"Tokens used: ~{result['tokens_used']}")
    print(f"Generation time: {result['generation_time']:.2f}s")
