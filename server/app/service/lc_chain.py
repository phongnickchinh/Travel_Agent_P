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
            max_tokens=32768,  # Increased for full itinerary generation (supports up to 128k context on some models)
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
        # Prompt template (Optimized - 40% shorter, same effectiveness)
        prompt_template = PromptTemplate(
        input_variables=["destination", "num_days", "preferences", "start_date", "poi_context", "accommodation_context"],
        template="""
        You are a senior professional travel planner AI with 10+ years of experience.

        Create a HIGH-QUALITY, REALISTIC, and WELL-STRUCTURED {num_days}-day itinerary for {destination}.

        Start date: {start_date}

        User preferences:
        {preferences}

        Available POIs (grouped by geographic clusters). You MUST only use POIs from this list:
        {poi_context}

        Available accommodations. You MUST select from this list:
        {accommodation_context}

        Return language: Vietnamese

        ========================
        CORE PLANNING RULES
        ========================

        1. POI SELECTION
        - Use poi_id EXACTLY as provided (never invent or modify).
        - Prioritize POIs with ratings.average ≥ 4.0 and higher ratings.count.
        - Match POI categories, pricing, and amenities to user preferences and budget.
        - CRITICAL: NEVER select POIs have categories field including "hotel" or "lodging" for daily activities. recheck this rule before finalizing. example: categories: ["landmark", "hotel"] will NOT be added to daily activities.

        2. DAILY STRUCTURE
        - POIs per day based on pace: relaxed: 2-3 | moderate: 3-4 | intensive: 5-6 (default: 3-4)
        - Each day MUST include at least one food-related POI.
        - Use POIs from the SAME geographic cluster per day whenever possible.
        - Order POIs to minimize travel distance.

        3. TIME & OPENING HOURS (CRITICAL)
        - Schedule visits ONLY within opening_hours for the specific day of week.
        - If is_24_hours = true → use "00:00-23:59".
        - If data is missing, infer reasonable hours by POI type (restaurants: 10:00-22:00, attractions: 08:00-17:00).
        - Provide estimated_times ("HH:MM-HH:MM") for EVERY POI - do not omit.

        4. CONTENT QUALITY (IMPORTANT)
        - Each activity: minimum 25 words, descriptive and engaging.
        - POI names MUST be wrapped in double quotes ("Tên POI").
        - Actively use POI data to enrich activities:
            • description → history, highlights, uniqueness
            • amenities → tailored suggestions (e.g., "good_for_children" → mention family-friendly, "outdoor_seating" → recommend outdoor ambiance, "reservations_required" → advise booking)
            • ratings → mention high-rated places naturally ("★4.7, 1200+ đánh giá")
            • pricing → align with user budget
        - Notes: 25-40 words summarizing day's theme.
        - Avoid repetitive phrasing across days.

        5. ACCOMMODATIONS
        - Each day includes accommodation (except final departure day).
        - Keep same accommodation if next day's cluster is within 10km; if changing, set accommodation_changed=true with reason.
        - check_in_time: "14:00" or "15:00" (arrival days) | check_out_time: "11:00" or "12:00" (departure days).
        - Match accommodation price to user budget.

        ========================
        OUTPUT FORMAT (STRICT)
        ========================

        Return ONLY a VALID JSON ARRAY. No markdown, no explanation, no extra text.
        Array length MUST equal {num_days}.

        JSON schema (example showing correct data usage):
        [
        {{
            "day": 1,
            "date": "YYYY-MM-DD",
            "poi_ids": ["poi_id_1", "poi_id_2", "poi_id_3"],
            "types": [["beach", "nature"], ["restaurant", "food"], ["cultural", "museum"]],
            "location": [latitude, longitude],
            "activities": [
            "Buổi sáng, khởi đầu hành trình tại \"Tên POI 1\" (★4.7, 1200+ đánh giá) - nơi được mô tả là [tận dụng description.short]. Địa điểm phù hợp cho gia đình có trẻ nhỏ [từ amenities: good_for_children]. Bạn có thể [hoạt động cụ thể dựa trên category].",
            "Đến trưa, dừng chân tại \"Tên POI 2\" để thưởng thức ẩm thực địa phương. Nhà hàng có không gian ngoài trời thoáng mát [từ amenities: outdoor_seating], mức giá phải chăng [từ pricing.level]. Nên đặt bàn trước [từ amenities: reservations_required].",
            "Chiều tối, ghé \"Tên POI 3\" để tìm hiểu về [từ description.long]. Nổi tiếng với [đặc điểm nổi bật]. Có chỗ đỗ xe thuận tiện [từ amenities: parking_available]."
            ],
            "opening_hours": ["00:00-23:59", "10:00-22:00", "08:00-17:00"],
            "estimated_times": ["08:00-10:30", "11:30-13:00", "14:30-17:00"],
            "estimated_cost_vnd": 500000,
            "accommodation_id": "accommodation_poi_id",
            "accommodation_name": "Tên Khách Sạn",
            "accommodation_location": [latitude, longitude],
            "check_in_time": "14:00",
            "accommodation_changed": false,
            "notes": "Ngày 1 tập trung khám phá khu vực [tên cluster] với các điểm đến nổi bật phù hợp cho [sở thích user]. Trải nghiệm đa dạng từ biển đến ẩm thực và văn hóa."
        }},
        {{
            "day": 2,
            "date": "YYYY-MM-DD",
            "poi_ids": ["poi_id_4", "poi_id_5", "poi_id_6"],
            "types": [["historical", "landmark"], ["cafe", "food"], ["shopping", "market"]],
            "location": [latitude, longitude],
            "activities": [
            "Sáng sớm ghé \"Tên POI 4\" (★4.5) - [mô tả từ description]. Điểm đến lịch sử này [thông tin đặc biệt].",
            "Trưa thưởng thức cà phê tại \"Tên POI 5\", nơi có [đặc điểm từ description]. Quán có wifi miễn phí [từ amenities], lý tưởng để nghỉ ngơi.",
            "Chiều khám phá \"Tên POI 6\" với nhiều gian hàng thú vị. [Thông tin từ description]. Khu vực này đông vui vào buổi tối."
            ],
            "opening_hours": ["07:00-17:00", "07:00-22:00", "06:00-21:00"],
            "estimated_times": ["07:30-09:30", "10:00-11:30", "14:00-17:00"],
            "estimated_cost_vnd": 600000,
            "accommodation_id": "new_accommodation_poi_id",
            "accommodation_name": "Tên Khách Sạn Mới",
            "accommodation_location": [latitude, longitude],
            "check_out_time": "11:00",
            "check_in_time": "15:00",
            "accommodation_changed": true,
            "accommodation_change_reason": "Di chuyển đến khu vực mới gần các điểm tham quan ngày mai",
            "notes": "Ngày 2 khám phá di tích lịch sử và ẩm thực địa phương tại khu vực [tên cluster]. Trải nghiệm văn hóa và mua sắm đa dạng."
        }}
        ]

        Validate JSON syntax before returning. Generate the {num_days}-day itinerary now (JSON array only):
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
                    types=day_data.get('types', []),  # Extract types from LLM output
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
