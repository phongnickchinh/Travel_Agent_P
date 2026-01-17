"""
POI Clustering with HDBSCAN (Machine Learning)
==============================================

Replaces BFS clustering with ML-based HDBSCAN for better performance and quality.

Advantages over BFS:
- O(n log n) vs O(n²) time complexity
- Auto-detects optimal cluster count
- Handles variable density (city center vs suburbs)
- Detects noise/outlier POIs
- Uses accurate Haversine distance

Dependencies:
    pip install hdbscan scikit-learn

Author: Travel Agent P Team
Date: January 6, 2026
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Optional: Only import if ML clustering is enabled
try:
    import hdbscan
    from sklearn.cluster import DBSCAN, KMeans
    ML_CLUSTERING_AVAILABLE = True
except ImportError:
    logger.warning("[CLUSTERING] hdbscan/sklearn not installed. ML clustering unavailable.")
    ML_CLUSTERING_AVAILABLE = False


class POIClustering:
    """
    POI Clustering with multiple algorithms (HDBSCAN, DBSCAN, K-Means).
    
    Recommended: HDBSCAN for best quality/performance balance.
    """
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate great-circle distance between two points on Earth.
        
        More accurate than Euclidean distance for geographic coordinates.
        
        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Earth radius in km
        R = 6371.0
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def extract_coordinates(pois: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[int]]:
        """
        Extract valid coordinates from POIs.
        
        Args:
            pois: List of POI dicts with location data
            
        Returns:
            Tuple of (coordinates_array, valid_indices)
            - coordinates_array: numpy array of shape (n, 2) with [lat, lng]
            - valid_indices: List of indices in original pois list
        """
        coords = []
        valid_indices = []
        
        for i, poi in enumerate(pois):
            location = poi.get('location', {})
            coords_raw = location.get('coordinates', [None, None])
            
            if isinstance(coords_raw, (list, tuple)) and len(coords_raw) >= 2:
                lng, lat = coords_raw[0], coords_raw[1]
                if isinstance(lng, (int, float)) and isinstance(lat, (int, float)):
                    coords.append([float(lat), float(lng)])  # [lat, lng] for ML
                    valid_indices.append(i)
        
        if not coords:
            logger.warning("[CLUSTERING] No valid coordinates found in POIs")
            return np.array([]), []
        
        return np.array(coords), valid_indices
    
    @staticmethod
    def cluster_hdbscan(
        pois: List[Dict[str, Any]],
        min_cluster_size: int = 3,
        min_samples: int = 2,
        max_clusters: Optional[int] = None,
        metric: str = 'haversine',
        assign_noise_to_nearest: bool = True
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Cluster POIs using HDBSCAN (Hierarchical DBSCAN).
        
        Best for: Variable density, auto cluster count, noise detection
        
        Args:
            pois: List of POI dicts
            min_cluster_size: Minimum POIs per cluster (default: 3)
            min_samples: Min neighbors to be core point (default: 2)
            max_clusters: Optional max clusters (will extract from hierarchy)
            metric: Distance metric ('haversine' for lat/lng, 'euclidean' for projected)
            assign_noise_to_nearest: If True, assign noise POIs to nearest cluster (default: True)
                                     Important for travel: distant attractions shouldn't be discarded!
            
        Returns:
            Dict of {cluster_id: [POI list]}
            If assign_noise_to_nearest=True: All POIs assigned to clusters (no -1)
            If assign_noise_to_nearest=False: Cluster -1 contains noise/outliers
        """
        if not ML_CLUSTERING_AVAILABLE:
            logger.error("[HDBSCAN] hdbscan not installed. Install: pip install hdbscan")
            return {}
        
        # Extract coordinates
        coords, valid_indices = POIClustering.extract_coordinates(pois)
        
        if len(coords) == 0:
            logger.warning("[HDBSCAN] No valid coordinates, returning empty clusters")
            return {}
        
        # Convert lat/lng to radians if using haversine
        if metric == 'haversine':
            coords_rad = np.radians(coords)
        else:
            coords_rad = coords
        
        # Run HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric=metric,
            cluster_selection_method='eom',  # Excess of Mass (better quality)
            allow_single_cluster=False
        )
        
        cluster_labels = clusterer.fit_predict(coords_rad)
        
        # Get cluster strengths (for quality assessment)
        probabilities = clusterer.probabilities_
        
        # Log clustering stats
        unique_labels = set(cluster_labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        logger.info(
            f"[HDBSCAN] Found {n_clusters} clusters from {len(pois)} POIs "
            f"(noise: {n_noise}, avg_prob: {probabilities.mean():.2f})"
        )
        
        # If max_clusters specified and we have too many, merge small clusters
        if max_clusters and n_clusters > max_clusters:
            cluster_labels = POIClustering._reduce_clusters_hdbscan(
                cluster_labels, coords, max_clusters
            )
            n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
            logger.info(f"[HDBSCAN] Reduced to {n_clusters} clusters (target: {max_clusters})")
        
        # Group POIs by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            original_idx = valid_indices[i]
            poi = pois[original_idx]
            
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(poi)
        
        # Handle noise cluster (-1) for travel planning
        if -1 in clusters:
            noise_pois = clusters[-1]
            noise_count = len(noise_pois)
            logger.info(f"[HDBSCAN] {noise_count} noise POIs detected (outliers/distant attractions)")
            
            if assign_noise_to_nearest and noise_count > 0:
                # Assign each noise POI to nearest cluster (important for travel!)
                # Example: Bà Nà Hills (30km from Da Nang) shouldn't be discarded
                logger.info(f"[HDBSCAN] Assigning {noise_count} noise POIs to nearest clusters")
                clusters = POIClustering._assign_noise_to_clusters(
                    noise_pois, clusters, coords, valid_indices, metric
                )
                # Remove empty noise cluster
                clusters.pop(-1, None)
        
        return clusters
    
    @staticmethod
    def cluster_dbscan(
        pois: List[Dict[str, Any]],
        eps_km: float = 2.0,
        min_samples: int = 3
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Cluster POIs using DBSCAN (Density-Based Clustering).
        
        Good for: Fixed density, simple clustering
        Requires: Tuning eps (search radius)
        
        Args:
            pois: List of POI dicts
            eps_km: Search radius in kilometers (default: 2.0)
            min_samples: Min POIs to form cluster (default: 3)
            
        Returns:
            Dict of {cluster_id: [POI list]}
        """
        if not ML_CLUSTERING_AVAILABLE:
            logger.error("[DBSCAN] sklearn not installed")
            return {}
        
        coords, valid_indices = POIClustering.extract_coordinates(pois)
        
        if len(coords) == 0:
            return {}
        
        # Convert lat/lng to radians for haversine
        coords_rad = np.radians(coords)
        
        # DBSCAN with haversine metric
        # eps in radians: eps_km / Earth_radius_km
        eps_rad = eps_km / 6371.0
        
        clusterer = DBSCAN(eps=eps_rad, min_samples=min_samples, metric='haversine')
        cluster_labels = clusterer.fit_predict(coords_rad)
        
        # Group POIs
        clusters = {}
        for i, label in enumerate(cluster_labels):
            original_idx = valid_indices[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(pois[original_idx])
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        logger.info(f"[DBSCAN] Found {n_clusters} clusters (noise: {n_noise})")
        
        return clusters
    
    @staticmethod
    def cluster_kmeans(
        pois: List[Dict[str, Any]],
        n_clusters: int = 5
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Cluster POIs using K-Means.
        
        Good for: Fixed cluster count, balanced clusters
        Bad for: Variable density, outliers
        
        Args:
            pois: List of POI dicts
            n_clusters: Number of clusters (required)
            
        Returns:
            Dict of {cluster_id: [POI list]}
        """
        if not ML_CLUSTERING_AVAILABLE:
            logger.error("[K-MEANS] sklearn not installed")
            return {}
        
        coords, valid_indices = POIClustering.extract_coordinates(pois)
        
        if len(coords) == 0:
            return {}
        
        # K-Means (no haversine support, use euclidean on lat/lng)
        # Note: Less accurate for geographic data
        clusterer = KMeans(n_clusters=min(n_clusters, len(coords)), random_state=42)
        cluster_labels = clusterer.fit_predict(coords)
        
        # Group POIs
        clusters = {}
        for i, label in enumerate(cluster_labels):
            original_idx = valid_indices[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(pois[original_idx])
        
        logger.info(f"[K-MEANS] Created {n_clusters} clusters")
        
        return clusters
    
    @staticmethod
    def _reduce_clusters_hdbscan(
        cluster_labels: np.ndarray,
        coords: np.ndarray,
        target_clusters: int
    ) -> np.ndarray:
        """
        Reduce number of clusters by merging smallest clusters.
        
        Similar to _merge_small_clusters but optimized for HDBSCAN output.
        
        Args:
            cluster_labels: Array of cluster labels
            coords: Array of coordinates [lat, lng]
            target_clusters: Target number of clusters
            
        Returns:
            Updated cluster_labels array
        """
        unique_labels = set(cluster_labels)
        unique_labels.discard(-1)  # Ignore noise
        
        while len(unique_labels) > target_clusters:
            # Find smallest cluster
            cluster_sizes = {label: np.sum(cluster_labels == label) for label in unique_labels}
            smallest_label = min(cluster_sizes, key=cluster_sizes.get)
            
            # Find center of smallest cluster
            smallest_mask = cluster_labels == smallest_label
            smallest_center = coords[smallest_mask].mean(axis=0)
            
            # Find nearest cluster
            min_distance = float('inf')
            nearest_label = None
            
            for label in unique_labels:
                if label == smallest_label:
                    continue
                
                cluster_mask = cluster_labels == label
                cluster_center = coords[cluster_mask].mean(axis=0)
                
                distance = np.linalg.norm(smallest_center - cluster_center)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_label = label
            
            if nearest_label is None:
                break
            
            # Merge smallest into nearest
            cluster_labels[cluster_labels == smallest_label] = nearest_label
            unique_labels.remove(smallest_label)
        
        return cluster_labels
    
    @staticmethod
    def _assign_noise_to_clusters(
        noise_pois: List[Dict[str, Any]],
        clusters: Dict[int, List[Dict]],
        all_coords: np.ndarray,
        valid_indices: List[int],
        metric: str = 'haversine'
    ) -> Dict[int, List[Dict]]:
        """
        Assign noise/outlier POIs to their nearest cluster.
        
        CRITICAL for travel planning:
        Distant attractions (e.g., Bà Nà Hills 30km from Da Nang, Hội An Ancient Town)
        should NOT be discarded - they're often the MAIN destinations!
        
        Args:
            noise_pois: List of POIs labeled as noise (-1)
            clusters: Existing clusters Dict[cluster_id, List[POI]]
            all_coords: Full coordinate array (n x 2) [lat, lng]
            valid_indices: Mapping of cluster indices to original POI indices
            metric: Distance metric (haversine/euclidean)
            
        Returns:
            Updated clusters with noise POIs assigned to nearest cluster
        """
        if not noise_pois or not clusters or len(clusters) == 0:
            logger.warning("[NOISE] Cannot assign noise - no valid clusters")
            return clusters
        
        # Remove -1 cluster from valid clusters
        valid_clusters = {k: v for k, v in clusters.items() if k != -1}
        if not valid_clusters:
            logger.warning("[NOISE] No non-noise clusters to assign to")
            return clusters
        
        # Calculate cluster centers using valid POIs
        cluster_centers = {}
        for cluster_id, cluster_pois in valid_clusters.items():
            center_lat, center_lng = POIClustering.calculate_cluster_center(cluster_pois)
            cluster_centers[cluster_id] = np.array([center_lat, center_lng])
        
        logger.info(f"[NOISE] Assigning {len(noise_pois)} noise POIs to {len(cluster_centers)} clusters")
        
        # Assign each noise POI to nearest cluster
        for poi in noise_pois:
            location = poi.get('location', {})
            coords_raw = location.get('coordinates', [None, None])
            
            if not isinstance(coords_raw, (list, tuple)) or len(coords_raw) < 2:
                logger.warning(f"[NOISE] Invalid location for POI: {poi.get('name', 'Unknown')}")
                continue
            
            lng, lat = coords_raw[0], coords_raw[1]
            if lat is None or lng is None:
                continue
            
            poi_coords = np.array([float(lat), float(lng)])
            
            # Find nearest cluster
            min_distance = float('inf')
            nearest_cluster_id = None
            
            for cluster_id, center_coords in cluster_centers.items():
                if metric == 'haversine':
                    # Use Haversine distance for lat/lng
                    distance = POIClustering.haversine_distance(
                        poi_coords[0], poi_coords[1],
                        center_coords[0], center_coords[1]
                    )
                else:
                    # Euclidean distance
                    distance = np.linalg.norm(poi_coords - center_coords)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_cluster_id = cluster_id
            
            # Assign to nearest cluster
            if nearest_cluster_id is not None:
                clusters[nearest_cluster_id].append(poi)
                poi_name = poi.get('name', 'Unknown')
                logger.info(
                    f"[NOISE] '{poi_name}' assigned to cluster {nearest_cluster_id} "
                    f"(distance: {min_distance:.2f}km)"
                )
        
        return clusters
    
    @staticmethod
    def calculate_cluster_center(cluster_pois: List[Dict[str, Any]]) -> Tuple[float, float]:
        """
        Calculate geographic center of a cluster.
        
        Args:
            cluster_pois: List of POIs in cluster
            
        Returns:
            Tuple (lat, lng)
        """
        valid_coords = []
        for poi in cluster_pois:
            location = poi.get('location', {})
            coords = location.get('coordinates', [])
            if len(coords) >= 2 and coords[0] is not None:
                valid_coords.append((coords[1], coords[0]))  # (lat, lng)
        
        if not valid_coords:
            return (0.0, 0.0)
        
        avg_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
        avg_lng = sum(c[1] for c in valid_coords) / len(valid_coords)
        
        return (avg_lat, avg_lng)


# ============================================
# PUBLIC API
# ============================================

def cluster_pois_ml(
    pois: List[Dict[str, Any]],
    algorithm: str = 'hdbscan',
    min_cluster_size: int = 3,
    max_clusters: Optional[int] = None,
    assign_noise_to_nearest: bool = True,
    **kwargs
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Cluster POIs using ML algorithms.
    
    Args:
        pois: List of POI dicts with location data
        algorithm: 'hdbscan' (recommended), 'dbscan', or 'kmeans'
        min_cluster_size: Minimum POIs per cluster (HDBSCAN/DBSCAN)
        max_clusters: Optional target cluster count (HDBSCAN/K-Means)
        assign_noise_to_nearest: If True, assign outlier POIs to nearest cluster (default: True)
                                 Recommended for travel planning - distant attractions should be included!
        **kwargs: Algorithm-specific parameters
        
    Returns:
        Dict of {cluster_id: [POI list]}
        
    Example:
        >>> clusters = cluster_pois_ml(pois, algorithm='hdbscan', max_clusters=5)
        >>> for cluster_id, cluster_pois in clusters.items():
        ...     print(f"Cluster {cluster_id}: {len(cluster_pois)} POIs")
    """
    if algorithm == 'hdbscan':
        return POIClustering.cluster_hdbscan(
            pois, 
            min_cluster_size=min_cluster_size,
            max_clusters=max_clusters,
            assign_noise_to_nearest=assign_noise_to_nearest,
            **kwargs
        )
    elif algorithm == 'dbscan':
        eps_km = kwargs.get('eps_km', 2.0)
        return POIClustering.cluster_dbscan(
            pois, 
            eps_km=eps_km,
            min_samples=min_cluster_size
        )
    elif algorithm == 'kmeans':
        if max_clusters is None:
            max_clusters = 5
        return POIClustering.cluster_kmeans(pois, n_clusters=max_clusters)
    else:
        logger.error(f"[CLUSTERING] Unknown algorithm: {algorithm}")
        return {}
