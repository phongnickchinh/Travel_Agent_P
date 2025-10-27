"""
MongoDB Connection Test Script
==============================

Run this to verify MongoDB connection and indexes.

Usage:
    python test_mongodb.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.mongodb_client import get_mongodb_client
from app.repo.poi_repository import POIRepository
from app.model.poi import (
    POI, GeoJSONLocation, Address, Description, 
    Ratings, Pricing, POIMetadata,
    CategoryEnum, PriceLevelEnum, DataProviderEnum, DataSource
)
from datetime import datetime


def test_mongodb_connection():
    """Test MongoDB connection."""
    print("=" * 60)
    print("🧪 Testing MongoDB Connection")
    print("=" * 60)
    
    try:
        client = get_mongodb_client()
        
        # Check health
        is_healthy = client.is_healthy()
        print(f"✅ MongoDB Health: {'Healthy' if is_healthy else 'Unhealthy'}")
        
        if is_healthy:
            db = client.get_database()
            print(f"✅ Database: {db.name}")
            
            # List collections
            collections = db.list_collection_names()
            print(f"✅ Collections: {collections}")
            
            # Check POI collection
            poi_collection = client.get_collection("poi")
            poi_count = poi_collection.count_documents({})
            print(f"✅ POI Count: {poi_count}")
            
            # Check indexes
            indexes = list(poi_collection.list_indexes())
            print(f"✅ POI Indexes: {len(indexes)}")
            for idx in indexes:
                print(f"   - {idx['name']}: {list(idx.get('key', {}).keys())}")
            
            return True
        else:
            print("❌ MongoDB connection not healthy")
            return False
    
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False


def test_poi_repository():
    """Test POI repository."""
    print("\n" + "=" * 60)
    print("🧪 Testing POI Repository")
    print("=" * 60)
    
    try:
        repo = POIRepository()
        
        # Test count
        count = repo.count()
        print(f"✅ Total POI: {count}")
        
        # Test get popular
        popular = repo.get_popular(limit=5)
        print(f"✅ Popular POI: {len(popular)} found")
        
        return True
    
    except Exception as e:
        print(f"❌ POI repository test failed: {e}")
        return False


def test_create_sample_poi():
    """Test creating a sample POI."""
    print("\n" + "=" * 60)
    print("🧪 Testing POI Creation (Sample)")
    print("=" * 60)
    
    try:
        from app.utils.poi_dedupe import generate_dedupe_key
        
        # Create sample POI: My Khe Beach
        sample_poi = POI(
            poi_id="poi_test_mykhebeach",
            dedupe_key=generate_dedupe_key("Mỹ Khê Beach", 16.0544, 108.2428),
            name="Mỹ Khê Beach",
            name_unaccented="my khe beach",
            name_alternatives=[],
            location=GeoJSONLocation(
                type="Point",
                coordinates=[108.2428, 16.0544]  # [lng, lat]
            ),
            address=Address(
                street="Võ Nguyên Giáp",
                ward="Phước Mỹ",
                district="Sơn Trà",
                city="Đà Nẵng",
                country="Vietnam",
                full_address="Võ Nguyên Giáp, Phước Mỹ, Sơn Trà, Đà Nẵng"
            ),
            categories=[CategoryEnum.BEACH, CategoryEnum.NATURE],
            description=Description(
                short="One of the most beautiful beaches in Vietnam",
                long="Mỹ Khê Beach is a 20-mile stretch of white sand beach with clear blue water..."
            ),
            ratings=Ratings(
                average=4.7,
                count=15234
            ),
            pricing=Pricing(
                level=PriceLevelEnum.FREE
            ),
            sources=[
                DataSource(
                    provider=DataProviderEnum.MANUAL,
                    confidence=1.0
                )
            ],
            metadata=POIMetadata(
                verified=True,
                popularity_score=87.5
            )
        )
        
        print(f"✅ Sample POI created:")
        print(f"   - ID: {sample_poi.poi_id}")
        print(f"   - Name: {sample_poi.name}")
        print(f"   - Dedupe Key: {sample_poi.dedupe_key}")
        print(f"   - Location: {sample_poi.location.coordinates}")
        print(f"   - Categories: {sample_poi.categories}")
        
        # Try to insert (will fail if already exists)
        repo = POIRepository()
        
        # Check if exists
        existing = repo.get_by_id(sample_poi.poi_id)
        if existing:
            print(f"⚠️  POI already exists: {sample_poi.poi_id}")
            print(f"   Use this for testing: repo.get_by_id('{sample_poi.poi_id}')")
        else:
            print(f"ℹ️  POI ready to insert (uncomment repo.create() to test)")
            # Uncomment to actually insert:
            # result = repo.create(sample_poi)
            # print(f"✅ POI inserted: {result['poi_id']}")
        
        return True
    
    except Exception as e:
        print(f"❌ POI creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Starting MongoDB Tests...\n")
    
    # Test 1: Connection
    test1 = test_mongodb_connection()
    
    # Test 2: Repository
    test2 = test_poi_repository()
    
    # Test 3: Sample POI
    test3 = test_create_sample_poi()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"Connection Test: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Repository Test: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Sample POI Test: {'✅ PASS' if test3 else '❌ FAIL'}")
    print("=" * 60)
    
    if all([test1, test2, test3]):
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - check errors above")
        sys.exit(1)
