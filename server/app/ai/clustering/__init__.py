"""
Clustering Sub-package
======================

Machine Learning-based POI clustering algorithms.

Algorithms:
- HDBSCAN: Recommended, auto-detects clusters
- DBSCAN: Density-based clustering
- K-Means: Classic clustering

Author: Travel Agent P Team
"""

from .clustering_ml import POIClustering, ML_CLUSTERING_AVAILABLE

__all__ = [
    "POIClustering",
    "ML_CLUSTERING_AVAILABLE",
]
