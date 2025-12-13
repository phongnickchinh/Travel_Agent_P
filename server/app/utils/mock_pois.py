"""
Mock POI Dataset - Da Nang
============================

Purpose:
- Provide 20+ Da Nang POIs for Week 4 testing
- Use in LangChain prompts for itinerary generation
- Match MongoDB POI schema structure

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

from typing import List, Dict, Any


MOCK_POIS_DA_NANG: List[Dict[str, Any]] = [
    # BEACH & COASTAL
    {
        "poi_id": "poi_my_khe_beach",
        "name": "Mỹ Khê Beach",
        "name_en": "My Khe Beach",
        "categories": ["beach", "outdoor"],
        "description": "One of the most beautiful beaches in the world, perfect for swimming and water sports. 30km white sand coastline.",
        "location": {"type": "Point", "coordinates": [108.2479, 16.0544]},
        "price_level": "free",
        "rating": 4.6,
        "user_ratings_total": 15234,
        "opening_hours": "Open 24 hours",
        "estimated_duration_minutes": 120
    },
    {
        "poi_id": "poi_non_nuoc_beach",
        "name": "Bãi Biển Non Nước",
        "name_en": "Non Nuoc Beach",
        "categories": ["beach", "outdoor"],
        "description": "Tranquil beach near Marble Mountains, less crowded than My Khe. Great for sunrise viewing.",
        "location": {"type": "Point", "coordinates": [108.2635, 16.0012]},
        "price_level": "free",
        "rating": 4.5,
        "user_ratings_total": 8921,
        "opening_hours": "Open 24 hours",
        "estimated_duration_minutes": 90
    },
    
    # CULTURAL & TEMPLES
    {
        "poi_id": "poi_linh_ung_pagoda",
        "name": "Chùa Linh Ứng",
        "name_en": "Linh Ung Pagoda",
        "categories": ["temple", "cultural", "landmark"],
        "description": "Famous pagoda on Son Tra Peninsula with 67m tall Lady Buddha statue. Stunning ocean views.",
        "location": {"type": "Point", "coordinates": [108.2793, 16.1089]},
        "price_level": "free",
        "rating": 4.7,
        "user_ratings_total": 12456,
        "opening_hours": "5:00 AM - 9:00 PM",
        "estimated_duration_minutes": 60
    },
    {
        "poi_id": "poi_marble_mountains",
        "name": "Ngũ Hành Sơn",
        "name_en": "Marble Mountains",
        "categories": ["cultural", "landmark", "outdoor"],
        "description": "Five marble hills with caves, tunnels, Buddhist sanctuaries, and panoramic city views.",
        "location": {"type": "Point", "coordinates": [108.2626, 16.0050]},
        "price_level": "inexpensive",
        "rating": 4.5,
        "user_ratings_total": 18732,
        "opening_hours": "7:00 AM - 5:30 PM",
        "estimated_duration_minutes": 120
    },
    
    # BRIDGES & LANDMARKS
    {
        "poi_id": "poi_dragon_bridge",
        "name": "Cầu Rồng",
        "name_en": "Dragon Bridge",
        "categories": ["landmark", "attraction"],
        "description": "Iconic dragon-shaped bridge that breathes fire and water on weekend nights (9pm Sat/Sun).",
        "location": {"type": "Point", "coordinates": [108.2272, 16.0614]},
        "price_level": "free",
        "rating": 4.6,
        "user_ratings_total": 22341,
        "opening_hours": "Open 24 hours (fire show: 9 PM Sat/Sun)",
        "estimated_duration_minutes": 30
    },
    {
        "poi_id": "poi_love_bridge",
        "name": "Cầu Tình Yêu",
        "name_en": "Love Bridge (Trần Thị Lý Bridge)",
        "categories": ["landmark", "attraction"],
        "description": "Sail-shaped bridge beautifully lit at night, popular romantic spot.",
        "location": {"type": "Point", "coordinates": [108.2194, 16.0397]},
        "price_level": "free",
        "rating": 4.4,
        "user_ratings_total": 9821,
        "opening_hours": "Open 24 hours",
        "estimated_duration_minutes": 20
    },
    
    # NATURE & OUTDOOR
    {
        "poi_id": "poi_son_tra_peninsula",
        "name": "Bán Đảo Sơn Trà",
        "name_en": "Son Tra Peninsula",
        "categories": ["outdoor", "nature", "hiking"],
        "description": "Jungle-clad peninsula with rare red-shanked douc langurs, pristine beaches, and hiking trails.",
        "location": {"type": "Point", "coordinates": [108.2841, 16.1126]},
        "price_level": "free",
        "rating": 4.7,
        "user_ratings_total": 11234,
        "opening_hours": "6:00 AM - 6:00 PM",
        "estimated_duration_minutes": 180
    },
    {
        "poi_id": "poi_ba_na_hills",
        "name": "Bà Nà Hills",
        "name_en": "Ba Na Hills",
        "categories": ["attraction", "outdoor", "landmark"],
        "description": "Mountain resort with Golden Bridge, cable car (world record), French village, and amusement park.",
        "location": {"type": "Point", "coordinates": [107.9972, 15.9964]},
        "price_level": "expensive",
        "rating": 4.5,
        "user_ratings_total": 34521,
        "opening_hours": "7:00 AM - 10:00 PM",
        "estimated_duration_minutes": 360
    },
    
    # MUSEUMS & CULTURE
    {
        "poi_id": "poi_cham_museum",
        "name": "Bảo Tàng Điêu Khắc Chăm",
        "name_en": "Museum of Cham Sculpture",
        "categories": ["museum", "cultural"],
        "description": "World's largest collection of Cham artifacts (7th-15th century). UNESCO-recognized.",
        "location": {"type": "Point", "coordinates": [108.2220, 16.0617]},
        "price_level": "inexpensive",
        "rating": 4.3,
        "user_ratings_total": 6543,
        "opening_hours": "7:00 AM - 5:00 PM",
        "estimated_duration_minutes": 90
    },
    {
        "poi_id": "poi_da_nang_museum",
        "name": "Bảo Tàng Đà Nẵng",
        "name_en": "Da Nang Museum",
        "categories": ["museum", "cultural"],
        "description": "City history museum with exhibits on Sa Huynh culture, Vietnam War, and local heritage.",
        "location": {"type": "Point", "coordinates": [108.2191, 16.0677]},
        "price_level": "free",
        "rating": 4.1,
        "user_ratings_total": 3421,
        "opening_hours": "8:00 AM - 5:00 PM (Closed Mondays)",
        "estimated_duration_minutes": 75
    },
    
    # MARKETS & SHOPPING
    {
        "poi_id": "poi_han_market",
        "name": "Chợ Hàn",
        "name_en": "Han Market",
        "categories": ["shopping", "food"],
        "description": "Bustling central market with local food, souvenirs, clothing. Great for street food.",
        "location": {"type": "Point", "coordinates": [108.2205, 16.0686]},
        "price_level": "inexpensive",
        "rating": 4.2,
        "user_ratings_total": 8932,
        "opening_hours": "6:00 AM - 7:00 PM",
        "estimated_duration_minutes": 90
    },
    {
        "poi_id": "poi_con_market",
        "name": "Chợ Cồn",
        "name_en": "Con Market",
        "categories": ["shopping", "food"],
        "description": "Local wholesale market, authentic Vietnamese experience. Famous for banh trang rice paper.",
        "location": {"type": "Point", "coordinates": [108.2143, 16.0745]},
        "price_level": "inexpensive",
        "rating": 4.0,
        "user_ratings_total": 4231,
        "opening_hours": "5:00 AM - 6:00 PM",
        "estimated_duration_minutes": 60
    },
    
    # FOOD & DINING
    {
        "poi_id": "poi_banh_mi_ba_lan",
        "name": "Bánh Mì Bà Lan",
        "name_en": "Ba Lan Banh Mi",
        "categories": ["restaurant", "food"],
        "description": "Legendary banh mi shop, open since 1979. Must-try Vietnamese sandwich.",
        "location": {"type": "Point", "coordinates": [108.2198, 16.0721]},
        "price_level": "inexpensive",
        "rating": 4.6,
        "user_ratings_total": 7821,
        "opening_hours": "6:00 AM - 10:00 PM",
        "estimated_duration_minutes": 30
    },
    {
        "poi_id": "poi_mi_quang_ba_mua",
        "name": "Mì Quảng Bà Mua",
        "name_en": "Ba Mua Mi Quang",
        "categories": ["restaurant", "food"],
        "description": "Authentic Mi Quang (turmeric noodles), Da Nang signature dish. Local favorite.",
        "location": {"type": "Point", "coordinates": [108.2156, 16.0689]},
        "price_level": "inexpensive",
        "rating": 4.5,
        "user_ratings_total": 5632,
        "opening_hours": "6:00 AM - 9:00 PM",
        "estimated_duration_minutes": 45
    },
    
    # NIGHT ENTERTAINMENT
    {
        "poi_id": "poi_asia_park",
        "name": "Asia Park",
        "name_en": "Asia Park",
        "categories": ["attraction", "entertainment"],
        "description": "Amusement park with Sun Wheel (4th largest Ferris wheel in the world). Stunning night lights.",
        "location": {"type": "Point", "coordinates": [108.2277, 16.0398]},
        "price_level": "moderate",
        "rating": 4.3,
        "user_ratings_total": 12341,
        "opening_hours": "3:00 PM - 10:00 PM",
        "estimated_duration_minutes": 180
    },
    {
        "poi_id": "poi_helio_center",
        "name": "Helio Center",
        "name_en": "Helio Night Market",
        "categories": ["shopping", "food", "entertainment"],
        "description": "Rooftop night market with food court, shopping, and entertainment. Modern vibe.",
        "location": {"type": "Point", "coordinates": [108.2248, 16.0632]},
        "price_level": "moderate",
        "rating": 4.2,
        "user_ratings_total": 6543,
        "opening_hours": "5:00 PM - 11:00 PM",
        "estimated_duration_minutes": 120
    },
    
    # UNIQUE EXPERIENCES
    {
        "poi_id": "poi_golden_bridge",
        "name": "Cầu Vàng",
        "name_en": "Golden Bridge (at Ba Na Hills)",
        "categories": ["landmark", "attraction"],
        "description": "Instagram-famous bridge held by giant stone hands. 1,400m above sea level.",
        "location": {"type": "Point", "coordinates": [107.9981, 15.9956]},
        "price_level": "expensive",
        "rating": 4.8,
        "user_ratings_total": 28932,
        "opening_hours": "7:00 AM - 10:00 PM (within Ba Na Hills)",
        "estimated_duration_minutes": 60
    },
    {
        "poi_id": "poi_han_river_cruise",
        "name": "Du Thuyền Sông Hàn",
        "name_en": "Han River Night Cruise",
        "categories": ["attraction", "entertainment"],
        "description": "Evening cruise under illuminated bridges with live music and dinner options.",
        "location": {"type": "Point", "coordinates": [108.2242, 16.0638]},
        "price_level": "moderate",
        "rating": 4.4,
        "user_ratings_total": 9821,
        "opening_hours": "6:00 PM - 10:00 PM",
        "estimated_duration_minutes": 90
    },
    
    # SPIRITUAL & RELIGIOUS
    {
        "poi_id": "poi_phap_lam_pagoda",
        "name": "Chùa Pháp Lâm",
        "name_en": "Phap Lam Pagoda",
        "categories": ["temple", "cultural"],
        "description": "Historic pagoda in city center, peaceful atmosphere. Important Buddhist site.",
        "location": {"type": "Point", "coordinates": [108.2217, 16.0653]},
        "price_level": "free",
        "rating": 4.3,
        "user_ratings_total": 4521,
        "opening_hours": "5:00 AM - 9:00 PM",
        "estimated_duration_minutes": 45
    },
    {
        "poi_id": "poi_cao_dai_temple",
        "name": "Thánh Thất Cao Đài",
        "name_en": "Cao Dai Temple",
        "categories": ["temple", "cultural"],
        "description": "Colorful Cao Dai temple, unique Vietnamese religion blending Buddhism, Taoism, and Christianity.",
        "location": {"type": "Point", "coordinates": [108.2189, 16.0712]},
        "price_level": "free",
        "rating": 4.2,
        "user_ratings_total": 3211,
        "opening_hours": "6:00 AM - 6:00 PM",
        "estimated_duration_minutes": 40
    }
]


def get_mock_pois_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Filter POIs by category.
    
    Args:
        category: Category name (e.g., "beach", "food", "cultural")
        
    Returns:
        List of matching POIs
    """
    return [poi for poi in MOCK_POIS_DA_NANG if category in poi.get('categories', [])]


