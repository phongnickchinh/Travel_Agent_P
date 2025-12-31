"""
LangChain LCEL Chain - Travel Itinerary Generator
==================================================

Purpose:
- Build LCEL chain for travel planning
- Support multiple LLM providers: Groq (FREE), HuggingFace, OpenAI
- Parse JSON output into DayPlan list
- Track token usage and cost from API responses

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from config import Config
from ..utils.mock_pois import MOCK_POIS_DA_NANG, get_mock_poi_summary
from ..utils.sanitization import escape_for_prompt
from ..model.mongo.plan import DayPlan

logger = logging.getLogger(__name__)


@dataclass
class LLMUsageStats:
    """Token usage statistics from LLM API response."""
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    model: str = ""
    provider: str = ""


def create_llm_instance(provider: str = None, temperature: float = 0.7):
    """
    Factory function to create LLM instance based on provider.
    
    Args:
        provider: "groq", "huggingface", or "openai"
        temperature: Sampling temperature
        
    Returns:
        LLM instance and provider name
    """
    provider = provider or Config.LLM_PROVIDER
    
    if provider == "groq":
        # Groq is FREE and fast - recommended for development
        from langchain_groq import ChatGroq
        
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured. Get free key at https://console.groq.com")
        
        llm = ChatGroq(
            api_key=Config.GROQ_API_KEY,
            model=Config.GROQ_MODEL or "llama-3.1-70b-versatile",
            temperature=temperature,
            max_tokens=4096,  # Increased for full itinerary generation (4-7 days)
        )
        return llm, "groq", Config.GROQ_MODEL or "llama-3.1-70b-versatile"
    
    elif provider == "huggingface":
        from langchain_community.llms.huggingface_endpoint import HuggingFaceEndpoint
        
        if not Config.HUGGINGFACE_API_KEY:
            raise ValueError("HUGGINGFACE_API_KEY not configured")
        
        llm = HuggingFaceEndpoint(
            endpoint_url=f"https://api-inference.huggingface.co/models/{Config.HUGGINGFACE_MODEL}",
            huggingfacehub_api_token=Config.HUGGINGFACE_API_KEY,
            task="text-generation",
            model_kwargs={
                "max_new_tokens": 4096,  # Increased for full itinerary generation (4-7 days)
                "temperature": temperature,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        )
        return llm, "huggingface", Config.HUGGINGFACE_MODEL
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'groq' or 'huggingface'")


class TravelPlannerChain:
    """
    LangChain LCEL chain for generating travel itineraries.
    
    Features:
    - Multiple LLM providers: Groq (FREE), HuggingFace
    - Structured prompt with POI context
    - JSON output parsing
    - EXACT token usage tracking from API responses
    
    Usage:
        chain = TravelPlannerChain()  # Uses Groq by default (FREE)
        result = chain.run({
            "destination": "Da Nang",
            "num_days": 3,
            "preferences": {"interests": ["beach", "culture"]},
            "start_date": "2025-06-01"
        })
        print(f"Tokens used: {result['usage'].tokens_total}")
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize LangChain chain.
        
        Args:
            provider: LLM provider ("groq", "huggingface") - defaults to config
            temperature: Sampling temperature
        """
        self.temperature = temperature
        
        # Create LLM instance based on provider
        self.llm, self.provider, self.model = create_llm_instance(provider, temperature)
        
        # Build LCEL chain
        self.chain = self._build_chain()
        
        logger.info(f"[INFO] LangChain initialized with {self.provider}: {self.model}")
    
    def _build_chain(self):
        """
        Build LCEL chain: Prompt → LLM → Parser.
        
        Returns:
            RunnableSequence (LCEL chain)
        """
        # Prompt template
        prompt_template = PromptTemplate(
        input_variables=["destination", "num_days", "preferences", "start_date", "poi_context", "accommodation_context"],
        template="""
        You are a senior professional travel planner AI with 10+ years of experience designing detailed, realistic itineraries.

        Your task is to create a HIGH-QUALITY, DETAILED, and WELL-STRUCTURED {num_days}-day travel itinerary for {destination}.

        Start date: {start_date}

        User preferences:
        {preferences}

        Below is the list of available POIs organized by geographic clusters. You MUST only select POIs from this list:
        {poi_context}
        
        Below is the list of available accommodations. You MUST select accommodations from this list:
        {accommodation_context}
        
        Return language: Vietnamese

        ========================
        CRITICAL INSTRUCTIONS
        ========================

        1. You MUST select POIs strictly from the provided list.
        - Use "poi_id" EXACTLY as shown.
        - Do NOT invent or modify any poi_id.

        2. Each day MUST include:
        - POIs per day based on user's pace preference:
            • If pace = "relaxed": 2-3 POIs per day
            • If pace = "moderate": 3-4 POIs per day  
            • If pace = "intensive": 5-6 POIs per day
            • If pace not specified: default to 3-4 POIs
        - If a geographic cluster is too small, you MUST combine multiple clusters to meet the daily POI count.
        - At least:
            • 1 food-related activity for lunch
            • 1 food-related activity for dinner

        3. Time planning rules:
        - Sort POIs in logical visiting order within the day.
        - Respect opening hours.
        - Avoid overlapping estimated visit times.
        - Travel pace should feel realistic and comfortable.

        4. Content quality rules:
        - Activities MUST be descriptive and natural (minimum 25 words per activity).
        - POI names in activities MUST be wrapped in double quotes ("") for map processing.
            Example: Buổi sáng, ghé thăm "Bãi biển Mỹ Khê" để tắm biển và thư giãn.
        - Notes MUST summarize the day’s theme, travel flow, and experience (minimum 25–40 words).
        - Avoid repetitive phrasing across days.

        5. Balance rules:
        - Mix categories such as nature, culture, food, sightseeing, relaxation.
        - CRITICAL: Each day should focus on a specific geographic area.

        6. GEOGRAPHIC CLUSTERING (CRITICAL - HIGHEST PRIORITY):
        - POIs are PRE-GROUPED into geographic clusters (areas within ~2km radius).
        - Each cluster is labeled with its center coordinates.
        - YOU MUST select POIs from the SAME CLUSTER for the same day whenever possible.
        - This minimizes travel distance and maximizes time at destinations.
        - Only mix clusters if absolutely necessary for category balance.
        - Order POIs within a day to minimize total travel distance between them.

        7. REVIEW-BASED DESTINATION EVALUATION:
        - Each POI includes review summaries with ratings (Reviews: ...).
        - Prioritize POIs with:
            • Higher ratings (★4.5+) for must-visit recommendations
            • More reviews (indicates popular/verified destinations)
            • Positive review sentiments
        - Mention notable experiences from reviews in your activity descriptions when relevant.
        - Avoid POIs with concerning negative reviews unless they offer unique value.

        8. BUDGET/PRICING EVALUATION:
        - Each POI shows price level (indicators).
        - Match POI price levels to user's budget preference:
            • If budget = "low": Prioritize Free, Budget-friendly options
            • If budget = "medium": Mix of Budget-friendly and Moderate
            • If budget = "high"/"luxury": Include Premium and Luxury options
        - Distribute costs across days to avoid budget spikes.
        - Note approximate daily costs in estimated_cost_vnd.

        9. Data consistency:
        - opening_hours and estimated_times MUST align with each POI.
        - location should represent the central point of the day's activities.

        10. Missing data handling (CRITICAL):
        - Do NOT skip a POI just because some fields are missing.
        - If any field is missing or unknown, still include the POI and set that field to null in the JSON output.
        - Apply this to every field (activities, opening_hours, estimated_times, accommodation fields, etc.) so the array length and poi_ids remain intact.

        11. ACCOMMODATION PLANNING (CRITICAL FOR MULTI-DAY TRIPS):
        - Each day MUST include accommodation information (except last day if returning home).
        - Select accommodation from the provided ACCOMMODATIONS list using accommodation_id.
        - Accommodation selection rules:
            • Day 1: Choose accommodation closest to first day's POI cluster.
            • Subsequent days: Keep same accommodation if next day's cluster is within 10km.
            • Change accommodation if next day's cluster is >10km away from current location.
        - If accommodation changes:
            • Set accommodation_changed = true
            • Provide accommodation_change_reason (e.g., "Di chuyển đến khu vực mới gần các điểm tham quan ngày mai")
        - Check-in/Check-out times:
            • check_in_time: Usually "14:00" or "15:00" (Day 1 or when changing)
            • check_out_time: Usually "11:00" or "12:00" (Last day or when leaving)
            • Only include check_out_time on days when leaving the accommodation
        - Match accommodation price level to user's budget preference.

        ========================
        OUTPUT FORMAT (STRICT)
        ========================

        Return ONLY a VALID JSON ARRAY.
        - No markdown
        - No explanation
        - No comments
        - No extra text before or after JSON

        Before returning the final answer:
        - Internally validate that the output is valid JSON
        - Ensure the array length equals {num_days}

        JSON schema example:
        [
        {{
            "day": 1,
            "date": "YYYY-MM-DD",
            "poi_ids": ["poi_id_1", "poi_id_2", "poi_id_3"],
            "location": [latitude, longitude],
            "activities": [
            "Buổi sáng, tham quan \"Tên POI 1\" để khám phá và trải nghiệm (12-20 từ).",
            "Dùng bữa trưa tại \"Tên POI 2\" với các món đặc sản địa phương hấp dẫn.",
            "Chiều tối, thư giãn tại \"Tên POI 3\" ngắm hoàng hôn tuyệt đẹp."
            ],
            "opening_hours": ["HH:MM-HH:MM", "HH:MM-HH:MM", "HH:MM-HH:MM"],
            "estimated_times": ["HH:MM-HH:MM", "HH:MM-HH:MM", "HH:MM-HH:MM"],
            "estimated_cost_vnd": 500000,
            "accommodation_id": "accommodation_poi_id",
            "accommodation_name": "Tên Khách Sạn",
            "accommodation_location": [latitude, longitude],
            "check_in_time": "14:00",
            "accommodation_changed": false,
            "notes": "Tóm tắt trải nghiệm ngày 1 với dòng chảy tự nhiên và mạch lạc (25-40 từ)..."
        }},
        {{
            "day": 2,
            "date": "YYYY-MM-DD",
            "poi_ids": ["poi_id_4", "poi_id_5", "poi_id_6"],
            "location": [latitude, longitude],
            "activities": [
            "Sáng sớm ghé \"Tên POI 4\" để tham quan và chụp ảnh...",
            "Trưa thưởng thức ẩm thực tại \"Tên POI 5\"...",
            "Chiều khám phá \"Tên POI 6\" với nhiều hoạt động thú vị..."
            ],
            "opening_hours": ["HH:MM-HH:MM", "HH:MM-HH:MM", "HH:MM-HH:MM"],
            "estimated_times": ["HH:MM-HH:MM", "HH:MM-HH:MM", "HH:MM-HH:MM"],
            "estimated_cost_vnd": 600000,
            "accommodation_id": "new_accommodation_poi_id",
            "accommodation_name": "Tên Khách Sạn Mới",
            "accommodation_location": [latitude, longitude],
            "check_out_time": "11:00",
            "check_in_time": "15:00",
            "accommodation_changed": true,
            "accommodation_change_reason": "Di chuyển đến khu vực mới gần các điểm tham quan ngày mai",
            "notes": "Tóm tắt ngày 2 với trải nghiệm phong phú và đa dạng..."
        }}
        ]

        CRITICAL: Ensure valid JSON syntax with proper commas, brackets, and quotes.
        Generate the {num_days}-day itinerary now (JSON array only, no extra text):
        """
        )
        
        # Output parser (extract JSON from text)
        parser = StrOutputParser()
        
        # Build chain
        chain = (
            RunnablePassthrough()
            | prompt_template
            | self.llm
            | parser
        )
        
        return chain
    
    def run(self, input_data: Dict[str, Any], poi_context: str = None, accommodation_context: str = None) -> Dict[str, Any]:
        """
        Generate travel itinerary.
        
        Args:
            input_data: Dict with keys:
                - destination: str
                - num_days: int
                - preferences: dict
                - start_date: str (YYYY-MM-DD)
            poi_context: Pre-formatted POI context string (from PlacesService)
                         If None, falls back to mock data
            accommodation_context: Pre-formatted accommodation context string
                         If None, uses empty placeholder
                
        Returns:
            Dict with keys:
                - itinerary: List[DayPlan]
                - llm_response_raw: str
                - model: str
                - success: bool
                - error: Optional[str]
        """
        try:
            # Prepare input
            destination = input_data.get('destination', 'Da Nang')
            num_days = input_data.get('num_days', 3)
            preferences = input_data.get('preferences', {})
            start_date = input_data.get('start_date')
            
            # Generate start_date if not provided
            if not start_date:
                start_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Format preferences
            pref_text = self._format_preferences(preferences)
            
            # Use provided POI context or fall back to mock data
            if poi_context:
                logger.info(f"[INFO] Using real POI context ({len(poi_context)} chars)")
            else:
                logger.warning("[WARN] No POI context provided, using mock data")
                poi_context = get_mock_poi_summary()
            
            # Use provided accommodation context or placeholder
            if accommodation_context:
                logger.info(f"[INFO] Using accommodation context ({len(accommodation_context)} chars)")
            else:
                logger.warning("[WARN] No accommodation context provided")
                accommodation_context = "No specific accommodations found. Please suggest appropriate lodging options based on the destination and budget."
            
            # Prepare chain input
            chain_input = {
                "destination": destination,
                "num_days": num_days,
                "preferences": pref_text,
                "start_date": start_date,
                "poi_context": poi_context,
                "accommodation_context": accommodation_context
            }
            
            logger.info(f"[INFO] Running LangChain for {num_days}-day {destination} itinerary")
            
            # Run chain
            llm_output = self.chain.invoke(chain_input)
            
            # Log response details for debugging
            if isinstance(llm_output, str):
                output_len = len(llm_output)
                logger.info(f"[INFO] LLM response received: {output_len} chars")
            elif hasattr(llm_output, 'content'):
                output_len = len(llm_output.content) if llm_output.content else 0
                logger.info(f"[INFO] LLM response received: {output_len} chars (AIMessage)")
            else:
                output_len = 0
                logger.warning(f"[WARN] LLM response type unexpected: {type(llm_output)}")
            
            # Extract text from response (handle both str and AIMessage)
            if hasattr(llm_output, 'content'):
                llm_text = llm_output.content
            else:
                llm_text = str(llm_output)
            
            # Debug: log first 500 chars of response if empty or too short
            if not llm_text or len(llm_text) < 50:
                logger.error(f"[ERROR] LLM returned empty/short response: '{llm_text}'")
                if hasattr(llm_output, 'response_metadata'):
                    logger.error(f"[ERROR] Response metadata: {llm_output.response_metadata}")
            else:
                logger.debug(f"[DEBUG] LLM response preview: {llm_text[:200]}...")
            
            # Extract usage stats if available (Groq provides this)
            usage = LLMUsageStats(
                model=self.model,
                provider=self.provider
            )
            
            if hasattr(llm_output, 'response_metadata'):
                meta = llm_output.response_metadata
                token_usage = meta.get('token_usage', {})
                usage.tokens_input = token_usage.get('prompt_tokens', 0)
                usage.tokens_output = token_usage.get('completion_tokens', 0)
                usage.tokens_total = token_usage.get('total_tokens', 0)
                
                # Calculate cost for Groq (currently FREE but tracking for future)
                if self.provider == "groq":
                    from ..providers.llm.groq_adapter import GROQ_PRICING
                    pricing = GROQ_PRICING.get(self.model, {"input": 0.0, "output": 0.0})
                    usage.cost_usd = (
                        (usage.tokens_input / 1_000_000) * pricing["input"] +
                        (usage.tokens_output / 1_000_000) * pricing["output"]
                    )
            
            # Parse JSON output
            itinerary = self._parse_itinerary(llm_text, num_days, start_date)
            
            return {
                "itinerary": itinerary,
                "llm_response_raw": llm_text,
                "model": self.model,
                "provider": self.provider,
                "usage": usage,
                "tokens_input": usage.tokens_input,
                "tokens_output": usage.tokens_output,
                "tokens_total": usage.tokens_total,
                "cost_usd": usage.cost_usd,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"[ERROR] LangChain execution failed: {e}")
            return {
                "itinerary": [],
                "llm_response_raw": None,
                "model": self.model,
                "provider": getattr(self, 'provider', 'unknown'),
                "usage": LLMUsageStats(),
                "tokens_input": 0,
                "tokens_output": 0,
                "tokens_total": 0,
                "cost_usd": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _format_preferences(self, preferences: Dict[str, Any]) -> str:
        """
        Format user preferences for prompt.
        
        Args:
            preferences: User input dict
            
        Returns:
            Formatted string
        """
        lines = []
        
        if interests := preferences.get('interests'):
            # Limit interests and escape to prevent prompt injection
            safe_interests = []
            for i in interests[:10]:
                if isinstance(i, str):
                    safe_interests.append(escape_for_prompt(i, max_length=50))
            if safe_interests:
                lines.append(f"- Interests: {', '.join(safe_interests)}")
        
        if budget := preferences.get('budget'):
            lines.append(f"- Budget: {escape_for_prompt(str(budget), max_length=20)}")
        
        if pace := preferences.get('pace'):
            lines.append(f"- Pace: {escape_for_prompt(str(pace), max_length=20)}")
        
        if dietary := preferences.get('dietary'):
            lines.append(f"- Dietary: {escape_for_prompt(str(dietary), max_length=50)}")
        
        return '\n'.join(lines) if lines else "- No specific preferences"
    
    def _parse_itinerary(
        self,
        llm_output: str,
        num_days: int,
        start_date: str
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM JSON output into DayPlan list.
        
        Args:
            llm_output: Raw LLM response
            num_days: Expected day count
            start_date: ISO date string
            
        Returns:
            List of DayPlan dicts
        """
        try:
            # Extract JSON array from text (handle markdown code blocks)
            json_match = re.search(r'\[.*\]', llm_output, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in LLM output")
            
            json_str = json_match.group(0)
            raw_itinerary = json.loads(json_str)
            
            if not isinstance(raw_itinerary, list):
                raise ValueError("Parsed output is not a list")
            
            # Validate and normalize
            itinerary = []
            for day_data in raw_itinerary[:num_days]:  # Limit to num_days
                # Extract location as [lat, lng] - LLM should provide this
                location = day_data.get('location')
                if isinstance(location, list) and len(location) == 2:
                    location = [float(location[0]), float(location[1])]
                else:
                    location = None
                
                # Extract accommodation location as [lat, lng] if provided
                accommodation_location = day_data.get('accommodation_location')
                if isinstance(accommodation_location, list) and len(accommodation_location) == 2:
                    accommodation_location = [float(accommodation_location[0]), float(accommodation_location[1])]
                else:
                    accommodation_location = None
                
                day_plan = DayPlan(
                    day=day_data.get('day', len(itinerary) + 1),
                    date=day_data.get('date', self._calculate_date(start_date, len(itinerary))),
                    poi_ids=day_data.get('poi_ids', []),
                    activities=day_data.get('activities', []),
                    notes=day_data.get('notes'),
                    location=location,
                    # opening_hours and estimated_times from LLM
                    opening_hours=day_data.get('opening_hours', []),
                    estimated_times=day_data.get('estimated_times', []),
                    estimated_cost_vnd=day_data.get('estimated_cost_vnd', 0),
                    # Accommodation fields
                    accommodation_id=day_data.get('accommodation_id'),
                    accommodation_name=day_data.get('accommodation_name'),
                    accommodation_address=day_data.get('accommodation_address'),
                    accommodation_location=accommodation_location,
                    check_in_time=day_data.get('check_in_time'),
                    check_out_time=day_data.get('check_out_time'),
                    accommodation_changed=day_data.get('accommodation_changed', False),
                    accommodation_change_reason=day_data.get('accommodation_change_reason')
                )
                itinerary.append(day_plan.model_dump())
            
            logger.info(f"[INFO] Parsed {len(itinerary)} days from LLM output")
            return itinerary
            
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] JSON parsing failed: {e}")
            # Fallback: Generate default itinerary
            return self._generate_fallback_itinerary(num_days, start_date)
        
        except Exception as e:
            logger.error(f"[ERROR] Itinerary parsing failed: {e}")
            return self._generate_fallback_itinerary(num_days, start_date)
    
    def _calculate_date(self, start_date: str, day_offset: int) -> str:
        """
        Calculate date for a specific day.
        
        Args:
            start_date: ISO date (YYYY-MM-DD)
            day_offset: Days to add (0-based)
            
        Returns:
            ISO date string
        """
        date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        new_date = date_obj + timedelta(days=day_offset)
        return new_date.strftime('%Y-%m-%d')
    
    def _generate_fallback_itinerary(self, num_days: int, start_date: str) -> List[Dict[str, Any]]:
        """
        Generate basic itinerary when LLM parsing fails.
        
        Args:
            num_days: Number of days
            start_date: ISO date
            
        Returns:
            List of DayPlan dicts
        """
        logger.warning("[WARN] Using fallback itinerary due to LLM parsing error")
        
        # Use first 3 POIs per day from mock dataset
        itinerary = []
        poi_index = 0
        
        for day in range(1, num_days + 1):
            poi_ids = []
            activities = []
            
            for _ in range(3):  # 3 POIs per day
                if poi_index < len(MOCK_POIS_DA_NANG):
                    poi = MOCK_POIS_DA_NANG[poi_index]
                    poi_ids.append(poi['poi_id'])
                    activities.append(f"Visit {poi['name_en']}")
                    poi_index += 1
            
            day_plan = DayPlan(
                day=day,
                date=self._calculate_date(start_date, day - 1),
                poi_ids=poi_ids,
                activities=activities,
                notes="Auto-generated fallback itinerary"
            )
            itinerary.append(day_plan.model_dump())
        
        return itinerary


# Example usage
if __name__ == "__main__":
    chain = TravelPlannerChain()
    
    result = chain.run({
        "destination": "Da Nang",
        "num_days": 3,
        "preferences": {
            "interests": ["beach", "culture", "food"],
            "budget": "medium"
        },
        "start_date": "2025-06-01"
    })
    
    print(f"Success: {result['success']}")
    print(f"Model: {result['model']}")
    print(f"\nItinerary ({len(result['itinerary'])} days):")
    for day in result['itinerary']:
        print(f"  Day {day['day']}: {len(day['poi_ids'])} POIs")
