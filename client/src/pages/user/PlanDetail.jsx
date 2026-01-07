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
  Church,
  Clock,
  Coffee,
  CreditCard,
  Dumbbell,
  Film,
  Heart,
  Hospital,
  Landmark,
  Loader2,
  MapPin,
  Mountain,
  Music,
  Palmtree,
  Plane,
  Plus,
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
import DayItinerary from '../../components/features/plan/DayItinerary';
import RegeneratePlanModal from '../../components/features/plan/RegeneratePlanModal';
import { EditableDate, EditableTitle } from '../../components/ui/EditableField';
import planAPI from '../../services/planApi';
import { getCachedImage, preloadAndCacheImage } from '../../utils/imageCache';

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
    // Cultural & Historical
    landmark: Landmark,
    museum: Landmark,
    temple: Landmark,
    pagoda: Landmark,
    church: Church,
    cathedral: Church,
    mosque: Church,
    shrine: Church,
    religious: Church,
    historical: Landmark,
    cultural: Landmark,
    heritage: Landmark,
    // Shopping
    shopping: ShoppingBag,
    mall: ShoppingBag,
    market: ShoppingBag,
    store: ShoppingBag,
    boutique: ShoppingBag,
    // Nature & Outdoor
    nature: TreePine,
    park: TreePine,
    beach: Palmtree,
    mountain: Mountain,
    hill: Mountain,
    peak: Mountain,
    lake: TreePine,
    waterfall: TreePine,
    river: TreePine,
    forest: TreePine,
    garden: TreePine,
    // Accommodation
    hotel: Bed,
    accommodation: Bed,
    resort: Bed,
    hostel: Bed,
    homestay: Bed,
    lodge: Bed,
    // Activities & Entertainment
    viewpoint: Camera,
    attraction: Camera,
    entertainment: Film,
    cinema: Film,
    theater: Film,
    adventure: Mountain,
    // Wellness & Sports
    spa: Sparkles,
    wellness: Heart,
    massage: Heart,
    gym: Dumbbell,
    sport: Dumbbell,
    fitness: Dumbbell,
    yoga: Heart,
    // Transport
    airport: Plane,
    station: Train,
    transport: Train,
    bus: Train,
    // Services
    hospital: Hospital,
    clinic: Hospital,
    medical: Hospital,
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