def get_mock_poi_names() -> List[str]:
    """
    Get all POI names for LangChain context.
    
    Returns:
        List of POI names (English + Vietnamese)
    """
    names = []
    for poi in MOCK_POIS_DA_NANG:
        names.append(f"{poi['name']} ({poi['name_en']})")
    return names


def get_mock_poi_summary() -> str:
    """
    Generate formatted POI summary for LLM prompt.
    
    Returns:
        Multi-line string with POI details
    """
    lines = ["Available POIs in Da Nang:"]
    lines.append("=" * 60)
    
    for poi in MOCK_POIS_DA_NANG:
        categories_str = ", ".join(poi['categories'])
        duration = poi['estimated_duration_minutes']
        
        line = (
            f"- {poi['name']} ({poi['name_en']})\n"
            f"  ID: {poi['poi_id']}\n"
            f"  Categories: {categories_str}\n"
            f"  Description: {poi['description']}\n"
            f"  Duration: {duration} min | Price: {poi['price_level']} | Rating: {poi['rating']}/5\n"
        )
        lines.append(line)
    
    return "\n".join(lines)


# Export for easy import
__all__ = [
    'MOCK_POIS_DA_NANG',
    'get_mock_pois_by_category',
    'get_mock_poi_names',
    'get_mock_poi_summary'
]
