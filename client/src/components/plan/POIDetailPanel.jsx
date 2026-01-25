/**
 * POI Detail Panel - Slide-in panel from right side
 * 
 * Features:
 * - Slide-in animation from right
 * - Photo grid layout (1 large + 4 small)
 * - Tabs: Overview, Reviews, Location
 * - Save/Added to plan button
 * - Google Map in Location tab
 * 
 * Design based on: Travel app POI detail panel
 */

import { GoogleMap, Marker, useJsApiLoader } from '@react-google-maps/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Accessibility,
  ArrowLeft,
  Calendar,
  Car,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  ExternalLink,
  Globe,
  Grid3X3,
  Loader2,
  MapPin,
  Phone,
  Plus,
  Share2,
  Star,
  User,
  UtensilsCrossed,
  Wifi,
  X
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import searchAPI from '../../services/searchApi';

// Check if Google Photos API is enabled via environment variable
// Default: true (production), set VITE_ENABLE_GOOGLE_PHOTOS=false in dev to save costs
const ENABLE_GOOGLE_PHOTOS = import.meta.env.VITE_ENABLE_GOOGLE_PHOTOS !== 'false';
const PLACEHOLDER_IMAGE = 'https://placehold.co/800x600/e2e8f0/64748b?text=POI+Image';
const PLACEHOLDER_IMAGES = [
  'https://placehold.co/800x600/e2e8f0/64748b?text=Main+Photo',
  'https://placehold.co/400x400/f1f5f9/94a3b8?text=Photo+2',
  'https://placehold.co/400x400/f1f5f9/94a3b8?text=Photo+3',
  'https://placehold.co/400x400/f1f5f9/94a3b8?text=Photo+4',
  'https://placehold.co/400x400/f1f5f9/94a3b8?text=Photo+5',
];

// Format relative time for reviews
const formatRelativeTime = (publishTime, relativeTime) => {
  if (relativeTime) return relativeTime;
  if (!publishTime) return '';
  
  const date = new Date(publishTime);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays < 1) return 'Today';
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;
  return `${Math.floor(diffDays / 365)} year${Math.floor(diffDays / 365) > 1 ? 's' : ''} ago`;
};

// Star rating component
const StarRating = ({ rating, size = 'sm' }) => {
  const stars = [];
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;
  
  const starSize = size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-4 h-4' : 'w-5 h-5';
  
  for (let i = 0; i < 5; i++) {
    if (i < fullStars) {
      stars.push(<Star key={i} className={`${starSize} fill-amber-400 text-amber-400`} />);
    } else if (i === fullStars && hasHalfStar) {
      stars.push(
        <div key={i} className="relative">
          <Star className={`${starSize} text-gray-300`} />
          <div className="absolute inset-0 overflow-hidden w-1/2">
            <Star className={`${starSize} fill-amber-400 text-amber-400`} />
          </div>
        </div>
      );
    } else {
      stars.push(<Star key={i} className={`${starSize} text-gray-300`} />);
    }
  }
  
  return <div className="flex items-center gap-0.5">{stars}</div>;
};

