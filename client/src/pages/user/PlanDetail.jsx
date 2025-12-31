/**
 * PlanDetail - Travel Plan Detail View (Continuous Scroll)
 * 
 * Features:
 * - All days displayed as continuous scrollable cards
 * - Sequential POI numbering across all days (1 to last)
 * - Google Maps with custom markers (featured images + type icons)
 * - InfoWindow on hover
 * - Info panels for costs, accommodation, preferences
 */

import { GoogleMap, InfoWindow, OverlayView, useJsApiLoader } from '@react-google-maps/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowLeft,
  Bed,
  Calendar,
  Camera,
  ChevronDown,
  ChevronUp,
  Coffee,
  CreditCard,
  Dumbbell,
  Film,
  Hospital,
  Landmark,
  Loader2,
  MapPin,
  Music,
  Palmtree,
  Plane,
  Settings2,
  Share2,
  ShoppingBag,
  Sparkles,
  Star,
  Train,
  TreePine,
  Utensils,
  UtensilsCrossed,
  Wine
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import planAPI from '../../services/planApi';

// Map container style
const mapContainerStyle = {
  width: '100%',
  height: '100%',
};

// Map options - disable default POI markers
const mapOptions = {
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: true,
  zoomControl: true,
  styles: [
    {
      featureType: 'poi',
      elementType: 'labels',
      stylers: [{ visibility: 'off' }]
    },
    {
      featureType: 'poi.business',
      stylers: [{ visibility: 'off' }]
    }
  ]
};

// POI type to icon mapping (expanded)
const getTypeIcon = (category) => {
  const iconMap = {
    // Food & Drink
    restaurant: UtensilsCrossed,
    food: Utensils,
    cafe: Coffee,
    coffee: Coffee,
    bar: Wine,
    pub: Wine,
    club: Music,
    nightlife: Music,
    // Cultural
    landmark: Landmark,
    museum: Landmark,
    temple: Landmark,
    pagoda: Landmark,
    church: Landmark,
    historical: Landmark,
    // Shopping
    shopping: ShoppingBag,
    mall: ShoppingBag,
    market: ShoppingBag,
    store: ShoppingBag,
    // Nature
    nature: TreePine,
    park: TreePine,
    beach: Palmtree,
    mountain: TreePine,
    lake: TreePine,
    waterfall: TreePine,
    // Accommodation
    hotel: Bed,
    accommodation: Bed,
    resort: Bed,
    hostel: Bed,
    homestay: Bed,
    // Activities
    viewpoint: Camera,
    attraction: Camera,
    entertainment: Film,
    cinema: Film,
    spa: Sparkles,
    wellness: Sparkles,
    gym: Dumbbell,
    sport: Dumbbell,
    // Transport
    airport: Plane,
    station: Train,
    transport: Train,
    // Services
    hospital: Hospital,
    clinic: Hospital,
  };
  
  if (!category) return MapPin;
  const lowerCategory = category.toLowerCase();
  
  for (const [key, icon] of Object.entries(iconMap)) {
    if (lowerCategory.includes(key)) return icon;
  }
  return MapPin;
};

// Check if category is accommodation type
const isAccommodation = (category) => {
  if (!category) return false;
  const lower = category.toLowerCase();
  return ['hotel', 'accommodation', 'resort', 'hostel', 'homestay', 'lodge', 'villa'].some(t => lower.includes(t));
};

// Format duration in Vietnamese
const formatDuration = (minutes) => {
  if (!minutes) return null;
  const numMinutes = typeof minutes === 'string' ? parseInt(minutes) : minutes;
  if (isNaN(numMinutes)) return minutes; // Return as-is if not parseable
  if (numMinutes >= 60) {
    const hours = Math.floor(numMinutes / 60);
    const mins = numMinutes % 60;
    return mins > 0 ? `${hours}h${mins}p` : `${hours} tiếng`;
  }
  return `${numMinutes} phút`;
};

// Parse estimated time slot (e.g., "09:00-10:30") to get start time and duration in minutes
const parseEstimatedTime = (timeSlot) => {
  if (!timeSlot || typeof timeSlot !== 'string') return { startTime: null, durationMinutes: null };
  
  const parts = timeSlot.split('-');
  if (parts.length !== 2) return { startTime: timeSlot, durationMinutes: null };
  
  const [start, end] = parts.map(t => t.trim());
  
  // Parse times to calculate duration
  const parseTime = (t) => {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + (m || 0);
  };
  
  try {
    const startMinutes = parseTime(start);
    const endMinutes = parseTime(end);
    const durationMinutes = endMinutes >= startMinutes 
      ? endMinutes - startMinutes 
      : (24 * 60 - startMinutes) + endMinutes; // Handle overnight
    
    return { startTime: start, durationMinutes };
  } catch {
    return { startTime: start, durationMinutes: null };
  }
};

