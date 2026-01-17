"""
LLM Sub-package
===============

LangChain integration and LLM provider adapters.

Modules:
- lc_chain: LCEL chain for itinerary generation
- groq_adapter: Groq LLM adapter (FREE tier)
- hf_adapter: HuggingFace adapter

Author: Travel Agent P Team
"""

from .lc_chain import TravelPlannerChain, LLMUsageStats, create_llm_instance

__all__ = [
    "TravelPlannerChain",
    "LLMUsageStats",
    "create_llm_instance",
]
