"""
Test Merge Small Clusters Implementation
"""
import sys
sys.path.insert(0, 'p:\\coddd\\Travel_Agent_P\\server')

from typing import List, Dict, Any, Optional
import logging
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def _cluster_pois_by_location(
    pois: List[Dict[str, Any]], 
    radius_km: float = 2.0,
    target_clusters: Optional[int] = None
) -> Dict[int, List[Dict]]:
    """BFS clustering + merge logic (copied from planner_service.py)"""
    if not pois:
        return {}
    
    # Build POI nodes with coordinates
    poi_nodes = []
    for i, poi in enumerate(pois):
        location = poi.get('location', {})
        if isinstance(location, dict):
            if 'coordinates' in location:  # GeoJSON format
                lng, lat = location['coordinates']
            else:
                lat = location.get('latitude', location.get('lat'))
                lng = location.get('longitude', location.get('lng'))
        else:
            continue
        
        poi_nodes.append({
            'index': i,
            'poi': poi,
            'lat': lat,
            'lng': lng,
            'cluster': -1
        })
    
    if not poi_nodes:
        return {1: pois}
    
    # Build adjacency list
    adjacency = {i: [] for i in range(len(poi_nodes))}
    degree_per_km = 1 / 111.0
    radius_deg = radius_km * degree_per_km
    
    for i in range(len(poi_nodes)):
        for j in range(i + 1, len(poi_nodes)):
            lat_diff = poi_nodes[i]['lat'] - poi_nodes[j]['lat']
            lng_diff = poi_nodes[i]['lng'] - poi_nodes[j]['lng']
            distance_deg = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
            
            if distance_deg <= radius_deg:
                adjacency[i].append(j)
                adjacency[j].append(i)
    
    # BFS clustering
    cluster_id = 0
    for i in range(len(poi_nodes)):
        if poi_nodes[i]['cluster'] != -1:
            continue
        
        cluster_id += 1
        queue = deque([i])
        poi_nodes[i]['cluster'] = cluster_id
        visited = {i}
        
        while queue:
            current_idx = queue.popleft()
            for neighbor_idx in adjacency[current_idx]:
                if neighbor_idx in visited:
                    continue
                
                poi_nodes[neighbor_idx]['cluster'] = cluster_id
                queue.append(neighbor_idx)
                visited.add(neighbor_idx)
    
    # Group POIs by cluster
    clusters = {}
    for node in poi_nodes:
        cid = node['cluster']
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(node['poi'])
    
    logger.info(f"[CLUSTERING] BFS created {len(clusters)} clusters from {len(pois)} POIs (radius={radius_km}km)")
    
    # Merge small clusters if target_clusters specified
    if target_clusters and len(clusters) > target_clusters:
        logger.info(f"[MERGE] Merging {len(clusters)} clusters down to {target_clusters} target clusters")
        clusters = _merge_small_clusters(clusters, poi_nodes, target_clusters)
    
    return clusters


def _merge_small_clusters(
    clusters: Dict[int, List[Dict]], 
    poi_nodes: List[Dict],
    target_clusters: int
) -> Dict[int, List[Dict]]:
    """Merge smallest cluster with nearest cluster"""
    def calculate_center(cluster_pois):
        lats = []
        lngs = []
        for poi in cluster_pois:
            loc = poi.get('location', {})
            if 'coordinates' in loc:
                lng, lat = loc['coordinates']
            else:
                lat = loc.get('latitude', loc.get('lat'))
                lng = loc.get('longitude', loc.get('lng'))
            lats.append(lat)
            lngs.append(lng)
        return (sum(lats) / len(lats), sum(lngs) / len(lngs))
    
    while len(clusters) > target_clusters:
        smallest_id = min(clusters.keys(), key=lambda cid: len(clusters[cid]))
        smallest_cluster = clusters[smallest_id]
        
        if len(clusters) == 1:
            break
        
        smallest_center = calculate_center(smallest_cluster)
        
        min_distance = float('inf')
        nearest_id = None
        
        for cluster_id, cluster_pois in clusters.items():
            if cluster_id == smallest_id:
                continue
            
            candidate_center = calculate_center(cluster_pois)
            distance = (
                (smallest_center[0] - candidate_center[0]) ** 2 +
                (smallest_center[1] - candidate_center[1]) ** 2
            ) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest_id = cluster_id
        
        if nearest_id is None:
            break
        
        clusters[nearest_id].extend(smallest_cluster)
        del clusters[smallest_id]
        
        logger.info(
            f"[MERGE] Merged cluster {smallest_id} ({len(smallest_cluster)} POIs) "
            f"into cluster {nearest_id} (distance={min_distance*111:.2f}km). "
            f"Remaining: {len(clusters)} clusters"
        )
    
    # Re-index
    sorted_ids = sorted(clusters.keys())
    reindexed = {i+1: clusters[old_id] for i, old_id in enumerate(sorted_ids)}
    
    logger.info(f"[MERGE] Final: {len(reindexed)} balanced clusters")
    return reindexed


# Test cases
def test_merge_clusters():
    print("\n" + "="*60)
    print("TEST: Merge Small Clusters (29 POIs → 5 clusters)")
    print("="*60 + "\n")
    
    # Create 29 test POIs in a VERY SPARSE grid (ensure multiple clusters)
    # 0.03 degree ≈ 3.3km spacing → with radius=2km, each POI is its own cluster
    test_pois = []
    for i in range(29):
        test_pois.append({
            'name': f'POI {i+1}',
            'poi_id': f'poi_{i+1}',
            'location': {
                # Grid: 6 columns x 5 rows
                'coordinates': [108.2428 + (i % 6) * 0.03, 16.0544 + (i // 6) * 0.03]
            }
        })
    
    # Test 1: No target (natural BFS clustering with SMALL radius)
    print("\n--- Test 1: Natural BFS with radius=2km (creates many clusters) ---")
    clusters = _cluster_pois_by_location(test_pois, radius_km=2.0, target_clusters=None)
    print(f"✅ Created {len(clusters)} clusters naturally")
    print(f"   Sizes: {sorted([len(c) for c in clusters.values()], reverse=True)}\n")
    
    # Test 2: Target 5 clusters (merge required)
    print("\n--- Test 2: Target 5 clusters (with merging from many small clusters) ---")
    clusters = _cluster_pois_by_location(test_pois, radius_km=2.0, target_clusters=5)
    print(f"✅ Merged to {len(clusters)} clusters (target: 5)")
    print(f"   Sizes: {sorted([len(c) for c in clusters.values()], reverse=True)}")
    print(f"   Total POIs preserved: {sum(len(c) for c in clusters.values())}/29\n")
    
    # Verify no data loss
    total_pois = sum(len(c) for c in clusters.values())
    assert total_pois == 29, f"❌ Data loss! {total_pois}/29 POIs"
    assert len(clusters) == 5, f"❌ Wrong cluster count! {len(clusters)}/5"
    
    print("="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    
    # Show cluster distribution
    print("\n📊 CLUSTER BREAKDOWN:")
    for cid, cpois in sorted(clusters.items()):
        print(f"   Cluster {cid}: {len(cpois)} POIs - {[p['name'] for p in cpois[:3]]}...")


if __name__ == '__main__':
    test_merge_clusters()