// Normalize photo URL (Google Places photo path → media URL)
const buildPhotoUrl = (url, apiKey) => {
  if (!url) return null;
  if (url.startsWith('http')) return url;
  if (url.startsWith('places/') && apiKey) {
    return `https://places.googleapis.com/v1/${url}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=600`;
  }
  return url;
};

// Build share URL from token (fallback to current origin)
const buildShareUrl = (token) => {
  if (!token) return null;
  const origin = typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : 'http://localhost:5173';
  return `${origin}/shared/${token}`;
};

export default function PlanDetail() {
  const { planId, shareToken } = useParams();
  const isPublicView = Boolean(shareToken);
  const navigate = useNavigate();

  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoveredPOI, setHoveredPOI] = useState(null); // Changed to hover-based
  const [error, setError] = useState('');
  const [showInfoPanel, setShowInfoPanel] = useState(true);
  const [shareState, setShareState] = useState({ isPublic: false, shareToken: null, shareUrl: null });
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const mapRef = useRef(null);

  // Load Google Maps
  const googleMapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey,
  });

  useEffect(() => {
    if (!googleMapsApiKey) {
      setError((prev) => prev || 'Google Maps API key is not configured. Please contact support.');
    }
  }, [googleMapsApiKey]);
  // Fetch plan details (private or public view)
  useEffect(() => {
    const fetchPlan = async () => {
      try {
        setLoading(true);
        const result = isPublicView
          ? await planAPI.getSharedPlan(shareToken)
          : await planAPI.getPlanById(planId);

        if (result.success && result.data) {
          const planData = result.data.plan || result.data;
          setPlan(planData);
          setError('');

          // Initialize sharing info (only for owner view)
          if (!isPublicView) {
            const tokenFromPlan = planData.share_token || planData.shareToken;
            const isPublic = planData.is_public ?? Boolean(tokenFromPlan);
            const shareUrl = planData.share_url || buildShareUrl(tokenFromPlan);
            setShareState({
              isPublic,
              shareToken: tokenFromPlan || null,
              shareUrl: shareUrl || null,
            });
          } else {
            setShareState({
              isPublic: true,
              shareToken: shareToken,
              shareUrl: buildShareUrl(shareToken),
            });
          }
        } else {
          setError(result.error || 'Không tìm thấy kế hoạch');
        }
      } catch (err) {
        console.error('Error fetching plan:', err);
        setError('Lỗi khi tải kế hoạch');
      } finally {
        setLoading(false);
      }
    };

    if ((isPublicView && shareToken) || (!isPublicView && planId)) {
      fetchPlan();
    }
  }, [planId, shareToken, isPublicView]);

  // Format date helper
  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' });
  };

  // Get Google Maps link for POI
  const getGoogleMapsLink = (poiName, location) => {
    if (location?.latitude && location?.longitude) {
      return `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}`;
    }
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(poiName)}`;
  };

  // Normalize activity fields to keep POI name/description aligned
  const extractActivityData = (activity) => {
    if (!activity || typeof activity === 'string') {
      return { isString: true };
    }

    const poi = activity.poi || {};
    const rawLocation = activity.location || poi.location;
    const location = rawLocation && (rawLocation.latitude || rawLocation.lat)
      ? {
          latitude: rawLocation.latitude ?? rawLocation.lat,
          longitude: rawLocation.longitude ?? rawLocation.lng,
        }
      : null;

    return {
      isString: false,
      poiName: activity.poi_name || poi.name || 'Địa điểm',
      description: activity.description || poi.description || activity.activity || '',
      time: activity.time || activity.start_time || null,
      duration: activity.duration || activity.duration_minutes || null,
      estimatedCost: activity.estimated_cost || poi.estimated_cost || null,
      location,
      address: activity.address || poi.address || null,
      rating: activity.rating || poi.rating || null,
      category: activity.category || poi.category || null,
    };
  };

  // Extract ALL POIs with coordinates from entire itinerary (continuous numbering)
  const allPOIs = useMemo(() => {
    if (!plan?.itinerary) return [];
    
    const pois = [];
    let globalIndex = 0;
    
    plan.itinerary.forEach((day, dayIndex) => {
      const activities = day.activities || [];
      const estimatedTimes = day.estimated_times || [];
      const featuredImages = (day.featured_images || []).map((img) => buildPhotoUrl(img, googleMapsApiKey));
      
      let poiIndexInDay = 0;
      activities.forEach((activity, actIndex) => {
        globalIndex++;
        const data = extractActivityData(activity);
        if (data.isString) return;
        if (!data.location?.latitude || !data.location?.longitude) return;
        
        // Parse estimated time for this activity
        const { startTime, durationMinutes } = parseEstimatedTime(estimatedTimes[actIndex]);
        
        pois.push({
          id: globalIndex,
          dayIndex: dayIndex + 1,
          name: data.poiName,
          lat: data.location.latitude,
          lng: data.location.longitude,
          time: startTime || data.time || null,
          duration: durationMinutes || data.duration || null,
          category: data.category,
          rating: data.rating || null,
          reviewCount: activity.poi?.user_ratings_total || activity.user_ratings_total || null,
          featuredImage: featuredImages[poiIndexInDay] || null
        });
        poiIndexInDay++;
      });
    });
    
    return pois;
  }, [plan, googleMapsApiKey]);

  // Build global activity index map (for matching activity cards with POIs)
  const activityIndexMap = useMemo(() => {
    if (!plan?.itinerary) return {};
    
    const map = {};
    let globalIndex = 0;
    
    plan.itinerary.forEach((day, dayIndex) => {
      const activities = day.activities || [];
      activities.forEach((activity, actIndex) => {
        globalIndex++;
        map[`${dayIndex}-${actIndex}`] = globalIndex;
      });
    });
    
    return map;
  }, [plan]);

  // Map center (first POI with coords or destination location)
  const mapCenter = useMemo(() => {
    if (allPOIs.length > 0) {
      return { lat: allPOIs[0].lat, lng: allPOIs[0].lng };
    }
    
    const location = plan?.destination_location;
    if (location?.latitude && location?.longitude) {
      return { lat: location.latitude, lng: location.longitude };
    }
    
    return { lat: 16.0544, lng: 108.2428 }; // Default: Da Nang
  }, [allPOIs, plan]);

  // Calculate trip summary (costs, accommodations, preferences)
  const tripSummary = useMemo(() => {
    if (!plan?.itinerary) return null;
    
    let totalCost = 0;
    const accommodations = [];
    
    plan.itinerary.forEach((day) => {
      if (day.estimated_cost_vnd) {
        totalCost += day.estimated_cost_vnd;
      }
      if (day.accommodation_name && !accommodations.some(a => a.name === day.accommodation_name)) {
        accommodations.push({
          name: day.accommodation_name,
          address: day.accommodation_address,
          checkIn: day.check_in_time,
          checkOut: day.check_out_time
        });
      }
    });
    
    return {
      totalCost,
      accommodations,
      preferences: plan.preferences || {},
      numDays: plan.itinerary.length,
      numPOIs: allPOIs.length
    };
  }, [plan, allPOIs]);

  // Format VND currency
  const formatVND = (amount) => {
    if (!amount) return '0 ₫';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  // Handle map load
  const onMapLoad = useCallback((mapInstance) => {
    mapRef.current = mapInstance;
    
    // Fit bounds to show all POIs initially
    if (allPOIs.length > 1) {
      const bounds = new window.google.maps.LatLngBounds();
      allPOIs.forEach(poi => bounds.extend({ lat: poi.lat, lng: poi.lng }));
      mapInstance.fitBounds(bounds, { padding: 50 });
    }
  }, [allPOIs]);

  // Handle activity hover - focus on map
  const handleActivityHover = (globalIndex) => {
    const poi = allPOIs.find(p => p.id === globalIndex);
    if (poi && mapRef.current) {
      mapRef.current.panTo({ lat: poi.lat, lng: poi.lng });
      mapRef.current.setZoom(16);
      setHoveredPOI(poi.id);
    }
  };

  // Handle mouse leave - reset to show all
  const handleActivityLeave = () => {
    if (mapRef.current && allPOIs.length > 1) {
      const bounds = new window.google.maps.LatLngBounds();
      allPOIs.forEach(poi => bounds.extend({ lat: poi.lat, lng: poi.lng }));
      mapRef.current.fitBounds(bounds, { padding: 50 });
    }
    setHoveredPOI(null);
  };

  // Toggle plan sharing (owner view only)
  const handleToggleShare = async () => {
    if (isPublicView || !planId) return;
    const targetPublic = !shareState.isPublic;
    setShareLoading(true);
    try {
      const result = await planAPI.toggleShare(planId, targetPublic);
      if (result.success && result.data) {
        const token = result.data.share_token || shareState.shareToken;
        const isPublic = result.data.is_public ?? targetPublic;
        setShareState({
          isPublic,
          shareToken: token,
          shareUrl: result.data.share_url || buildShareUrl(token),
        });
        setShareCopied(false);
      } else {
        console.error('[Share] Toggle failed:', result.error);
      }
    } catch (err) {
      console.error('[Share] Toggle error:', err);
    } finally {
      setShareLoading(false);
    }
  };

  // Copy share link to clipboard
  const handleCopyShareLink = async () => {
    const url = shareState.shareUrl || buildShareUrl(shareState.shareToken);
    if (!url) return;

    try {
      await navigator.clipboard.writeText(url);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 1500);
    } catch (err) {
      console.error('[Share] Copy failed:', err);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 animate-spin text-gray-400" />
          <p className="text-gray-500 font-medium">Đang tải kế hoạch...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !plan) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error || 'Không tìm thấy kế hoạch'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-600 hover:text-gray-900 flex items-center gap-2 mx-auto"
          >
            <ArrowLeft className="w-4 h-4" />
            Quay lại Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-full px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="font-poppins font-bold text-xl text-gray-900">
                {plan.plan_name || plan.destination}
              </h1>
              <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {plan.destination}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {plan.itinerary?.length || 0} ngày
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {isPublicView && (
              <span className="text-xs font-medium text-brand-primary bg-brand-muted px-3 py-1 rounded-full">
                Bản chia sẻ công khai
              </span>
            )}

            {!isPublicView && (
              <motion.button
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleToggleShare}
                disabled={shareLoading}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  shareState.isPublic
                    ? 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100'
                    : 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'
                } ${shareLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                <Share2 className="w-4 h-4" />
                <span className="text-sm font-semibold">
                  {shareState.isPublic ? 'Đang công khai' : 'Chỉ mình tôi'}
                </span>
              </motion.button>
            )}

            <motion.button
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleCopyShareLink}
              disabled={!shareState.shareUrl}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                shareState.shareUrl
                  ? 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                  : 'border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Share2 className="w-4 h-4" />
              <span className="text-sm font-semibold">
                {shareCopied ? 'Đã sao chép' : 'Sao chép link'}
              </span>
            </motion.button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Left: Scrollable Itinerary - All Days */}
        <main className="w-[40%] overflow-y-auto px-8 py-6 min-w-[400px] border-r border-gray-200">
          <div className="max-w-3xl mx-auto space-y-8">
            {plan.itinerary?.map((day, dayIndex) => {
              // Calculate starting index for this day
              const startIndex = plan.itinerary
                .slice(0, dayIndex)
                .reduce((sum, d) => sum + (d.activities?.length || 0), 0);
              
              return (
                <motion.div
                  key={dayIndex}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: dayIndex * 0.1 }}
                  className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
                >
                  {/* Day Header */}
                  <div className="bg-brand-primary text-white px-6 py-4">
                    <h2 className="font-poppins font-bold text-lg">
                      Ngày {dayIndex + 1}
                      {day.date && (
                        <span className="font-normal text-gray-300 ml-2">
                          - {formatDate(day.date)}
                        </span>
                      )}
                    </h2>
                    {day.theme && (
                      <p className="text-gray-300 text-sm mt-1">{day.theme}</p>
                    )}
                  </div>

                  {/* Activities - Continuous bullet list */}
                  <div className="p-6">
                    {day.activities?.length > 0 ? (
                      <ul className="space-y-3">
                        {day.activities.map((activity, actIndex) => {
                          const globalIndex = startIndex + actIndex + 1;
                          const extracted = extractActivityData(activity);
                          const isString = extracted.isString;
                          
                          // Parse estimated time from day's estimated_times array
                          const estimatedTimes = day.estimated_times || [];
                          const { startTime, durationMinutes } = parseEstimatedTime(estimatedTimes[actIndex]);
                          
                          const {
                            poiName,
                            description,
                            time,
                            duration,
                            estimatedCost,
                            location,
                            address,
                            rating,
                              category,
                          } = extracted;
                          
                          // Use parsed time or fallback to extracted
                          const displayTime = startTime || time;
                          const displayDuration = durationMinutes || duration;
                          
                          const hasLocation = location?.latitude && location?.longitude;
                          const isAccomm = isAccommodation(category);
                          const TypeIcon = getTypeIcon(category);
                          const durationText = formatDuration(displayDuration);

                          return (
                            <li
                              key={actIndex}
                              className={`py-2 border-l-3 pl-4 transition-all ${
                                isAccomm 
                                  ? 'border-l-purple-400 bg-purple-50/50 rounded-r-lg -ml-4 pl-8 pr-4'
                                  : hoveredPOI === globalIndex
                                    ? 'border-l-brand-secondary bg-brand-muted/30'
                                    : 'border-l-gray-200 hover:border-l-brand-primary'
                              }`}
                            >
                              {/* Main line: Time + POI Name (clickable) + Duration */}
                              <div className="flex items-start gap-2 flex-wrap">
                                {/* Index badge */}
                                <span className={`inline-flex items-center justify-center w-6 h-6 text-xs font-bold rounded-full shrink-0 ${
                                  isAccomm ? 'bg-purple-500 text-white' : 'bg-brand-primary text-white'
                                }`}>
                                  {globalIndex}
                                </span>
                                
                                {/* Time */}
                                {displayTime && (
                                  <span className="text-sm text-gray-500 font-medium">
                                    {displayTime}
                                  </span>
                                )}
                                
                                {/* Separator */}
                                {displayTime && <span className="text-gray-300">—</span>}
                                
                                {/* POI Name - Clickable link to map */}
                                {poiName && hasLocation ? (
                                  <button
                                    onClick={() => handleActivityHover(globalIndex)}
                                    onMouseEnter={() => handleActivityHover(globalIndex)}
                                    onMouseLeave={handleActivityLeave}
                                    className={`font-semibold text-base hover:underline cursor-pointer inline-flex items-center gap-1 transition-colors ${
                                      isAccomm 
                                        ? 'text-purple-700 hover:text-purple-800'
                                        : 'text-brand-primary hover:text-brand-secondary'
                                    }`}
                                  >
                                    <TypeIcon className="w-4 h-4" />
                                    "{poiName}"
                                  </button>
                                ) : poiName ? (
                                  <span className="font-semibold text-base text-gray-800 inline-flex items-center gap-1">
                                    <TypeIcon className="w-4 h-4 text-gray-400" />
                                    {poiName}
                                  </span>
                                ) : null}
                                
                                {/* Duration badge */}
                                {durationText && (
                                  <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                                    ~{durationText}
                                  </span>
                                )}
                                
                                {/* Accommodation badge */}
                                {isAccomm && (
                                  <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded-full font-medium">
                                    Lưu trú
                                  </span>
                                )}
                              </div>
                              
                              {/* Description line */}
                              {description && (
                                <p className="text-sm text-gray-600 mt-1 ml-8">
                                  {description}
                                </p>
                              )}
                              
                              {/* Meta info (cost, address) */}
                              {(estimatedCost || address) && (
                                <div className="text-xs text-gray-400 mt-1 ml-8 flex flex-wrap gap-2">
                                  {estimatedCost && <span>💰 {estimatedCost}</span>}
                                  {address && <span className="truncate max-w-[250px]" title={address}>📍 {address}</span>}
                                </div>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-gray-500 text-center py-4">
                        Chưa có hoạt động cho ngày này
                      </p>
                    )}
                  </div>

                  {/* Day Notes */}
                  {day.notes && (
                    <div className="px-6 pb-4">
                      <p className="text-sm text-gray-500 italic border-t border-gray-100 pt-4">
                        💡 {day.notes}
                      </p>
                    </div>
                  )}
                </motion.div>
              );
            })}

            {/* Summary Card */}
            {plan.summary && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: (plan.itinerary?.length || 0) * 0.1 }}
                className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6"
              >
                <h3 className="font-poppins font-bold text-lg text-gray-900 mb-3">
                  📋 Tổng kết chuyến đi
                </h3>
                <p className="text-gray-700">{plan.summary}</p>
              </motion.div>
            )}
          </div>
        </main>

        {/* Right: Sticky Google Map with Info Panels */}
        <aside className="w-[60%] bg-white shrink-0 sticky top-[73px] h-[calc(100vh-73px)] relative">
          {loadError && (
            <div className="flex items-center justify-center h-full text-gray-500">
              Lỗi tải Google Maps
            </div>
          )}
          
          {!isLoaded && !loadError && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          )}

          {isLoaded && (
            <>
              <GoogleMap
                mapContainerStyle={mapContainerStyle}
                center={mapCenter}
                zoom={13}
                options={mapOptions}
                onLoad={onMapLoad}
              >
                {/* Custom Markers for ALL POIs using OverlayView */}
                {allPOIs.map((poi) => {
                  const TypeIcon = getTypeIcon(poi.category);
                  const isHovered = hoveredPOI === poi.id;
                  
                  return (
                    <OverlayView
                      key={poi.id}
                      position={{ lat: poi.lat, lng: poi.lng }}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ 
                          scale: isHovered ? 1.2 : 1, 
                          opacity: 1,
                          zIndex: isHovered ? 100 : 1
                        }}
                        className="relative cursor-pointer transform -translate-x-1/2 -translate-y-1/2"
                        onMouseEnter={() => setHoveredPOI(poi.id)}
                        onMouseLeave={() => setHoveredPOI(null)}
                        style={{ position: 'relative', zIndex: isHovered ? 100 : 1 }}
                      >
                        {/* Marker container - bumped size for clarity */}
                        <div 
                          className={`w-11 h-11 rounded-full border-2 shadow-md overflow-hidden transition-all duration-200 ${
                            isAccommodation(poi.category)
                              ? isHovered 
                                ? 'border-purple-400 ring-3 ring-purple-400/40' 
                                : 'border-purple-300'
                              : isHovered 
                                ? 'border-brand-secondary ring-3 ring-brand-secondary/30' 
                                : 'border-white'
                          }`}
                          style={{
                            backgroundImage: poi.featuredImage ? `url(${poi.featuredImage})` : 'none',
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                            backgroundColor: poi.featuredImage ? 'transparent' : (isAccommodation(poi.category) ? '#8B5CF6' : '#2E571C')
                          }}
                        >
                          {/* Icon overlay at bottom-right - smaller */}
                          <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-white rounded-full shadow-sm flex items-center justify-center">
                            <TypeIcon className="w-2.5 h-2.5 text-brand-primary" />
                          </div>
                          
                          {/* Number badge at top-left - smaller */}
                          <div className={`absolute -top-1 -left-1 w-4 h-4 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow ${
                            isAccommodation(poi.category) ? 'bg-purple-500' : 'bg-brand-primary'
                          }`}>
                            {poi.id}
                          </div>
                          
                          {/* Fallback icon if no image - smaller */}
                          {!poi.featuredImage && (
                            <div className="w-full h-full flex items-center justify-center">
                              <TypeIcon className="w-4 h-4 text-white" />
                            </div>
                          )}
                        </div>
                      </motion.div>
                    </OverlayView>
                  );
                })}

                {/* InfoWindow for hovered POI - Compact & Professional */}
                {hoveredPOI && (() => {
                  const poi = allPOIs.find(p => p.id === hoveredPOI);
                  if (!poi) return null;
                  const isAccomm = isAccommodation(poi.category);
                  
                  return (
                    <InfoWindow
                      position={{ lat: poi.lat, lng: poi.lng }}
                      onCloseClick={() => setHoveredPOI(null)}
                      options={{ 
                        disableAutoPan: true, 
                        pixelOffset: new window.google.maps.Size(0, -24),
                        maxWidth: 220
                      }}
                    >
                      <div className="p-1 min-w-[160px] max-w-[200px]">
                        {/* Featured image */}
                        {poi.featuredImage && (
                          <img 
                            src={poi.featuredImage}
                            alt=""
                            className="w-full h-16 object-cover rounded mb-1.5"
                          />
                        )}
                        
                        {/* POI Name */}
                        <p className={`font-semibold text-sm leading-tight ${
                          isAccomm ? 'text-purple-700' : 'text-gray-900'
                        }`}>
                          {poi.id}. {poi.name}
                        </p>
                        
                        {/* Rating & Reviews */}
                        {(poi.rating || poi.reviewCount) && (
                          <div className="flex items-center gap-1.5 mt-1">
                            {poi.rating && (
                              <span className="inline-flex items-center gap-0.5 text-xs font-medium text-amber-600">
                                <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                {poi.rating.toFixed(1)}
                              </span>
                            )}
                            {poi.reviewCount && (
                              <span className="text-[10px] text-gray-400">
                                ({poi.reviewCount.toLocaleString()} đánh giá)
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Day & Time - single line */}
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                          <span>Ngày {poi.dayIndex}</span>
                          {poi.time && (
                            <>
                              <span className="text-gray-300">•</span>
                              <span>{poi.time}</span>
                            </>
                          )}
                          {poi.duration && (
                            <>
                              <span className="text-gray-300">•</span>
                              <span>{formatDuration(poi.duration)}</span>
                            </>
                          )}
                        </div>
                        
                        {/* Accommodation badge */}
                        {isAccomm && (
                          <span className="inline-block mt-1.5 text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
                            🏨 Lưu trú
                          </span>
                        )}
                      </div>
                    </InfoWindow>
                  );
                })()}
              </GoogleMap>

              {/* Floating Info Panel */}
              <AnimatePresence>
                {tripSummary && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="absolute bottom-4 left-4 right-4 z-10"
                  >
                    <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
                      {/* Toggle Header */}
                      <button 
                        onClick={() => setShowInfoPanel(!showInfoPanel)}
                        className="w-full px-4 py-3 flex items-center justify-between bg-brand-muted hover:bg-brand-muted/80 transition-colors"
                      >
                        <span className="font-poppins font-semibold text-brand-primary flex items-center gap-2">
                          <Settings2 className="w-4 h-4" />
                          Thông tin chuyến đi
                        </span>
                        {showInfoPanel ? (
                          <ChevronDown className="w-5 h-5 text-brand-primary" />
                        ) : (
                          <ChevronUp className="w-5 h-5 text-brand-primary" />
                        )}
                      </button>

                      {/* Panel Content */}
                      <AnimatePresence>
                        {showInfoPanel && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="p-4 grid grid-cols-3 gap-4">
                              {/* Cost Summary */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase flex items-center gap-1">
                                  <CreditCard className="w-3 h-3" />
                                  Chi phí ước tính
                                </h4>
                                <p className="text-lg font-bold text-brand-primary">
                                  {formatVND(tripSummary.totalCost)}
                                </p>
                                <p className="text-xs text-gray-500">
                                  ~{formatVND(Math.round(tripSummary.totalCost / tripSummary.numDays))}/ngày
                                </p>
                              </div>

                              {/* Accommodation Info */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase flex items-center gap-1">
                                  <Bed className="w-3 h-3" />
                                  Lưu trú
                                </h4>
                                {tripSummary.accommodations.length > 0 ? (
                                  <div className="space-y-1">
                                    {tripSummary.accommodations.slice(0, 2).map((acc, i) => (
                                      <p key={i} className="text-sm font-medium text-gray-800 truncate" title={acc.name}>
                                        🏨 {acc.name}
                                      </p>
                                    ))}
                                    {tripSummary.accommodations.length > 2 && (
                                      <p className="text-xs text-gray-400">
                                        +{tripSummary.accommodations.length - 2} nơi khác
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <p className="text-sm text-gray-400">Chưa có thông tin</p>
                                )}
                              </div>

                              {/* Preferences */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase flex items-center gap-1">
                                  <Settings2 className="w-3 h-3" />
                                  Tùy chọn
                                </h4>
                                <div className="space-y-1 text-sm">
                                  {tripSummary.preferences.budget && (
                                    <p className="text-gray-700">
                                      💰 {formatVND(tripSummary.preferences.budget)}
                                    </p>
                                  )}
                                  {tripSummary.preferences.budget_level && (
                                    <p className="text-gray-700 capitalize">
                                      📊 {tripSummary.preferences.budget_level}
                                    </p>
                                  )}
                                  {tripSummary.preferences.pace && (
                                    <p className="text-gray-700 capitalize">
                                      🚶 {tripSummary.preferences.pace}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="px-4 pb-4 flex items-center justify-center gap-6 text-sm text-gray-500">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                {tripSummary.numDays} ngày
                              </span>
                              <span className="flex items-center gap-1">
                                <MapPin className="w-4 h-4" />
                                {tripSummary.numPOIs} địa điểm
                              </span>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
