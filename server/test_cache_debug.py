"""
Test script to debug Google data caching to MongoDB.

Run this to verify:
1. Destination caching (PlaceDetail collection)
2. POI caching (poi collection)
"""

import logging
import sys
from pprint import pprint

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add server to path
sys.path.insert(0, 'p:/coddd/Travel_Agent_P/server')

from app.service.planner_service import PlannerService
from app.providers.places.google_places_provider import GooglePlacesProvider
from app.repo.mongo.place_detail_repository import PlaceDetailRepository
from app.repo.mongo.poi_repository import POIRepository

logger = logging.getLogger(__name__)

def test_destination_cache():
    """Test destination caching to place_details collection."""
    print("\n" + "="*80)
    print("TEST 1: Destination Caching")
    print("="*80)
    
    planner = PlannerService()
    
    # Test place_id (Da Nang)
    test_place_id = "ChIJoRyG2RwZQjERWLj1Xw8e9HE"
    
    print(f"\n1. Testing destination resolution: {test_place_id}")
    result = planner._resolve_destination(test_place_id)
    
    if result:
        print("\n✓ Destination resolved successfully:")
        print(f"  - Name: {result.get('name')}")
        print(f"  - Location: {result.get('location')}")
        print(f"  - Place ID: {result.get('place_id')}")
        
        # Check if cached in MongoDB
        place_detail_repo = PlaceDetailRepository()
        cached = place_detail_repo.get_by_place_id(test_place_id)
        if cached:
            print("\n✓ Destination found in MongoDB cache!")
            print(f"  - Cached name: {cached.get('name')}")
        else:
            print("\n✗ Destination NOT found in MongoDB cache!")
    else:
        print("\n✗ Destination resolution failed!")

def test_poi_cache():
    """Test POI caching to poi collection."""
    print("\n" + "="*80)
    print("TEST 2: POI Caching")
    print("="*80)
    
    planner = PlannerService()
    google_provider = GooglePlacesProvider()
    
    # Test location (Da Nang)
    location = {
        'latitude': 16.0544,
        'longitude': 108.2428
    }
    
    print(f"\n1. Searching POIs near Da Nang...")
    
    # Search Google API
    try:
        pois = google_provider.nearby_search(
            location=location,
            radius=5000,  # 5km
            types=['restaurant'],
            max_results=5
        )
        
        print(f"\n✓ Found {len(pois)} POIs from Google API")
        
        if pois:
            # Test caching first POI
            test_poi = pois[0]
            print(f"\n2. Testing POI cache for: {test_poi.get('name')}")
            print(f"   - POI ID: {test_poi.get('poi_id')}")
            print(f"   - Keys: {list(test_poi.keys())[:10]}...")
            
            # Cache to MongoDB
            success = planner._cache_poi_to_mongodb(test_poi)
            
            if success:
                print("\n✓ POI cached successfully!")
                
                # Verify in MongoDB
                poi_repo = POIRepository()
                cached = poi_repo.get_by_id(test_poi.get('poi_id'))
                if cached:
                    print("✓ POI verified in MongoDB!")
                    print(f"  - Cached name: {cached.get('name')}")
                else:
                    print("✗ POI NOT found in MongoDB!")
            else:
                print("\n✗ POI cache failed!")
        else:
            print("\n✗ No POIs found from Google API")
            
    except Exception as e:
        print(f"\n✗ Error searching POIs: {e}")
        import traceback
        traceback.print_exc()

def test_full_workflow():
    """Test full workflow: create plan → fetch POIs → cache."""
    print("\n" + "="*80)
    print("TEST 3: Full Workflow (Create Plan)")
    print("="*80)
    
    planner = PlannerService()
    
    # Mock plan data
    plan = {
        'destination_place_id': 'ChIJoRyG2RwZQjERWLj1Xw8e9HE',  # Da Nang
        'destination': 'Da Nang',
        'destination_types': ['locality', 'political'],
        'preferences': {
            'interests': ['beach', 'food', 'culture']
        }
    }
    
    print("\n1. Fetching POIs for plan...")
    try:
        result = planner._fetch_pois_for_plan(plan, num_days=3)
        
        if result:
            poi_context, accommodation_context, poi_cache = result
            print(f"\n✓ POIs fetched successfully!")
            print(f"  - POI context length: {len(poi_context) if poi_context else 0}")
            print(f"  - Accommodation context length: {len(accommodation_context) if accommodation_context else 0}")
            print(f"  - POI cache count: {len(poi_cache)}")
            
            # Check MongoDB for cached POIs
            poi_repo = POIRepository()
            count = poi_repo.count()
            print(f"\n✓ Total POIs in MongoDB: {count}")
        else:
            print("\n✗ Failed to fetch POIs!")
            
    except Exception as e:
        print(f"\n✗ Error in workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("GOOGLE DATA CACHE DEBUG SCRIPT")
    print("="*80)
    
    # Run tests
    test_destination_cache()
    test_poi_cache()
    test_full_workflow()
    
    print("\n" + "="*80)
    print("TESTS COMPLETED")
    print("="*80)
