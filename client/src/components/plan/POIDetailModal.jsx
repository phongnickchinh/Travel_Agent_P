/**
 * POI Detail Modal - Shows full POI details including reviews
 * 
 * Features:
 * - Full POI information display
 * - Photo gallery
 * - Reviews with ratings
 * - Opening hours
 * - Contact information
 * - Amenities and services
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
    Accessibility,
    Calendar,
    Car,
    ChevronLeft,
    ChevronRight,
    Clock,
    CreditCard,
    ExternalLink,
    Globe,
    Loader2,
    MapPin,
    Phone,
    Star,
    User,
    UtensilsCrossed,
    Wifi,
    X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import searchAPI from '../../services/searchApi';

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
      stars.push(
        <Star key={i} className={`${starSize} fill-amber-400 text-amber-400`} />
      );
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
      stars.push(
        <Star key={i} className={`${starSize} text-gray-300`} />
      );
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
        {/* Author photo */}
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
        
        {/* Review content */}
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

// Photo gallery component
const PhotoGallery = ({ images, apiKey }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  
  if (!images || images.length === 0) return null;
  
  const buildPhotoUrl = (image) => {
    if (image.url) {
      if (image.url.startsWith('http')) return image.url;
      if (image.url.startsWith('places/') && apiKey) {
        return `https://places.googleapis.com/v1/${image.url}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=800`;
      }
    }
    if (image.photo_reference && apiKey) {
      return `https://places.googleapis.com/v1/${image.photo_reference}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=800`;
    }
    return null;
  };
  
  const currentImage = images[currentIndex];
  const imageUrl = buildPhotoUrl(currentImage);
  
  const goNext = () => setCurrentIndex((prev) => (prev + 1) % images.length);
  const goPrev = () => setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  
  return (
    <div className="relative w-full aspect-video bg-gray-100 dark:bg-gray-700 rounded-xl overflow-hidden">
      {imageUrl ? (
        <img 
          src={imageUrl} 
          alt={`Photo ${currentIndex + 1}`}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <MapPin className="w-12 h-12 text-gray-300" />
        </div>
      )}
      
      {/* Navigation arrows */}
      {images.length > 1 && (
        <>
          <button
            onClick={goPrev}
            className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full text-white transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={goNext}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 hover:bg-black/70 rounded-full text-white transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
          
          {/* Dots indicator */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {images.slice(0, 5).map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  idx === currentIndex ? 'bg-white' : 'bg-white/50'
                }`}
              />
            ))}
            {images.length > 5 && (
              <span className="text-white text-xs ml-1">+{images.length - 5}</span>
            )}
          </div>
        </>
      )}
      
      {/* Attribution */}
      {currentImage?.author_attributions?.[0]?.displayName && (
        <div className="absolute bottom-3 right-3 text-xs text-white/80 bg-black/40 px-2 py-1 rounded">
          Photo by {currentImage.author_attributions[0].displayName}
        </div>
      )}
    </div>
  );
};

export default function POIDetailModal({ isOpen, onClose, poiId, googleMapsApiKey }) {
  const [poi, setPoi] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Fetch POI details when modal opens
  useEffect(() => {
    if (isOpen && poiId) {
      fetchPOIDetail();
    }
  }, [isOpen, poiId]);
  
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
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);
  
  if (!isOpen) return null;
  
  const reviews = poi?.google_data.reviews || [];
  const images = poi?.images || [];
  const openingHours = poi?.opening_hours || {};
  const contact = poi?.contact || {};
  const amenities = poi?.amenities || {};
  const diningOptions = poi?.dining_options || {};
  const serviceOptions = poi?.service_options || {};
  
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex items-center justify-between">
                <h2 className="font-poppins font-bold text-xl text-gray-900 dark:text-white truncate pr-4">
                  {poi?.name || 'Place Details'}
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              
              {/* Tabs */}
              {poi && (
                <div className="flex gap-4 mt-3 -mb-4 border-b-0">
                  <button
                    onClick={() => setActiveTab('overview')}
                    className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'overview'
                        ? 'text-brand-primary border-brand-primary'
                        : 'text-gray-500 border-transparent hover:text-gray-700'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setActiveTab('reviews')}
                    className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'reviews'
                        ? 'text-brand-primary border-brand-primary'
                        : 'text-gray-500 border-transparent hover:text-gray-700'
                    }`}
                  >
                    Reviews ({reviews.length})
                  </button>
                </div>
              )}
            </div>
            
            {/* Content */}
            <div className="overflow-y-auto max-h-[calc(90vh-100px)]">
              {loading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
                  <MapPin className="w-12 h-12 text-gray-300 mb-4" />
                  <p className="text-gray-500">{error}</p>
                  <button
                    onClick={fetchPOIDetail}
                    className="mt-4 text-brand-primary hover:underline text-sm"
                  >
                    Try again
                  </button>
                </div>
              ) : poi ? (
                <div className="p-6">
                  {activeTab === 'overview' && (
                    <div className="space-y-6">
                      {/* Photo gallery */}
                      {images.length > 0 && (
                        <PhotoGallery images={images} apiKey={googleMapsApiKey} />
                      )}
                      
                      {/* Rating & Address */}
                      <div className="space-y-3">
                        {/* Rating */}
                        {poi.rating && (
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1.5">
                              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                                {poi.rating.toFixed(1)}
                              </span>
                              <StarRating rating={poi.rating} size="md" />
                            </div>
                            {poi.total_reviews > 0 && (
                              <span className="text-sm text-gray-500">
                                ({poi.total_reviews.toLocaleString()} reviews)
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Address */}
                        {poi.formatted_address && (
                          <div className="flex items-start gap-2 text-gray-600 dark:text-gray-300">
                            <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-gray-400" />
                            <p className="text-sm">{poi.formatted_address}</p>
                          </div>
                        )}
                        
                        {/* Google Maps link */}
                        {contact.google_maps_uri && (
                          <a
                            href={contact.google_maps_uri}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-sm text-brand-primary hover:underline"
                          >
                            <ExternalLink className="w-4 h-4" />
                            Open in Google Maps
                          </a>
                        )}
                      </div>
                      
                      {/* Opening hours */}
                      {openingHours.weekday_text && openingHours.weekday_text.length > 0 && (
                        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                          <h3 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            Opening Hours
                          </h3>
                          <div className="space-y-1">
                            {openingHours.weekday_text.map((text, idx) => (
                              <p key={idx} className="text-sm text-gray-600 dark:text-gray-300">
                                {text}
                              </p>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Contact info */}
                      {(contact.phone || contact.website) && (
                        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
                          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Contact</h3>
                          <div className="space-y-2">
                            {contact.phone && (
                              <a
                                href={`tel:${contact.phone}`}
                                className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 hover:text-brand-primary"
                              >
                                <Phone className="w-4 h-4" />
                                {contact.international_phone || contact.phone}
                              </a>
                            )}
                            {contact.website && (
                              <a
                                href={contact.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 hover:text-brand-primary"
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
                            {/* Dining options */}
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
                            
                            {/* Service options */}
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
                            
                            {/* Amenities */}
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
                </div>
              ) : null}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