// Review card component
const ReviewCard = ({ review }) => {
  const [expanded, setExpanded] = useState(false);
  const text = review.text || '';
  const isLong = text.length > 200;
  const displayText = expanded || !isLong ? text : text.substring(0, 200) + '...';
  
  return (
    <div className="border-b border-gray-100 dark:border-gray-700 pb-4 last:border-b-0">
      <div className="flex items-start gap-3">
        <div className="shrink-0">
          {review.author_photo_url ? (
            <img 
              src={review.author_photo_url} 
              alt={review.author_name}
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
              <User className="w-5 h-5 text-gray-400" />
            </div>
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="font-medium text-gray-900 dark:text-white text-sm">
                {review.author_name || 'Anonymous'}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <StarRating rating={review.rating || 0} size="sm" />
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatRelativeTime(review.publish_time, review.relative_publish_time)}
                </span>
              </div>
            </div>
          </div>
          
          {text && (
            <div className="mt-2">
              <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">
                {displayText}
              </p>
              {isLong && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="text-sm text-brand-primary hover:underline mt-1"
                >
                  {expanded ? 'Show less' : 'Read more'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Photo Gallery Modal - Full screen gallery with lazy loading
const PhotoGalleryModal = ({ isOpen, onClose, images, apiKey, initialIndex = 0 }) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [loadedImages, setLoadedImages] = useState(new Set([0, 1, 2])); // Pre-load first 3
  const [imageLoading, setImageLoading] = useState(false);
  
  useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex]);
  
  // Lazy load images as user navigates
  useEffect(() => {
    if (!loadedImages.has(currentIndex)) {
      setLoadedImages(prev => new Set([...prev, currentIndex]));
    }
    // Pre-load adjacent images
    const preloadIndices = [currentIndex - 1, currentIndex + 1].filter(
      i => i >= 0 && i < images.length && !loadedImages.has(i)
    );
    if (preloadIndices.length > 0) {
      setLoadedImages(prev => new Set([...prev, ...preloadIndices]));
    }
  }, [currentIndex, images.length, loadedImages]);
  
  const buildPhotoUrl = (image, index = 0) => {
    if (!ENABLE_GOOGLE_PHOTOS) {
      return `https://placehold.co/1200x800/e2e8f0/64748b?text=Photo+${index + 1}`;
    }
    if (image.url) {
      if (image.url.startsWith('http')) return image.url;
      if (image.url.startsWith('places/') && apiKey) {
        return `https://places.googleapis.com/v1/${image.url}/media?key=${apiKey}&maxHeightPx=1200&maxWidthPx=1600`;
      }
    }
    if (image.photo_reference && apiKey) {
      return `https://places.googleapis.com/v1/${image.photo_reference}/media?key=${apiKey}&maxHeightPx=1200&maxWidthPx=1600`;
    }
    return PLACEHOLDER_IMAGE;
  };
  
  const goToPrevious = () => {
    setCurrentIndex(prev => (prev > 0 ? prev - 1 : images.length - 1));
  };
  
  const goToNext = () => {
    setCurrentIndex(prev => (prev < images.length - 1 ? prev + 1 : 0));
  };
  
  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      if (e.key === 'ArrowLeft') goToPrevious();
      if (e.key === 'ArrowRight') goToNext();
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
  
  if (!isOpen || !images || images.length === 0) return null;
  
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 h-dvh max-h-dvh overflow-hidden z-60 bg-black/95 flex flex-col"


        >
          {/* Header */}
          <div className="shrink-0 flex items-center justify-between px-4 py-3 text-white">
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            <span className="text-sm font-medium">
              {currentIndex + 1} / {images.length}
            </span>
            <div className="w-10" /> {/* Spacer for centering */}
          </div>
          
          {/* Main image area */}
          <div className="flex-1 min-h-0 overflow-hidden flex items-center justify-center relative px-16">
            {/* Previous button */}
            <button
              onClick={goToPrevious}
              className="absolute left-4 p-3 bg-black/50 hover:bg-black/70 rounded-full text-white transition-colors"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
            
            {/* Current image */}
            <div className="max-w-full max-h-full flex items-center justify-center">
              {loadedImages.has(currentIndex) ? (
                <img
                  src={buildPhotoUrl(images[currentIndex], currentIndex)}
                  alt={`Photo ${currentIndex + 1}`}
                  className="max-w-full max-h-full object-contain"
                  onLoad={() => setImageLoading(false)}
                  onLoadStart={() => setImageLoading(true)}
                />
              ) : (
                <div className="flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
              )}
              {imageLoading && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
              )}
            </div>
            
            {/* Next button */}
            <button
              onClick={goToNext}
              className="absolute right-4 p-3 bg-black/50 hover:bg-black/70 rounded-full text-white transition-colors"
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          </div>
          
          {/* Thumbnail strip */}
          <div className="shrink-0 px-4 py-3 overflow-x-auto">
            <div className="flex gap-2 justify-center">
              {images.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentIndex(idx)}
                  className={`shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                    idx === currentIndex 
                      ? 'border-white scale-110' 
                      : 'border-transparent opacity-60 hover:opacity-100'
                  }`}
                >
                  {loadedImages.has(idx) || idx < 3 ? (
                    <img
                      src={buildPhotoUrl(img, idx)}
                      alt={`Thumbnail ${idx + 1}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full bg-gray-700 flex items-center justify-center text-xs text-gray-400">
                      {idx + 1}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// Photo Grid Component (1 large + 4 small)
const PhotoGrid = ({ images, apiKey, onShowAll }) => {
  if (!images || images.length === 0) {
    return (
      <div className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center">
        <MapPin className="w-12 h-12 text-gray-300" />
      </div>
    );
  }
  
  const buildPhotoUrl = (image, index = 0) => {
    // Skip Google Photos API if disabled (saves ~$7/1000 photos)
    // Controlled by VITE_ENABLE_GOOGLE_PHOTOS=false in .env
    if (!ENABLE_GOOGLE_PHOTOS) {
      return PLACEHOLDER_IMAGES[index % PLACEHOLDER_IMAGES.length];
    }
    
    if (image.url) {
      if (image.url.startsWith('http')) return image.url;
      if (image.url.startsWith('places/') && apiKey) {
        return `https://places.googleapis.com/v1/${image.url}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=800`;
      }
    }
    if (image.photo_reference && apiKey) {
      return `https://places.googleapis.com/v1/${image.photo_reference}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=800`;
    }
    return PLACEHOLDER_IMAGE;
  };
  
  const mainImage = images[0];
  const sideImages = images.slice(1, 3);
  const hasMorePhotos = images.length > 3;
  
  return (
    <div className="grid grid-cols-3 gap-2 rounded-xl overflow-hidden">
      {/* Main large image */}
      <button 
        onClick={() => onShowAll(0)}
        className="col-span-2 row-span-2 aspect-square relative group"
      >
        <img
          src={buildPhotoUrl(mainImage, 0)}
          alt="Main"
          className="w-full h-full object-cover group-hover:brightness-90 transition-all"
        />
      </button>
      
      {/* Side images (2x2 grid) */}
      <div className="grid grid-rows-2 gap-2">
        {sideImages.map((img, idx) => (
          <button 
            key={idx} 
            onClick={() => hasMorePhotos && idx === sideImages.length - 1 ? onShowAll(0) : onShowAll(idx + 1)}
            className="aspect-square relative group"
          >
            <img
              src={buildPhotoUrl(img, idx + 1)}
              alt={`Photo ${idx + 2}`}
              className="w-full h-full object-cover group-hover:brightness-90 transition-all"
            />
            {/* Show all photos button on last image */}
            {idx === sideImages.length - 1 && hasMorePhotos && (
              <div
                className="absolute inset-0 bg-black/50 flex items-center justify-center text-white text-sm font-medium group-hover:bg-black/60 transition-colors"
              >
                <Grid3X3 className="w-4 h-4 mr-1" />
                +{images.length - 3} photos
              </div>
            )}
          </button>
        ))}
        {/* Fill empty slots if less than 2 side images */}
        {sideImages.length < 2 && (
          <div className="aspect-square bg-gray-100 dark:bg-gray-700" />
        )}
      </div>
    </div>
  );
};

// Location Tab Component with Google Map
const LocationTab = ({ poi, apiKey }) => {
  const googleMapsUri = poi?.google_data?.google_maps_uri || '';
  const location = poi?.location;
  const viewport = poi?.google_data?.viewport;
  const addressComponents = poi?.google_data?.address_components || [];
  
  // Extract coordinates
  const coordinates = location?.coordinates || [];
  const lng = coordinates[0];
  const lat = coordinates[1];
  
  const center = useMemo(() => {
    if (lat && lng) return { lat, lng };
    return { lat: 16.0544, lng: 108.2428 }; // Default Da Nang
  }, [lat, lng]);
  
  // Calculate bounds from viewport
  const bounds = useMemo(() => {
    if (!viewport) return null;
    return {
      north: viewport.northeast?.latitude,
      south: viewport.southwest?.latitude,
      east: viewport.northeast?.longitude,
      west: viewport.southwest?.longitude,
    };
  }, [viewport]);
  
  // Format address from components
  const formattedAddress = useMemo(() => {
    if (!addressComponents.length) {
      // Handle address as object or string
      if (typeof poi?.address === 'string') return poi.address;
      if (poi?.address?.full_address) return poi.address.full_address;
      if (poi?.address?.city) {
        const parts = [poi.address.district, poi.address.city, poi.address.country].filter(Boolean);
        return parts.join(', ');
      }
      return '';
    }
    
    const parts = [];
    const district = addressComponents.find(c => c.types?.includes('administrative_area_level_2'));
    const city = addressComponents.find(c => c.types?.includes('administrative_area_level_1'));
    const country = addressComponents.find(c => c.types?.includes('country'));
    
    if (district) parts.push(district.long_name);
    if (city) parts.push(city.long_name);
    if (country) parts.push(country.long_name);
    
    return parts.join(', ');
  }, [addressComponents, poi?.address]);
  
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: apiKey || '',
  });
  
  const onLoad = useCallback((map) => {
    if (bounds && bounds.north && bounds.south) {
      const googleBounds = new window.google.maps.LatLngBounds(
        { lat: bounds.south, lng: bounds.west },
        { lat: bounds.north, lng: bounds.east }
      );
      map.fitBounds(googleBounds);
    }
  }, [bounds]);
  
  const mapContainerStyle = {
    width: '100%',
    height: '300px',
    borderRadius: '12px',
  };
  
  return (
    <div className="space-y-4">
      {/* Map */}
      {isLoaded ? (
        <GoogleMap
          mapContainerStyle={mapContainerStyle}
          center={center}
          zoom={15}
          onLoad={onLoad}
          options={{
            disableDefaultUI: true,
            zoomControl: true,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
          }}
        >
          <Marker position={center} />
        </GoogleMap>
      ) : (
        <div className="w-full h-75 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}
      
      {/* Address Info */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 space-y-3">
        <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <MapPin className="w-4 h-4 text-brand-primary" />
          Address
        </h3>
        
        <p className="text-sm text-gray-600 dark:text-gray-300">
          {typeof poi?.address === 'string' ? poi.address : poi?.address?.full_address || formattedAddress}
        </p>
        
        {formattedAddress && (typeof poi?.address === 'string' ? poi.address : poi?.address?.full_address) !== formattedAddress && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {formattedAddress}
          </p>
        )}
        
        {/* Coordinates */}
        <div className="text-xs text-gray-400 dark:text-gray-500 font-mono">
          {lat?.toFixed(6)}, {lng?.toFixed(6)}
        </div>
        
        {/* Open in Google Maps by Uri*/}
        <a
          href={googleMapsUri || `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-brand-primary hover:underline"
        >
          <ExternalLink className="w-4 h-4" />
          Open in Google Maps
        </a>
      </div>
    </div>
  );
};

// Main Component
export default function POIDetailPanel({ 
  isOpen, 
  onClose, 
  poiId, 
  googleMapsApiKey,
  onAddToPlan,
  isAddedToPlan = false,
}) {
  const [poi, setPoi] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showAllPhotos, setShowAllPhotos] = useState(false);
  const [galleryStartIndex, setGalleryStartIndex] = useState(0);
  const [isAdded, setIsAdded] = useState(isAddedToPlan);
  
  // Fetch POI details when panel opens
  useEffect(() => {
    if (isOpen && poiId) {
      fetchPOIDetail();
      setActiveTab('overview');
    }
  }, [isOpen, poiId]);
  
  useEffect(() => {
    setIsAdded(isAddedToPlan);
  }, [isAddedToPlan]);
  
  const fetchPOIDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await searchAPI.getPOIDetail(poiId);
      if (response?.poi) {
        setPoi(response.poi);
      } else {
        setError('Place not found');
      }
    } catch (err) {
      console.error('Failed to fetch POI detail:', err);
      setError(err.response?.data?.resultMessage?.en || 'Failed to load place details');
    } finally {
      setLoading(false);
    }
  };
  
  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);
  
  const handleAddToPlan = () => {
    if (onAddToPlan && poi) {
      onAddToPlan(poi);
      setIsAdded(true);
    }
  };
  
  const handleShare = async () => {
    if (navigator.share && poi) {
      try {
        await navigator.share({
          title: poi.name,
          text: poi.description?.short || `Check out ${poi.name}`,
          url: window.location.href,
        });
      } catch (err) {
        console.log('Share cancelled');
      }
    }
  };
  
  // Extract data
  const reviews = poi?.google_data?.reviews || [];
  const images = poi?.images || [];
  const openingHours = poi?.opening_hours || {};
  const contact = poi?.contact || {};
  const amenities = poi?.amenities || {};
  const diningOptions = poi?.dining_options || {};
  const serviceOptions = poi?.service_options || {};
  // Ensure rating is a number (handle case where poi.ratings is an object)
  const rawRating = poi?.ratings?.average ?? (typeof poi?.ratings === 'number' ? poi?.ratings : 0);
  const rating = typeof rawRating === 'number' ? rawRating : parseFloat(rawRating) || 0;
  const reviewCount = poi?.ratings?.count || poi?.user_ratings_total || 0;
  const primaryType = poi?.primary_type || poi?.types?.[0] || 'Place';
  
  // Tabs configuration
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'reviews', label: 'Reviews', count: reviews.length },
    { id: 'location', label: 'Location' },
    // { id: 'guides', label: 'Guides' },    // Hidden - no data yet
    // { id: 'activities', label: 'Activities' }, // Hidden - no data yet
  ];
  
  return (
    <>
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key={`poi-detail-backdrop-${poiId}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          
          {/* Slide-in Panel */}
          <motion.div
            key={`poi-detail-panel-${poiId}`}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.25 }}
            className="fixed top-0 right-0 z-50 w-full max-w-2xl lg:w-1/2 h-full bg-white dark:bg-gray-800 shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                >
                  <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                </button>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Share button */}
                <button
                  onClick={handleShare}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                >
                  <Share2 className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                </button>
                
                {/* Save/Added button */}
                {onAddToPlan && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleAddToPlan}
                    disabled={isAdded}
                    className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      isAdded 
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-brand-primary text-white hover:bg-brand-dark'
                    }`}
                  >
                    {isAdded ? (
                      <>
                        <Check className="w-4 h-4" />
                        Added
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        Save
                      </>
                    )}
                  </motion.button>
                )}
              </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                  <MapPin className="w-12 h-12 mb-3 text-gray-300" />
                  <p>{error}</p>
                  <button
                    onClick={fetchPOIDetail}
                    className="mt-3 text-brand-primary hover:underline"
                  >
                    Try again
                  </button>
                </div>
              ) : poi ? (
                <div className="p-4 space-y-4">
                  {/* POI Name & Rating */}
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                      {poi.name}
                    </h1>
                    <div className="flex items-center gap-2 mt-2 text-sm text-gray-600 dark:text-gray-300">
                      <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                      <span className="font-medium">{rating.toFixed(1)}</span>
                      <span className="text-gray-400">·</span>
                      <span>{reviewCount.toLocaleString()} reviews</span>
                      <span className="text-gray-400">·</span>
                      <span>
                        {(() => {
                          if (!poi.address) return 'Location';
                          if (typeof poi.address === 'string') return poi.address.split(',')[0];
                          return poi.address?.city || poi.address?.district || (poi.address?.full_address ? String(poi.address.full_address).split(',')[0] : 'Location');
                        })()}
                      </span>
                    </div>
                    {/* Type badge */}
                    <div className="mt-2">
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-300">
                        <MapPin className="w-3 h-3" />
                        {primaryType.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                  
                  {/* Photo Grid */}
                  <PhotoGrid 
                    images={images} 
                    apiKey={googleMapsApiKey}
                    onShowAll={(startIndex = 0) => {
                      setGalleryStartIndex(startIndex);
                      setShowAllPhotos(true);
                    }}
                  />
                  
                  {/* Tab Navigation */}
                  <div className="flex items-center gap-1 border-b border-gray-200 dark:border-gray-700">
                    {tabs.map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                          activeTab === tab.id
                            ? 'text-brand-primary'
                            : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                        }`}
                      >
                        {tab.label}
                        {tab.count !== undefined && tab.count > 0 && (
                          <span className="ml-1 text-xs text-gray-400">({tab.count})</span>
                        )}
                        {activeTab === tab.id && (
                          <motion.div
                            layoutId="activeTab"
                            className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-primary"
                          />
                        )}
                      </button>
                    ))}
                  </div>
                  
                  {/* Tab Content */}
                  <div className="pb-8">
                    {activeTab === 'overview' && (
                      <div className="space-y-4">
                        {/* Description */}
                        {(poi.description?.long || poi.description?.short) && (
                          <div>
                            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                              {poi.description?.long || poi.description?.short}
                            </p>
                          </div>
                        )}
                        
                        {/* Opening Hours */}
                        {openingHours.weekday_descriptions?.length > 0 && (
                          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                              <Clock className="w-4 h-4 text-brand-primary" />
                              Opening Hours
                            </h3>
                            <div className="space-y-1">
                              {openingHours.weekday_descriptions.map((desc, idx) => (
                                <p key={idx} className="text-sm text-gray-600 dark:text-gray-300">
                                  {desc}
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Contact */}
                        {(contact.phone || contact.website) && (
                          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                              <Phone className="w-4 h-4 text-brand-primary" />
                              Contact
                            </h3>
                            <div className="space-y-2">
                              {contact.phone && (
                                <a
                                  href={`tel:${contact.phone}`}
                                  className="flex items-center gap-2 text-sm text-brand-primary hover:underline"
                                >
                                  <Phone className="w-4 h-4" />
                                  {contact.phone}
                                </a>
                              )}
                              {contact.website && (
                                <a
                                  href={contact.website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 text-sm text-brand-primary hover:underline"
                                >
                                  <Globe className="w-4 h-4" />
                                  <span className="truncate">{contact.website}</span>
                                </a>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Amenities & Services */}
                        {(Object.keys(diningOptions).length > 0 || Object.keys(serviceOptions).length > 0 || Object.keys(amenities).length > 0) && (
                          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Amenities & Services</h3>
                            <div className="flex flex-wrap gap-2">
                              {diningOptions.serves_breakfast && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <UtensilsCrossed className="w-3 h-3" /> Breakfast
                                </span>
                              )}
                              {diningOptions.serves_lunch && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <UtensilsCrossed className="w-3 h-3" /> Lunch
                                </span>
                              )}
                              {diningOptions.serves_dinner && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <UtensilsCrossed className="w-3 h-3" /> Dinner
                                </span>
                              )}
                              {diningOptions.serves_coffee && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  ☕ Coffee
                                </span>
                              )}
                              {diningOptions.serves_vegetarian_food && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  🥗 Vegetarian
                                </span>
                              )}
                              {serviceOptions.dine_in && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  Dine-in
                                </span>
                              )}
                              {serviceOptions.takeout && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  Takeout
                                </span>
                              )}
                              {serviceOptions.delivery && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  🚚 Delivery
                                </span>
                              )}
                              {serviceOptions.outdoor_seating && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  🌳 Outdoor seating
                                </span>
                              )}
                              {serviceOptions.reservable && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <Calendar className="w-3 h-3" /> Reservable
                                </span>
                              )}
                              {amenities.free_wifi && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <Wifi className="w-3 h-3" /> Free WiFi
                                </span>
                              )}
                              {amenities.parking && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <Car className="w-3 h-3" /> Parking
                                </span>
                              )}
                              {amenities.wheelchair_accessible && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <Accessibility className="w-3 h-3" /> Accessible
                                </span>
                              )}
                              {amenities.accepts_credit_cards && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200">
                                  <CreditCard className="w-3 h-3" /> Credit cards
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {activeTab === 'reviews' && (
                      <div className="space-y-4">
                        {reviews.length > 0 ? (
                          reviews.map((review, idx) => (
                            <ReviewCard key={idx} review={review} />
                          ))
                        ) : (
                          <div className="text-center py-10 text-gray-500">
                            <Star className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                            <p>No reviews yet</p>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {activeTab === 'location' && (
                      <LocationTab 
                        poi={poi} 
                        apiKey={googleMapsApiKey} 
                      />
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
    
    {/* Photo Gallery Modal - Outside of main AnimatePresence to avoid key conflicts */}
    <PhotoGalleryModal
      isOpen={showAllPhotos}
      onClose={() => setShowAllPhotos(false)}
      images={images}
      apiKey={googleMapsApiKey}
      initialIndex={galleryStartIndex}
    />
    </>
  );
}