// Get marker color based on POI type (category-themed colors)
const getMarkerColor = (category) => {
  if (!category) return '#2E571C'; // Default brand primary
  const lower = category.toLowerCase();
  
  // Category-themed color palette
  const colorMap = {
    // Nature & Beach (Blue/Aqua)
    beach: '#3B82F6',
    ocean: '#3B82F6',
    sea: '#3B82F6',
    // Nature (Green)
    nature: '#10B981',
    park: '#10B981',
    forest: '#10B981',
    garden: '#10B981',
    tree: '#10B981',
    // Cultural & Historical (Purple)
    cultural: '#8B5CF6',
    museum: '#8B5CF6',
    temple: '#8B5CF6',
    pagoda: '#8B5CF6',
    church: '#8B5CF6',
    historical: '#8B5CF6',
    heritage: '#8B5CF6',
    landmark: '#8B5CF6',
    // Food & Drink (Orange/Red)
    restaurant: '#F97316',
    food: '#F97316',
    cafe: '#F59E0B',
    coffee: '#F59E0B',
    bar: '#EF4444',
    // Shopping (Pink)
    shopping: '#EC4899',
    mall: '#EC4899',
    market: '#EC4899',
    // Mountain & Adventure (Brown/Gray)
    mountain: '#78716C',
    hill: '#78716C',
    adventure: '#78716C',
    // Wellness (Pink/Rose)
    wellness: '#F472B6',
    spa: '#F472B6',
    yoga: '#F472B6',
    // Accommodation (Indigo)
    hotel: '#6366F1',
    accommodation: '#6366F1',
    resort: '#6366F1',
  };
  
  // Find matching color
  for (const [key, color] of Object.entries(colorMap)) {
    if (lower.includes(key)) return color;
  }
  
  return '#2E571C'; // Default brand primary
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

// Normalize photo URL (Google Places photo path → media URL) with caching
const buildPhotoUrl = (url, apiKey) => {
  if (!url) return null;
  
  // TEMPORARY: Disable Google Photos API to check costs
  if (url.startsWith('places/')) {
    // console.log('Skipping Google Photo API call for:', url);
    return 'https://placehold.co/600x400?text=No+Photo+(Cost+Check)'; 
  }
  
  let finalUrl = url;
  
  // Build full URL if needed
  if (!url.startsWith('http')) {
    if (url.startsWith('places/') && apiKey) {
      finalUrl = `https://places.googleapis.com/v1/${url}/media?key=${apiKey}&maxHeightPx=600&maxWidthPx=600`;
    } else {
      finalUrl = url;
    }
  }
  
  // Check cache first
  const cached = getCachedImage(finalUrl);
  return cached || finalUrl;
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
  const [hoveredImageCache, setHoveredImageCache] = useState({}); // Lazy-loaded images cache
  const [showRegenerateModal, setShowRegenerateModal] = useState(false);
  const [regenerateLoading, setRegenerateLoading] = useState(false);
  const mapRef = useRef(null);
  const preHoverViewRef = useRef(null);
  const hoverTimeoutRef = useRef(null); // Timeout for delayed hover (prevent accidental image loading)

  // ========== INLINE EDITING HANDLERS ==========
  
  // Save plan title
  const handleSaveTitle = useCallback(async (newTitle) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateTitle(planId, newTitle);
    if (result.success) {
      setPlan(prev => ({ ...prev, plan_name: newTitle }));
    } else {
      throw new Error(result.error || 'Lỗi cập nhật tiêu đề');
    }
  }, [planId, isPublicView]);

  // Save start date (recalculates all day dates on backend)
  const handleSaveStartDate = useCallback(async (newDate) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateStartDate(planId, newDate);
    if (result.success && result.data) {
      // Update full plan to get recalculated day dates
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Lỗi cập nhật ngày bắt đầu');
    }
  }, [planId, isPublicView]);

  // Save day notes
  const handleSaveDayNotes = useCallback(async (dayNumber, newNotes) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayNotes(planId, dayNumber, newNotes);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Lỗi cập nhật ghi chú');
    }
  }, [planId, isPublicView]);

  // Save day activities (array of strings)
  const handleSaveDayActivities = useCallback(async (dayNumber, activitiesText) => {
    if (!planId || isPublicView) return;
    // Convert comma/newline-separated text to array
    const activities = activitiesText
      .split(/[,\n]/)
      .map(a => a.trim())
      .filter(a => a.length > 0);
    
    const result = await planAPI.updateDayActivities(planId, dayNumber, activities);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Lỗi cập nhật hoạt động');
    }
  }, [planId, isPublicView]);

  // Save day accommodation
  const handleSaveAccommodation = useCallback(async (dayNumber, accommodationData) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayAccommodation(planId, dayNumber, accommodationData);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Lỗi cập nhật chỗ ở');
    }
  }, [planId, isPublicView]);

  // Save day itinerary (activities + estimated times)
  const handleSaveDayItinerary = useCallback(async (dayNumber, activities, estimatedTimes, poiIds) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayActivitiesWithTimes(planId, dayNumber, activities, estimatedTimes, poiIds);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Lỗi cập nhật hoạt động');
    }
  }, [planId, isPublicView]);

  const handleRegeneratePlan = useCallback(async (payload) => {
    if (!planId || isPublicView) return;
    setRegenerateLoading(true);
    try {
      const updateResult = await planAPI.updatePlan(planId, payload);
      if (!updateResult.success) {
        throw new Error(updateResult.error || 'Lỗi cập nhật kế hoạch');
      }
      const refreshed = await planAPI.getPlanById(planId);
      if (refreshed.success && refreshed.data) {
        const planData = refreshed.data.plan || refreshed.data;
        setPlan(planData);
      }
      setShowRegenerateModal(false);
    } catch (err) {
      console.error('[Regenerate] failed', err);
    } finally {
      setRegenerateLoading(false);
    }
  }, [planId, isPublicView]);

  // ========================================

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

  // Auto-reload when status is pending/processing (polling every 3 seconds)
  useEffect(() => {
    if (!plan || isPublicView) return;
    
    const status = plan.status?.toLowerCase();
    if (status === 'pending' || status === 'processing') {
      console.log(`[PlanDetail] Plan status is ${status}, starting polling...`);
      
      const pollInterval = setInterval(async () => {
        try {
          const result = await planAPI.getPlanById(planId);
          if (result.success && result.data) {
            const planData = result.data.plan || result.data;
            const newStatus = planData.status?.toLowerCase();
            
            console.log(`[PlanDetail] Poll result: status=${newStatus}`);
            
            // Update plan data
            setPlan(planData);
            
            // Stop polling if status changed to completed or failed
            if (newStatus === 'completed' || newStatus === 'failed') {
              console.log(`[PlanDetail] Status changed to ${newStatus}, stopping polling`);
              clearInterval(pollInterval);
            }
          }
        } catch (err) {
          console.error('[PlanDetail] Polling error:', err);
        }
      }, 3000); // Poll every 3 seconds
      
      // Cleanup on unmount or when status changes
      return () => {
        console.log('[PlanDetail] Clearing polling interval');
        clearInterval(pollInterval);
      };
    }
  }, [plan?.status, planId, isPublicView]);

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

  // Extract activity POIs with coordinates from entire itinerary (continuous numbering)
  const activityPOIs = useMemo(() => {
    if (!plan?.itinerary) return [];
    const pois = [];
    let globalIndex = 0;
    
    plan.itinerary.forEach((day, dayIndex) => {
      const activities = day.activities || [];
      const estimatedTimes = day.estimated_times || [];
      const featuredImages = (day.featured_images || []).map((img) => buildPhotoUrl(img, googleMapsApiKey));
      const dayTypes = day.types || []; // Extract types array from day data
      
      let poiIndexInDay = 0;
      activities.forEach((activity, actIndex) => {
        globalIndex++;
        const data = extractActivityData(activity);
        if (data.isString) return;
        if (!data.location?.latitude || !data.location?.longitude) return;
        
        // Parse estimated time for this activity
        const { startTime, durationMinutes } = parseEstimatedTime(estimatedTimes[actIndex]);
        
        // Get types for this POI (array of category strings)
        const poiTypes = dayTypes[poiIndexInDay] || [data.category].filter(Boolean);
        const primaryType = poiTypes[0] || data.category || 'attraction';
        
        pois.push({
          id: globalIndex,
          dayIndex: dayIndex + 1,
          name: data.poiName,
          lat: data.location.latitude,
          lng: data.location.longitude,
          time: startTime || data.time || null,
          duration: durationMinutes || data.duration || null,
          category: primaryType, // Use first type as primary category
          types: poiTypes, // Store full types array
          markerColor: getMarkerColor(primaryType), // Category-themed color
          rating: data.rating || null,
          reviewCount: activity.poi?.user_ratings_total || activity.user_ratings_total || null,
          imageUrl: featuredImages[poiIndexInDay] || null // Store URL but don't load immediately
        });
        poiIndexInDay++;
      });
    });
    
    return pois;
  }, [plan, googleMapsApiKey]);

  // Extract accommodation POIs separately (no numbering, separate array)
  const accommodationPOIs = useMemo(() => {
    if (!plan?.itinerary) return [];
    const accommodations = [];
    
    plan.itinerary.forEach((day, dayIndex) => {
      // Add accommodation POI if has valid location (GeoJSON format: [lng, lat])
      if (day.accommodation_location && day.accommodation_location.length === 2) {
        const [lat, lng] = day.accommodation_location;
        
        // Validate coordinates (must be numbers and in valid range)
        if (typeof lat === 'number' && typeof lng === 'number' && 
            lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
          
          const accId = day.accommodation_id || `acc_day${dayIndex + 1}`;
          
          // Check if already added (avoid duplicates across days)
          if (!accommodations.some(acc => acc.accommodationId === accId)) {
            accommodations.push({
              id: accId, // Use accommodation_id as unique identifier (not a number)
              accommodationId: accId,
              dayIndex: dayIndex + 1,
              name: day.accommodation_name || 'Nơi lưu trú',
              lat: lat,
              lng: lng,
              category: 'accommodation',
              types: ['accommodation', 'hotel'],
              markerColor: getMarkerColor('accommodation'), // Purple color
              rating: null,
              reviewCount: null,
              imageUrl: null,
              isAccommodation: true,
              address: day.accommodation_address,
              checkIn: day.check_in_time,
              checkOut: day.check_out_time,
              changed: day.accommodation_changed,
              changeReason: day.accommodation_change_reason
            });
          }
        }
      }
    });
    
    return accommodations;
  }, [plan]);

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

  // Map center (first activity POI with coords or destination location)
  const mapCenter = useMemo(() => {
    if (activityPOIs.length > 0) {
      return { lat: activityPOIs[0].lat, lng: activityPOIs[0].lng };
    }
    
    const location = plan?.destination_location;
    if (location?.latitude && location?.longitude) {
      return { lat: location.latitude, lng: location.longitude };
    }
    
    return { lat: 16.0544, lng: 108.2428 }; // Default: Da Nang
  }, [activityPOIs, plan]);

  const destinationLocation = useMemo(() => {
    const loc = plan?.destination_location;
    if (loc?.latitude && loc?.longitude) {
      return { lat: loc.latitude, lng: loc.longitude };
    }
    return null;
  }, [plan]);

  // Calculate trip summary (costs, accommodations, preferences)
  const tripSummary = useMemo(() => {
    if (!plan?.itinerary) return null;
    
    let totalCost = 0;
    const accommodations = [];
    const perDayBudget = Number(plan?.preferences?.budget) || 0;
    const numDays = plan.itinerary.length;
    
    plan.itinerary.forEach((day) => {
      if (day.estimated_cost_vnd) {
        totalCost += day.estimated_cost_vnd;
      }
      if (day.accommodation_name && !accommodations.some(a => a.name === day.accommodation_name)) {
        // Extract and validate location from GeoJSON format [lng, lat]
        let location = null;
        if (day.accommodation_location && day.accommodation_location.length === 2) {
          const [lng, lat] = day.accommodation_location;
          // Validate coordinates
          if (typeof lat === 'number' && typeof lng === 'number' && 
              lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
            location = { latitude: lat, longitude: lng };
          }
        }
        
        accommodations.push({
          name: day.accommodation_name,
          address: day.accommodation_address,
          checkIn: day.check_in_time,
          checkOut: day.check_out_time,
          location: location,
          accommodation_id: day.accommodation_id,
          changed: day.accommodation_changed,
          changeReason: day.accommodation_change_reason
        });
      }
    });
    
    return {
      totalCost,
      accommodations,
      preferences: plan.preferences || {},
      numDays,
      numPOIs: activityPOIs.length, // Count only activity POIs (not accommodations)
      playfulBudgetTotal: perDayBudget * numDays
    };
  }, [plan, activityPOIs]);

  // Format VND currency
  const formatVND = (amount) => {
    if (!amount) return '0 ₫';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const clampMapZoom = useCallback((map) => {
    if (!map) return;
    const currentZoom = map.getZoom();
    if (currentZoom && currentZoom > 17) {
      map.setZoom(17);
    }
  }, []);

  // Handle map load
  const onMapLoad = useCallback((mapInstance) => {
    mapRef.current = mapInstance;
    
    // Fit bounds to show all POIs (both activities and accommodations) initially
    const allPOIsForBounds = [...activityPOIs, ...accommodationPOIs];
    if (allPOIsForBounds.length > 1) {
      const bounds = new window.google.maps.LatLngBounds();
      allPOIsForBounds.forEach(poi => bounds.extend({ lat: poi.lat, lng: poi.lng }));
      mapInstance.fitBounds(bounds, { padding: 50 });
      window.google.maps.event.addListenerOnce(mapInstance, 'bounds_changed', () => clampMapZoom(mapInstance));
    } else {
      clampMapZoom(mapInstance);
    }
  }, [activityPOIs, accommodationPOIs, clampMapZoom]);

  // Handle activity hover - focus on map (search in both activity and accommodation POIs)
  const handleActivityHover = (globalIndex) => {
    const poi = activityPOIs.find(p => p.id === globalIndex) || accommodationPOIs.find(p => p.id === globalIndex);
    const map = mapRef.current;
    if (!poi || !map) return;

    // Store pre-hover view once to restore later
    if (!hoveredPOI && !preHoverViewRef.current) {
      preHoverViewRef.current = {
        zoom: map.getZoom(),
        center: map.getCenter(),
      };
    }

    if (hoveredPOI === poi.id) return;

    map.panTo({ lat: poi.lat, lng: poi.lng });
    const currentZoom = map.getZoom();
    const targetZoom = Math.min(Math.max(currentZoom ?? 15, 15), 17);
    if (!currentZoom || Math.abs(targetZoom - currentZoom) > 0.01) {
      map.setZoom(targetZoom);
    }
    clampMapZoom(map);
    setHoveredPOI(poi.id);
  };

  // Handle mouse leave - keep map at current POI position (don't reset)
  const handleActivityLeave = () => {
    // Don't reset map view - keep it at the last hovered POI
    // Only clear the hovered state for visual feedback
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
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 animate-spin text-gray-400 dark:text-gray-500" />
          <p className="text-gray-500 dark:text-gray-400 font-medium">Đang tải kế hoạch...</p>
        </div>
      </div>
    );
  }

  // Check plan generation status
  const planStatus = plan?.status?.toLowerCase();
  const isGenerating = planStatus === 'pending' || planStatus === 'processing';
  const hasFailed = planStatus === 'failed';

  // Error state
  if (error || !plan) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 dark:text-red-400 mb-4">{error || 'Không tìm thấy kế hoạch'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white flex items-center gap-2 mx-auto"
          >
            <ArrowLeft className="w-4 h-4" />
            Quay lại Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Generating Overlay - Show when status is pending or processing */}
      {isGenerating && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-2xl max-w-md mx-4 text-center"
          >
            <Loader2 className="w-16 h-16 animate-spin text-brand-primary mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              {planStatus === 'pending' ? 'Đang chuẩn bị...' : 'Đang tạo lịch trình'}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {planStatus === 'pending' 
                ? 'Hệ thống đang xử lý yêu cầu của bạn. Vui lòng đợi trong giây lát...'
                : 'AI đang phân tích và tạo lịch trình tối ưu cho bạn. Quá trình này có thể mất vài phút...'}
            </p>
            <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <div className="animate-pulse">●</div>
              <div className="animate-pulse delay-75">●</div>
              <div className="animate-pulse delay-150">●</div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Failed Overlay - Show when generation failed */}
      {hasFailed && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-2xl max-w-md mx-4 text-center"
          >
            <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">⚠️</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              Không thể tạo lịch trình
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Đã xảy ra lỗi khi tạo lịch trình. Vui lòng thử lại hoặc điều chỉnh yêu cầu.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Quay lại
              </button>
              <button
                onClick={() => setShowRegenerateModal(true)}
                className="flex-1 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-secondary"
              >
                Thử lại
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-full px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
            <div>
              {/* Editable Title - only for owner view */}
              {isPublicView ? (
                <h1 className="font-poppins font-bold text-xl text-gray-900 dark:text-white">
                  {plan.title || plan.destination}
                </h1>
              ) : (
                <EditableTitle
                  value={plan.title || plan.destination}
                  onSave={handleSaveTitle}
                  level="h1"
                />
              )}
              <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mt-1">
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
                onClick={() => setShowRegenerateModal(true)}
                disabled={regenerateLoading}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  regenerateLoading
                    ? 'border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                    : 'border-brand-primary text-brand-primary bg-white dark:bg-gray-800 hover:bg-brand-muted dark:hover:bg-brand-primary/10'
                }`}
              >
                <Loader2 className={`w-4 h-4 ${regenerateLoading ? 'animate-spin' : ''}`} />
                <span className="text-sm font-semibold">Tái tạo kế hoạch</span>
              </motion.button>
            )}

            {!isPublicView && (
              <motion.button
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleToggleShare}
                disabled={shareLoading}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                  shareState.isPublic
                    ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50'
                    : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
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
                  ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-600 cursor-not-allowed'
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
        <main className="w-[40%] overflow-y-auto px-8 py-6 min-w-100 border-r border-gray-200 dark:border-gray-700">
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
                  className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden"
                >
                  {/* Day Header */}
                  <div className="bg-brand-primary text-white px-6 py-4">
                    <h2 className="font-poppins font-bold text-lg flex items-center flex-wrap gap-2">
                      <span>Ngày {dayIndex + 1}</span>
                      {/* Editable start date for Day 1 only (owner view) */}
                      {dayIndex === 0 && !isPublicView ? (
                        <span className="font-normal text-gray-200">
                          - Bắt đầu từ: 
                          <span className="ml-1 inline-block bg-white/10 rounded px-2 py-0.5 hover:bg-white/20 transition-colors">
                            <EditableDate
                              value={day.date || plan.start_date}
                              onSave={handleSaveStartDate}
                              variant="dark"
                            />
                          </span>
                        </span>
                      ) : day.date ? (
                        <span className="font-normal text-gray-300">
                          - {formatDate(day.date)}
                        </span>
                      ) : null}
                    </h2>
                    {day.theme && (
                      <p className="text-gray-300 text-sm mt-1">{day.theme}</p>
                    )}
                  </div>

                  <DayItinerary
                    day={day}
                    dayNumber={dayIndex + 1}
                    startIndex={startIndex}
                    isPublicView={isPublicView}
                    onSave={handleSaveDayItinerary}
                    location={destinationLocation}
                    onHover={handleActivityHover}
                    onLeave={handleActivityLeave}
                  />
                </motion.div>
              );
            })}

            {/* Summary Card */}
            {plan.summary && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: (plan.itinerary?.length || 0) * 0.1 }}
                className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm p-6"
              >
                <h3 className="font-poppins font-bold text-lg text-gray-900 dark:text-white mb-3">
                  📋 Tổng kết chuyến đi
                </h3>
                <p className="text-gray-700 dark:text-gray-300">{plan.summary}</p>
              </motion.div>
            )}
          </div>
        </main>

        {/* Right: Sticky Google Map with Info Panels */}
        <aside className="w-[60%] bg-white dark:bg-gray-800 shrink-0 sticky top-18.25 h-[calc(100vh-73px)]">
          {loadError && (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              Lỗi tải Google Maps
            </div>
          )}
          
          {!isLoaded && !loadError && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400 dark:text-gray-500" />
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
                {/* Render activity POI markers (with numbers 1, 2, 3...) */}
                {activityPOIs.map((poi) => {
                  const TypeIconComponent = getTypeIcon(poi.category);
                  const isHovered = hoveredPOI === poi.id;
                  
                  // Handle marker hover with delay to prevent accidental image loading
                  // User must hover for 300ms before image is loaded (saves API costs)
                  const handleMarkerEnter = () => {
                    // Clear any existing timeout
                    if (hoverTimeoutRef.current) {
                      clearTimeout(hoverTimeoutRef.current);
                    }
                    
                    // Set delayed hover - show info window after 300ms
                    hoverTimeoutRef.current = setTimeout(() => {
                      setHoveredPOI(poi.id);
                      
                      // Lazy load image if not cached (TTL: 3 days for POI featured images)
                      if (poi.imageUrl && !hoveredImageCache[poi.id]) {
                        const fullUrl = buildPhotoUrl(poi.imageUrl, googleMapsApiKey);
                        
                        preloadAndCacheImage(fullUrl, 'poi_featured')
                          .then((url) => {
                            setHoveredImageCache(prev => ({ ...prev, [poi.id]: url }));
                          })
                          .catch((err) => {
                            console.error('Failed to load POI image:', err);
                            // Fallback: still show the URL even if preload fails
                            setHoveredImageCache(prev => ({ ...prev, [poi.id]: fullUrl }));
                          });
                      }
                    }, 300); // 300ms delay before showing info window and loading image
                  };
                  
                  // Handle marker leave - cancel pending hover timeout
                  const handleMarkerLeave = () => {
                    if (hoverTimeoutRef.current) {
                      clearTimeout(hoverTimeoutRef.current);
                      hoverTimeoutRef.current = null;
                    }
                    setHoveredPOI(null);
                  };
                  
                  return (
                    <OverlayView
                      key={poi.id}
                      position={{ lat: poi.lat, lng: poi.lng }}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0.85 }}
                        animate={{ 
                          scale: isHovered ? 1.08 : 0.95, 
                          opacity: isHovered ? 1 : 0.9,
                          zIndex: isHovered ? 100 : 1
                        }}
                        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                        className="relative cursor-pointer flex flex-col items-center"
                        onMouseEnter={handleMarkerEnter}
                        onMouseLeave={handleMarkerLeave}
                        style={{ 
                          position: 'relative', 
                          zIndex: isHovered ? 100 : 1,
                          transform: 'translate(-50%, -100%)' // Center marker on coordinates
                        }}
                      >
                        {/* Marker container - Icon-first design */}
                        <div 
                          className={`w-11 h-11 rounded-full border-2 shadow-md flex items-center justify-center transition-all duration-200 ${
                            isHovered 
                              ? 'border-white ring-3 ring-white/50 shadow-xl' 
                              : 'border-white shadow-lg'
                          }`}
                          style={{
                            backgroundColor: poi.markerColor,
                            opacity: isHovered ? 1 : 0.9,
                            transform: isHovered ? 'scale(1.04)' : 'scale(1)',
                            transition: 'opacity 180ms ease, transform 180ms ease'
                          }}
                        >
                          {/* Centered type icon */}
                          {TypeIconComponent && <TypeIconComponent className="w-6 h-6 text-white" />}
                          
                          {/* Number badge at top-right (activity POIs have numbers) */}
                          <div className="absolute -top-1 -right-1 w-5 h-5 bg-gray-900 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md border border-white">
                            {poi.id}
                          </div>
                        </div>
                        
                        {/* POI name label below marker */}
                        <div 
                          className={`mt-1 px-2 py-0.5 bg-white rounded-md shadow-sm border transition-all duration-200 max-w-32 ${
                            isHovered 
                              ? 'border-gray-300 shadow-md' 
                              : 'border-gray-200'
                          }`}
                          style={{ opacity: isHovered ? 1 : 0.9, transform: isHovered ? 'translateY(-2px)' : 'translateY(0)' }}
                        >
                          <p className="text-xs font-semibold text-gray-800 truncate text-center">
                            {poi.name}
                          </p>
                        </div>
                      </motion.div>
                    </OverlayView>
                  );
                })}

                {/* Render accommodation POI markers (with hotel emoji 🏨, no numbers) */}
                {accommodationPOIs.map((poi) => {
                  const TypeIconComponent = getTypeIcon(poi.category);
                  const isHovered = hoveredPOI === poi.id;
                  
                  // Handle marker hover with delay (same as activity POIs)
                  const handleAccommodationEnter = () => {
                    if (hoverTimeoutRef.current) {
                      clearTimeout(hoverTimeoutRef.current);
                    }
                    hoverTimeoutRef.current = setTimeout(() => {
                      setHoveredPOI(poi.id);
                    }, 300);
                  };
                  
                  const handleAccommodationLeave = () => {
                    if (hoverTimeoutRef.current) {
                      clearTimeout(hoverTimeoutRef.current);
                      hoverTimeoutRef.current = null;
                    }
                    setHoveredPOI(null);
                  };
                  
                  return (
                    <OverlayView
                      key={poi.id}
                      position={{ lat: poi.lat, lng: poi.lng }}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0.85 }}
                        animate={{ 
                          scale: isHovered ? 1.08 : 0.95, 
                          opacity: isHovered ? 1 : 0.9,
                          zIndex: isHovered ? 100 : 1
                        }}
                        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                        className="relative cursor-pointer flex flex-col items-center"
                        onMouseEnter={handleAccommodationEnter}
                        onMouseLeave={handleAccommodationLeave}
                        style={{ 
                          position: 'relative', 
                          zIndex: isHovered ? 100 : 1,
                          transform: 'translate(-50%, -100%)' // Center marker on coordinates
                        }}
                      >
                        {/* Marker container - Icon-first design */}
                        <div 
                          className={`w-11 h-11 rounded-full border-2 shadow-md flex items-center justify-center transition-all duration-200 ${
                            isHovered 
                              ? 'border-white ring-3 ring-white/50 shadow-xl' 
                              : 'border-white shadow-lg'
                          }`}
                          style={{
                            backgroundColor: poi.markerColor,
                            opacity: isHovered ? 1 : 0.9,
                            transform: isHovered ? 'scale(1.04)' : 'scale(1)',
                            transition: 'opacity 180ms ease, transform 180ms ease'
                          }}
                        >
                          {/* Centered type icon */}
                          {TypeIconComponent && <TypeIconComponent className="w-6 h-6 text-white" />}
                          
                          {/* Hotel emoji badge at top-right (accommodations show 🏨 instead of numbers) */}
                          <div className="absolute -top-1 -right-1 w-5 h-5 bg-purple-500 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md border border-white">
                            🏨
                          </div>
                        </div>
                        
                        {/* POI name label below marker */}
                        <div 
                          className={`mt-1 px-2 py-0.5 bg-white rounded-md shadow-sm border transition-all duration-200 max-w-32 ${
                            isHovered 
                              ? 'border-gray-300 shadow-md' 
                              : 'border-gray-200'
                          }`}
                          style={{ opacity: isHovered ? 1 : 0.9, transform: isHovered ? 'translateY(-2px)' : 'translateY(0)' }}
                        >
                          <p className="text-xs font-semibold text-gray-800 truncate text-center">
                            {poi.name}
                          </p>
                        </div>
                      </motion.div>
                    </OverlayView>
                  );
                })}


                {/* InfoWindow for hovered POI - Card-style design with image */}
                {hoveredPOI && (() => {
                  const poi = activityPOIs.find(p => p.id === hoveredPOI) || accommodationPOIs.find(p => p.id === hoveredPOI);
                  if (!poi) return null;
                  const isAccomm = isAccommodation(poi.category);
                  const cachedImage = hoveredImageCache[poi.id]; // Get cached image
                  
                  return (
                    <InfoWindow
                      position={{ lat: poi.lat, lng: poi.lng }}
                      onCloseClick={() => setHoveredPOI(null)}
                      options={{ 
                        disableAutoPan: true, 
                        pixelOffset: new window.google.maps.Size(0, -60),
                        maxWidth: 280
                      }}
                    >
                      <div className="w-60 overflow-hidden -m-2">
                        {/* Featured image with overlay icons */}
                        <div className="relative">
                          {cachedImage ? (
                            <img 
                              src={cachedImage}
                              alt={poi.name}
                              className="w-full h-32 object-cover"
                            />
                          ) : (
                            <div className="w-full h-32 bg-linear-to-br from-gray-200 to-gray-300 flex items-center justify-center">
                              <MapPin className="w-8 h-8 text-gray-400" />
                            </div>
                          )}
                          
                          {/* Overlay buttons on image */}
                          <div className="absolute top-2 right-2 flex items-center gap-1.5">
                            <button className="p-1.5 bg-white/90 rounded-full shadow-sm hover:bg-white transition-colors">
                              <Heart className="w-3.5 h-3.5 text-gray-600" />
                            </button>
                            <button className="p-1.5 bg-white/90 rounded-full shadow-sm hover:bg-white transition-colors">
                              <Plus className="w-3.5 h-3.5 text-gray-600" />
                            </button>
                          </div>
                          
                          {/* Day badge */}
                          <div className="absolute bottom-2 left-2">
                            <span className={`text-[10px] font-medium px-2 py-1 rounded-full shadow-sm ${
                              isAccomm 
                                ? 'bg-purple-500 text-white' 
                                : 'bg-brand-primary text-white'
                            }`}>
                              Ngày {poi.dayIndex}
                            </span>
                          </div>
                        </div>
                        
                        {/* Content section */}
                        <div className="p-3 bg-white">
                          {/* Location name with icon */}
                          <div className="flex items-start gap-2">
                            <MapPin className={`w-4 h-4 mt-0.5 shrink-0 ${
                              isAccomm ? 'text-purple-500' : 'text-brand-primary'
                            }`} />
                            <div className="flex-1 min-w-0">
                              <h4 className={`font-semibold text-sm leading-tight ${
                                isAccomm ? 'text-purple-700' : 'text-gray-900'
                              }`}>
                                {poi.name}
                              </h4>
                              {poi.address && (
                                <p className="text-[10px] text-gray-400 truncate mt-0.5">
                                  {poi.address}
                                </p>
                              )}
                            </div>
                          </div>
                          
                          {/* Description or activity info */}
                          {poi.description && (
                            <p className="text-xs text-gray-500 mt-2 line-clamp-2">
                              {poi.description}
                            </p>
                          )}
                          
                          {/* Rating & Time row */}
                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
                            <div className="flex items-center gap-2">
                              {poi.rating && (
                                <span className="inline-flex items-center gap-0.5 text-xs font-medium text-amber-600">
                                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                  {poi.rating.toFixed(1)}
                                </span>
                              )}
                              {poi.reviewCount && (
                                <span className="text-[10px] text-gray-400">
                                  ({poi.reviewCount.toLocaleString()})
                                </span>
                              )}
                            </div>
                            
                            {poi.time && (
                              <span className="text-[10px] text-gray-500 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {poi.time}
                              </span>
                            )}
                          </div>
                          
                          {/* Accommodation badge */}
                          {isAccomm && (
                            <div className="mt-2 flex items-center gap-1.5">
                              <span className="text-[10px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                                🏨 Lưu trú
                              </span>
                            </div>
                          )}
                        </div>
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
                    <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                      {/* Toggle Header */}
                      <button 
                        onClick={() => setShowInfoPanel(!showInfoPanel)}
                        className="w-full px-4 py-3 flex items-center justify-between bg-brand-muted dark:bg-brand-primary/20 hover:bg-brand-muted/80 dark:hover:bg-brand-primary/30 transition-colors"
                      >
                        <span className="font-poppins font-semibold text-brand-primary dark:text-brand-muted flex items-center gap-2">
                          <Settings2 className="w-4 h-4" />
                          Thông tin chuyến đi
                        </span>
                        {showInfoPanel ? (
                          <ChevronDown className="w-5 h-5 text-brand-primary dark:text-brand-muted" />
                        ) : (
                          <ChevronUp className="w-5 h-5 text-brand-primary dark:text-brand-muted" />
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
                                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase flex items-center gap-1">
                                  <CreditCard className="w-3 h-3" />
                                  Chi phí ước tính
                                </h4>
                                <p className="text-lg font-bold text-brand-primary dark:text-brand-muted">
                                  {formatVND(tripSummary.totalCost)}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                  ~{formatVND(Math.round(tripSummary.totalCost / tripSummary.numDays))}/ngày
                                </p>
                                {tripSummary.playfulBudgetTotal > 0 && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400">Ước tính vui: {formatVND(tripSummary.playfulBudgetTotal)}</p>
                                )}
                              </div>

                              {/* Accommodation Info */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase flex items-center gap-1">
                                  <Bed className="w-3 h-3" />
                                  Lưu trú
                                </h4>
                                {tripSummary.accommodations.length > 0 ? (
                                  <div className="space-y-1">
                                    {tripSummary.accommodations.slice(0, 2).map((acc, i) => (
                                      <p 
                                        key={i} 
                                        className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate cursor-pointer hover:text-brand-primary dark:hover:text-brand-muted transition-colors" 
                                        title={acc.name}
                                        onMouseEnter={() => {
                                          console.log("acc: ", acc);
                                          const accPOI = accommodationPOIs.find((poi) => {
                                            console.log("poi: ", poi);
                                            
                                            const matchId = acc.accommodation_id && poi.accommodationId === acc.accommodation_id;
                                            const matchLocation = acc.location && Math.abs(poi.lat - acc.location[1]) < 1e-6 && Math.abs(poi.lng - acc.location[0]) < 1e-6; // GeoJSON: [lng, lat]
                                            const matchName = poi.name === acc.name;
                                            return matchId || matchLocation || matchName;
                                          });
                                          if (accPOI) {
                                            handleActivityHover(accPOI.id);
                                          }
                                        }}
                                        onMouseLeave={handleActivityLeave}
                                      >
                                        🏨 {acc.name}
                                      </p>
                                    ))}
                                    {tripSummary.accommodations.length > 2 && (
                                      <p className="text-xs text-gray-400 dark:text-gray-500">
                                        +{tripSummary.accommodations.length - 2} nơi khác
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <p className="text-sm text-gray-400 dark:text-gray-500">Chưa có thông tin</p>
                                )}
                              </div>

                              {/* Preferences */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase flex items-center gap-1">
                                  <Settings2 className="w-3 h-3" />
                                  Tùy chọn
                                </h4>
                                <div className="space-y-1 text-sm">
                                  {tripSummary.preferences.budget && (
                                    <p className="text-gray-700 dark:text-gray-300">
                                      💰 {formatVND(tripSummary.preferences.budget)}
                                    </p>
                                  )}
                                  {tripSummary.preferences.budget_level && (
                                    <p className="text-gray-700 dark:text-gray-300 capitalize">
                                      📊 {tripSummary.preferences.budget_level}
                                    </p>
                                  )}
                                  {tripSummary.preferences.pace && (
                                    <p className="text-gray-700 dark:text-gray-300 capitalize">
                                      🚶 {tripSummary.preferences.pace}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="px-4 pb-4 flex items-center justify-center gap-6 text-sm text-gray-500 dark:text-gray-400">
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

      {!isPublicView && (
        console.log("plan before regenerate modal: ", plan),
        <RegeneratePlanModal
          isOpen={showRegenerateModal}
          onClose={() => setShowRegenerateModal(false)}
          onSubmit={handleRegeneratePlan}
          initialBudget={plan?.preferences?.budget || 3500000}
          initialBudgetLevel={plan?.preferences?.budget_level || plan?.budget_level || 'medium'}
          initialPace={plan?.preferences?.pace || plan?.pace || 'moderate'}
          initialTypes={plan?.preferences?.types || plan?.preferences?.interests || plan?.preferences?.types || []}
          initUserNotes={plan?.preferences?.user_notes || ''}
          currentNumDays={plan?.num_days || 3}
          planTitle={plan?.title || ''}
          loading={regenerateLoading}
        />
      )}
    </div>
  );
}
