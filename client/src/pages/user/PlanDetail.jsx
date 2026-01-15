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

import { Circle, GoogleMap, OverlayView, useJsApiLoader } from '@react-google-maps/api';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bed,
  Calendar,
  Camera,
  ChevronDown,
  ChevronUp,
  Church,
  ClipboardList,
  Clock,
  Coffee,
  Copy,
  CreditCard,
  Dumbbell,
  Film,
  Footprints,
  Globe,
  Hospital,
  Heart,
  Landmark,
  List,
  Loader2,
  Lock,
  Map,
  MapPin,
  Moon,
  Mountain,
  Music,
  Palmtree,
  Plane,
  Scroll,
  Search,
  Settings2,
  ShoppingBag,
  Sparkles,
  Star,
  Train,
  TreePine,
  Users,
  Utensils,
  UtensilsCrossed,
  Wallet,
  Wine,
  X
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { EditableDate, EditableTitle } from '../../components/common/EditableField';
import Tooltip from '../../components/common/Tooltip';
import DayItinerary from '../../components/plan/DayItinerary';
import RegeneratePlanModal from '../../components/plan/RegeneratePlanModal';
import planAPI from '../../services/planApi';
import searchAPI from '../../services/searchApi';
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

// Nearby search category options (matches CreatePlan interests)
// Backend converts these IDs to Google Places API types via type_mapping.py
const NEARBY_CATEGORY_OPTIONS = [
  { id: 'beach', label: 'Beach', Icon: Palmtree },
  { id: 'culture', label: 'Culture', Icon: Landmark },
  { id: 'food', label: 'Food', Icon: Utensils },
  { id: 'cafe', label: 'Cafe', Icon: Coffee },
  { id: 'nightlife', label: 'Nightlife', Icon: Moon },
  { id: 'nature', label: 'Nature', Icon: TreePine },
  { id: 'adventure', label: 'Adventure', Icon: Mountain },
  { id: 'shopping', label: 'Shopping', Icon: ShoppingBag },
  { id: 'relaxation', label: 'Relaxation', Icon: Sparkles },
  { id: 'history', label: 'History', Icon: Scroll },
  { id: 'photography', label: 'Photography', Icon: Camera },
  { id: 'family', label: 'Family', Icon: Users },
  { id: 'romantic', label: 'Romantic', Icon: Heart },
];

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

// Format duration in English
const formatDuration = (minutes) => {
  if (!minutes) return null;
  const numMinutes = typeof minutes === 'string' ? parseInt(minutes) : minutes;
  if (isNaN(numMinutes)) return minutes; // Return as-is if not parseable
  if (numMinutes >= 60) {
    const hours = Math.floor(numMinutes / 60);
    const mins = numMinutes % 60;
    return mins > 0 ? `${hours}h${mins}m` : `${hours} hour${hours > 1 ? 's' : ''}`;
  }
  return `${numMinutes} min`;
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

// Check if Google Photos API is enabled via environment variable
// Default: true (production), set VITE_ENABLE_GOOGLE_PHOTOS=false in dev to save costs
const ENABLE_GOOGLE_PHOTOS = import.meta.env.VITE_ENABLE_GOOGLE_PHOTOS !== 'false';

// Normalize photo URL (Google Places photo path → media URL) with caching
const buildPhotoUrl = (url, apiKey) => {
  if (!url) return null;
  
  // Skip Google Photos API if disabled (saves ~$7/1000 photos)
  if (!ENABLE_GOOGLE_PHOTOS && url.startsWith('places/')) {
    return 'https://placehold.co/600x400?text=Photo+Disabled';
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
    : 'http://phamphong.id.vn';
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
  const [activeTab, setActiveTab] = useState('itinerary'); // Mobile tab: 'itinerary' | 'map'
  const [showInfoPanel, setShowInfoPanel] = useState(true);
  const [shareState, setShareState] = useState({ isPublic: false, shareToken: null, shareUrl: null });
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [hoveredImageCache, setHoveredImageCache] = useState({}); // Lazy-loaded images cache
  const [showRegenerateModal, setShowRegenerateModal] = useState(false);
  const [regenerateLoading, setRegenerateLoading] = useState(false);
  
  // Nearby search states
  const [nearbyPOIs, setNearbyPOIs] = useState([]);
  const [nearbySearching, setNearbySearching] = useState(false);
  const [showNearbyPanel, setShowNearbyPanel] = useState(false);
  const [nearbyRadius, setNearbyRadius] = useState(3);
  const [nearbyCategory, setNearbyCategory] = useState('');
  const [hoveredNearbyPOI, setHoveredNearbyPOI] = useState(null);
  const [addingToDayPOI, setAddingToDayPOI] = useState(null);
  const [nearbySearchCenter, setNearbySearchCenter] = useState(null); // {lat, lng} for center marker
  
  const mapRef = useRef(null);
  const preHoverViewRef = useRef(null);
  const hoverTimeoutRef = useRef(null); // Timeout for delayed hover (prevent accidental image loading)
  const closeTimeoutRef = useRef(null); // Timeout for delayed close (allow moving to popup)
  const [isMouseInPopup, setIsMouseInPopup] = useState(false); // Track if mouse is inside popup

  // ========== INLINE EDITING HANDLERS ==========
  
  // Save plan title
  const handleSaveTitle = useCallback(async (newTitle) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateTitle(planId, newTitle);
    if (result.success) {
      setPlan(prev => ({ ...prev, plan_name: newTitle }));
    } else {
      throw new Error(result.error || 'Failed to update title');
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
      throw new Error(result.error || 'Failed to update start date');
    }
  }, [planId, isPublicView]);

  // Save day notes
  const handleSaveDayNotes = useCallback(async (dayNumber, newNotes) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayNotes(planId, dayNumber, newNotes);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Failed to update notes');
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
      throw new Error(result.error || 'Failed to update activities');
    }
  }, [planId, isPublicView]);

  // Save day accommodation
  const handleSaveAccommodation = useCallback(async (dayNumber, accommodationData) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayAccommodation(planId, dayNumber, accommodationData);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Failed to update accommodation');
    }
  }, [planId, isPublicView]);

  // Save day itinerary (activities + estimated times)
  const handleSaveDayItinerary = useCallback(async (dayNumber, activities, estimatedTimes, poiIds, types, featuredImages) => {
    if (!planId || isPublicView) return;
    const result = await planAPI.updateDayActivitiesWithTimes(planId, dayNumber, activities, estimatedTimes, poiIds, types, featuredImages);
    if (result.success && result.data) {
      setPlan(result.data);
    } else {
      throw new Error(result.error || 'Failed to update itinerary');
    }
  }, [planId, isPublicView]);

  // Add activity from POI search
  const handleAddActivityFromPOI = useCallback(async (dayNumber, poiId, note) => {
    console.log('[PlanDetail] handleAddActivityFromPOI called:', { dayNumber, poiId, note });
    if (!planId || isPublicView) {
      console.log('[PlanDetail] Skipping - no planId or isPublicView');
      return;
    }
    console.log('[PlanDetail] Calling planAPI.addActivityFromPOI...');
    const result = await planAPI.addActivityFromPOI(planId, dayNumber, poiId, note);
    console.log('[PlanDetail] API result:', result);
    if (result.success && result.data) {
      const planData = result.data.plan || result.data;
      setPlan(planData);
      console.log('[PlanDetail] Plan updated successfully');
    } else {
      throw new Error(result.error || 'Failed to add activity');
    }
  }, [planId, isPublicView]);

  const handleRegeneratePlan = useCallback(async (payload) => {
    if (!planId || isPublicView) return;
    setRegenerateLoading(true);
    try {
      const updateResult = await planAPI.updatePlan(planId, payload);
      if (!updateResult.success) {
        throw new Error(updateResult.error || 'Failed to update plan');
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

  // Search nearby POIs on map
  const handleSearchNearby = useCallback(async () => {
    if (!mapRef.current) return;
    
    const center = mapRef.current.getCenter();
    const lat = center.lat();
    const lng = center.lng();
    
    // Store center for visualization
    setNearbySearchCenter({ lat, lng });
    setNearbySearching(true);
    
    try {
      const options = { limit: 20 };
      if (nearbyCategory) {
        options.types = nearbyCategory;
      }
      
      const result = await searchAPI.searchNearby(lat, lng, nearbyRadius, options);
      
      if (result?.results) {
        const pois = result.results.map((poi, idx) => ({
          id: `nearby_${poi.poi_id || idx}`,
          poi_id: poi.poi_id,
          name: poi.name,
          lat: poi.location?.latitude || poi.location?.lat,
          lng: poi.location?.longitude || poi.location?.lng,
          address: poi.formatted_address || poi.address,
          rating: poi.rating,
          reviewCount: poi.total_reviews || poi.user_ratings_total,
          category: poi.types?.[0] || poi.primary_type || 'attraction',
          types: poi.types || [],
          markerColor: getMarkerColor(poi.types?.[0] || 'attraction'),
          imageUrl: poi.photo_url || null,
          distance_km: poi.distance_km
        }));
        setNearbyPOIs(pois);
      }
    } catch (err) {
      console.error('[SearchNearby] failed:', err);
    } finally {
      setNearbySearching(false);
    }
  }, [nearbyRadius, nearbyCategory]);

  // Clear nearby search results
  const handleClearNearby = useCallback(() => {
    setNearbyPOIs([]);
    setHoveredNearbyPOI(null);
    setAddingToDayPOI(null);
    setNearbySearchCenter(null); // Clear center marker
  }, []);

  // Add nearby POI to specific day
  const handleAddNearbyToDay = useCallback(async (poi, dayNumber) => {
    if (!planId || isPublicView) return;
    
    try {
      await handleAddActivityFromPOI(dayNumber, poi.poi_id, null);
      setAddingToDayPOI(null);
      // Remove added POI from nearby list
      setNearbyPOIs(prev => prev.filter(p => p.id !== poi.id));
    } catch (err) {
      console.error('[AddNearbyToDay] failed:', err);
    }
  }, [planId, isPublicView, handleAddActivityFromPOI]);

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
          setError(result.error || 'Plan not found');
        }
      } catch (err) {
        console.error('Error fetching plan:', err);
        setError('Error loading plan');
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
      poiName: activity.poi_name || poi.name || 'Location',
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
              name: day.accommodation_name || 'Accommodation',
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
          <p className="text-gray-500 dark:text-gray-400 font-medium">Loading plan...</p>
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
          <p className="text-red-500 dark:text-red-400 mb-4">{error || 'Plan not found'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white flex items-center gap-2 mx-auto"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
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
              {planStatus === 'pending' ? 'Preparing...' : 'Creating itinerary'}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {planStatus === 'pending' 
                ? 'Processing your request. Please wait a moment...'
                : 'AI is analyzing and creating an optimal itinerary for you. This may take a few minutes...'}
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
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              Failed to create itinerary
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              An error occurred while creating the itinerary. Please try again or adjust your request.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Go back
              </button>
              <button
                onClick={() => setShowRegenerateModal(true)}
                className="flex-1 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-secondary"
              >
                Try again
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-full px-4 lg:px-6 py-3 lg:py-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 lg:gap-4 flex-1 min-w-0">
            <button
              onClick={() => navigate('/dashboard')}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors shrink-0"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
            <div className="min-w-0 flex-1">
              {/* Editable Title - only for owner view */}
              {isPublicView ? (
                <h1 className="font-poppins font-bold text-lg lg:text-xl text-gray-900 dark:text-white truncate">
                  {plan.title || plan.destination}
                </h1>
              ) : (
                <EditableTitle
                  value={plan.title || plan.destination}
                  onSave={handleSaveTitle}
                  level="h1"
                  className="truncate"
                />
              )}
              <div className="flex items-center gap-2 lg:gap-4 text-xs lg:text-sm text-gray-500 dark:text-gray-400 mt-1">
                <span className="flex items-center gap-1 truncate">
                  <MapPin className="w-3 h-3 lg:w-4 lg:h-4 shrink-0" />
                  <span className="truncate">{plan.destination}</span>
                </span>
                <span className="flex items-center gap-1 shrink-0">
                  <Calendar className="w-3 h-3 lg:w-4 lg:h-4" />
                  {plan.itinerary?.length || 0}d
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-1 lg:gap-2 shrink-0">
            {isPublicView && (
              <span className="hidden lg:inline text-xs font-medium text-brand-primary bg-brand-muted px-3 py-1 rounded-full">
                Public shared version
              </span>
            )}

            {!isPublicView && (
              <Tooltip content="Regenerate plan" position="bottom">
                <motion.button
                  whileHover={{ scale: 1.02, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowRegenerateModal(true)}
                  disabled={regenerateLoading}
                  className={`flex items-center gap-2 p-2 lg:px-3 lg:py-2 rounded-lg border transition-colors ${
                    regenerateLoading
                      ? 'border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                      : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <Loader2 className={`w-4 h-4 ${regenerateLoading ? 'animate-spin' : ''}`} />
                  <span className="hidden lg:inline text-sm font-semibold">Regenerate plan</span>
                </motion.button>
              </Tooltip>
            )}

            {!isPublicView && (
              <Tooltip content={shareState.isPublic ? 'Click to make private' : 'Click to make public'} position="bottom">
                <motion.button
                  whileHover={{ scale: 1.02, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleToggleShare}
                  disabled={shareLoading}
                  className={`flex items-center gap-2 p-2 lg:px-3 lg:py-2 rounded-lg border transition-colors ${
                    shareState.isPublic
                      ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50'
                      : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  } ${shareLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
                >
                  {shareState.isPublic ? <Globe className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  <span className="hidden lg:inline text-sm font-semibold">
                    {shareState.isPublic ? 'Public' : 'Private'}
                  </span>
                </motion.button>
              </Tooltip>
            )}

            <Tooltip content={shareCopied ? 'Copied!' : 'Copy share link'} position="bottom">
              <motion.button
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleCopyShareLink}
                disabled={!shareState.shareUrl}
                className={`flex items-center gap-2 p-2 lg:px-3 lg:py-2 rounded-lg border transition-colors ${
                  shareState.shareUrl
                    ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    : 'border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-600 cursor-not-allowed'
                }`}
              >
                <Copy className="w-4 h-4" />
                <span className="hidden lg:inline text-sm font-semibold">
                  {shareCopied ? 'Copied!' : 'Copy link'}
                </span>
              </motion.button>
            </Tooltip>
          </div>
        </div>
      </header>

      {/* Mobile Tab Bar */}
      <div className="lg:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-[57px] z-10">
        <div className="flex">
          <button
            onClick={() => setActiveTab('itinerary')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === 'itinerary'
                ? 'text-brand-primary border-b-2 border-brand-primary bg-brand-muted/30'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <List className="w-4 h-4" />
            Itinerary
          </button>
          <button
            onClick={() => setActiveTab('map')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === 'map'
                ? 'text-brand-primary border-b-2 border-brand-primary bg-brand-muted/30'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <Map className="w-4 h-4" />
            Map
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col lg:flex-row h-[calc(100vh-57px-45px)] lg:h-[calc(100vh-73px)]">
        {/* Left: Scrollable Itinerary - All Days */}
        <main className={`${
          activeTab === 'itinerary' ? 'block' : 'hidden'
        } lg:block w-full lg:w-[45%] xl:w-[40%] overflow-y-auto px-4 lg:px-6 xl:px-8 py-4 lg:py-6 lg:min-w-[320px] lg:border-r border-gray-200 dark:border-gray-700 h-full`}>
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
                      <span>Day {dayIndex + 1}</span>
                      {/* Editable start date for Day 1 only (owner view) */}
                      {dayIndex === 0 && !isPublicView ? (
                        <span className="font-normal text-gray-200">
                          - Starting from: 
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
                    onAddActivityFromPOI={handleAddActivityFromPOI}
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
                <h3 className="font-poppins font-bold text-lg text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                  <ClipboardList className="w-5 h-5" /> Trip Summary
                </h3>
                <p className="text-gray-700 dark:text-gray-300">{plan.summary}</p>
              </motion.div>
            )}
          </div>
        </main>

        {/* Right: Sticky Google Map with Info Panels */}
        <aside className={`${
          activeTab === 'map' ? 'block' : 'hidden'
        } lg:block w-full lg:w-[55%] xl:w-[60%] bg-white dark:bg-gray-800 lg:shrink-0 lg:sticky lg:top-18.25 h-full lg:h-[calc(100vh-73px)]`}>
          {loadError && (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
              Error loading Google Maps
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
                  
                  // Handle marker leave - add delay before closing to allow moving to popup
                  const handleMarkerLeave = () => {
                    if (hoverTimeoutRef.current) {
                      clearTimeout(hoverTimeoutRef.current);
                      hoverTimeoutRef.current = null;
                    }
                    // Add 500ms delay before closing to allow user to move mouse to popup
                    closeTimeoutRef.current = setTimeout(() => {
                      if (!isMouseInPopup) {
                        setHoveredPOI(null);
                      }
                    }, 500);
                  };
                  
                  // Handle marker click - toggle info window for mobile (no hover on touch)
                  const handleMarkerClick = () => {
                    // Toggle: if already hovered, close it; otherwise open it
                    if (hoveredPOI === poi.id) {
                      setHoveredPOI(null);
                    } else {
                      setHoveredPOI(poi.id);
                      // Lazy load image if not cached
                      if (poi.imageUrl && !hoveredImageCache[poi.id]) {
                        const fullUrl = buildPhotoUrl(poi.imageUrl, googleMapsApiKey);
                        preloadAndCacheImage(fullUrl, 'poi_featured')
                          .then((url) => {
                            setHoveredImageCache(prev => ({ ...prev, [poi.id]: url }));
                          })
                          .catch((err) => {
                            console.error('Failed to load POI image:', err);
                            setHoveredImageCache(prev => ({ ...prev, [poi.id]: fullUrl }));
                          });
                      }
                    }
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
                        onClick={handleMarkerClick}
                        style={{ 
                          position: 'relative', 
                          zIndex: isHovered ? 100 : 1,
                          transform: 'translate(-50%, -100%)' // Center marker on coordinates
                        }}
                      >
                        {/* Marker container - Icon-first design (90% size) */}
                        <div 
                          className={`w-10 h-10 rounded-full border-2 shadow-md flex items-center justify-center transition-all duration-200 ${
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
                          {TypeIconComponent && <TypeIconComponent className="w-5 h-5 text-white" />}
                          
                          {/* Number badge at top-right (activity POIs have numbers) */}
                          <div className="absolute -top-1 -right-1 w-4 h-4 bg-gray-900 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-md border border-white">
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

                {/* Render accommodation POI markers (with hotel icon, no numbers) */}
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
                    // Add 500ms delay before closing to allow user to move mouse to popup
                    closeTimeoutRef.current = setTimeout(() => {
                      if (!isMouseInPopup) {
                        setHoveredPOI(null);
                      }
                    }, 500);
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
                        {/* Marker container - Icon-first design (90% size) */}
                        <div 
                          className={`w-10 h-10 rounded-full border-2 shadow-md flex items-center justify-center transition-all duration-200 ${
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
                          {TypeIconComponent && <TypeIconComponent className="w-5 h-5 text-white" />}
                          
                          {/* Hotel icon badge at top-right (accommodations show hotel icon instead of numbers) */}
                          <div className="absolute -top-1 -right-1 w-4 h-4 bg-purple-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-md border border-white">
                            <Bed className="w-3 h-3" />
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


                {/* Nearby Search POI Markers (temporary, dashed border styling) */}
                {nearbyPOIs.map((poi) => {
                  const TypeIconComponent = getTypeIcon(poi.category);
                  const isHovered = hoveredNearbyPOI === poi.id;
                  const isAddingDay = addingToDayPOI === poi.id;
                  
                  return (
                    <OverlayView
                      key={poi.id}
                      position={{ lat: poi.lat, lng: poi.lng }}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ 
                          scale: isHovered ? 1.1 : 1, 
                          opacity: 1,
                          zIndex: isHovered ? 150 : 50
                        }}
                        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                        className="relative cursor-pointer flex flex-col items-center"
                        onMouseEnter={() => setHoveredNearbyPOI(poi.id)}
                        onMouseLeave={() => { 
                          if (!isAddingDay) {
                            setHoveredNearbyPOI(null);
                          }
                        }}
                        style={{ 
                          position: 'relative', 
                          zIndex: isHovered ? 150 : 50,
                          transform: 'translate(-50%, -100%)'
                        }}
                      >
                        {/* Marker container - dashed border for temporary markers */}
                        <div 
                          className={`w-10 h-10 rounded-full border-2 border-dashed shadow-md flex items-center justify-center transition-all duration-200 ${
                            isHovered 
                              ? 'border-white ring-2 ring-brand-primary/50 shadow-xl' 
                              : 'border-white/80 shadow-lg'
                          }`}
                          style={{
                            backgroundColor: poi.markerColor,
                            opacity: isHovered ? 1 : 0.85
                          }}
                        >
                          {TypeIconComponent && <TypeIconComponent className="w-5 h-5 text-white" />}
                          
                          {/* Search badge */}
                          <div className="absolute -top-1 -right-1 w-4 h-4 bg-brand-primary text-white text-xs rounded-full flex items-center justify-center shadow-md border border-white">
                            <Search className="w-2.5 h-2.5" />
                          </div>
                        </div>
                        
                        {/* Name label */}
                        <div className={`mt-1 px-2 py-0.5 bg-white/95 rounded-md shadow-sm border border-dashed transition-all duration-200 max-w-36 ${
                          isHovered ? 'border-brand-primary shadow-md' : 'border-gray-300'
                        }`}>
                          <p className="text-xs font-medium text-gray-700 truncate text-center">
                            {poi.name}
                          </p>
                        </div>

                        {/* Day selector dropdown on hover */}
                        {isHovered && plan?.itinerary && !isPublicView && (
                          <motion.div
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="absolute top-full mt-1 bg-white rounded-lg shadow-xl border border-gray-200 p-2 min-w-40 z-200"
                            onMouseEnter={() => setHoveredNearbyPOI(poi.id)}
                            onMouseLeave={() => {
                              setHoveredNearbyPOI(null);
                              setAddingToDayPOI(null);
                            }}
                          >
                            {/* POI Info */}
                            <div className="pb-2 mb-2 border-b border-gray-100">
                              {poi.rating && (
                                <div className="flex items-center gap-1 text-xs text-amber-600 mb-1">
                                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                  {poi.rating.toFixed(1)}
                                  {poi.reviewCount && <span className="text-gray-400">({poi.reviewCount})</span>}
                                </div>
                              )}
                              {poi.distance_km && (
                                <p className="text-[10px] text-gray-400">{poi.distance_km.toFixed(1)} km away</p>
                              )}
                            </div>
                            
                            {/* Add to day buttons */}
                            <p className="text-[10px] font-medium text-gray-500 mb-1.5">Add to:</p>
                            <div className="flex flex-wrap gap-1">
                              {plan.itinerary.map((_, dayIdx) => (
                                <button
                                  key={dayIdx}
                                  onClick={() => handleAddNearbyToDay(poi, dayIdx + 1)}
                                  className="px-2 py-1 text-xs font-medium bg-brand-muted text-brand-primary rounded hover:bg-brand-primary hover:text-white transition-colors"
                                >
                                  Day {dayIdx + 1}
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </motion.div>
                    </OverlayView>
                  );
                })}

                {/* Nearby Search Center Marker and Radius Circle */}
                {nearbySearchCenter && (
                  <>
                    {/* Radius Circle */}
                    <Circle
                      center={nearbySearchCenter}
                      radius={nearbyRadius * 1000} // Convert km to meters
                      options={{
                        fillColor: '#2E571C',
                        fillOpacity: 0.08,
                        strokeColor: '#2E571C',
                        strokeOpacity: 0.5,
                        strokeWeight: 2,
                        strokeDashArray: [4, 4],
                      }}
                    />
                    {/* Center Marker (Crosshair style) */}
                    <OverlayView
                      position={nearbySearchCenter}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <div 
                        className="relative flex items-center justify-center"
                        style={{ transform: 'translate(-50%, -50%)' }}
                      >
                        {/* Outer ring */}
                        <div className="absolute w-8 h-8 rounded-full border-2 border-brand-primary bg-brand-primary/10 animate-pulse" />
                        {/* Center dot */}
                        <div className="w-3 h-3 rounded-full bg-brand-primary border-2 border-white shadow-md z-10" />
                        {/* Crosshairs */}
                        <div className="absolute w-10 h-0.5 bg-brand-primary/50" />
                        <div className="absolute w-0.5 h-10 bg-brand-primary/50" />
                      </div>
                    </OverlayView>
                  </>
                )}

                {/* Custom Popup for hovered POI - OverlayView with flexible positioning */}
                {hoveredPOI && (() => {
                  const poi = activityPOIs.find(p => p.id === hoveredPOI) || accommodationPOIs.find(p => p.id === hoveredPOI);
                  if (!poi) return null;
                  const isAccomm = isAccommodation(poi.category);
                  const cachedImage = hoveredImageCache[poi.id];
                  const TypeIconComponent = getTypeIcon(poi.category);
                  
                  // Calculate popup position: show above or below POI based on viewport position
                  const map = mapRef.current;
                  let showAbove = true; // Default: show above POI
                  if (map) {
                    const projection = map.getProjection();
                    if (projection) {
                      const poiLatLng = new window.google.maps.LatLng(poi.lat, poi.lng);
                      const poiPoint = projection.fromLatLngToPoint(poiLatLng);
                      const bounds = map.getBounds();
                      if (bounds) {
                        const ne = bounds.getNorthEast();
                        const sw = bounds.getSouthWest();
                        const nePoint = projection.fromLatLngToPoint(ne);
                        const swPoint = projection.fromLatLngToPoint(sw);
                        // Check if POI is in top 30% of visible map area
                        const mapHeight = Math.abs(nePoint.y - swPoint.y);
                        const poiRelativeY = Math.abs(poiPoint.y - nePoint.y) / mapHeight;
                        showAbove = poiRelativeY > 0.3; // If POI is in top 30%, show below
                      }
                    }
                  }
                  
                  return (
                    <OverlayView
                      position={{ lat: poi.lat, lng: poi.lng }}
                      mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}
                    >
                      <div 
                        className="relative"
                        style={{ 
                          transform: showAbove 
                            ? 'translate(-50%, calc(-100% - 50px))' // Show above: move up by popup height + marker height
                            : 'translate(-50%, 50px)', // Show below: move down by marker height
                          zIndex: 200
                        }}
                        onMouseEnter={() => {
                          setIsMouseInPopup(true);
                          if (closeTimeoutRef.current) {
                            clearTimeout(closeTimeoutRef.current);
                            closeTimeoutRef.current = null;
                          }
                        }}
                        onMouseLeave={() => {
                          setIsMouseInPopup(false);
                          // Close popup after 300ms when leaving popup
                          closeTimeoutRef.current = setTimeout(() => {
                            setHoveredPOI(null);
                          }, 300);
                        }}
                      >
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9, y: showAbove ? 10 : -10 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ duration: 0.15 }}
                          className="w-56 bg-white rounded-xl shadow-xl overflow-hidden border border-gray-200"
                        >
                          {/* Featured image - square, edge-to-edge, rounded top corners only */}
                          <div className="relative w-full aspect-square">
                            {cachedImage ? (
                              <img 
                                src={cachedImage}
                                alt={poi.name}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full bg-linear-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                                {TypeIconComponent && <TypeIconComponent className="w-12 h-12 text-gray-300" />}
                              </div>
                            )}
                            
                            {/* Day badge on image */}
                            <div className="absolute bottom-2 left-2">
                              <span className={`text-[10px] font-medium px-2 py-1 rounded-full shadow-sm ${
                                isAccomm 
                                  ? 'bg-purple-500 text-white' 
                                  : 'bg-brand-primary text-white'
                              }`}>
                                Day {poi.dayIndex}
                              </span>
                            </div>
                          </div>
                          
                          {/* Content section */}
                          <div className="p-3">
                            {/* Location name with type-based icon */}
                            <div className="flex items-start gap-2">
                              {TypeIconComponent && (
                                <TypeIconComponent className={`w-4 h-4 mt-0.5 shrink-0 ${
                                  isAccomm ? 'text-purple-500' : 'text-brand-primary'
                                }`} />
                              )}
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
                              <div className="mt-2">
                                <span className="text-[10px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1">
                                  <Bed className="w-3 h-3" /> Stay
                                </span>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      </div>
                    </OverlayView>
                  );
                })()}
              </GoogleMap>

              {/* Nearby Search Floating Panel */}
              {!isPublicView && (
                <div className="absolute top-20 right-4 z-20">
                  {/* Search Toggle Button */}
                  {!showNearbyPanel && (
                    <Tooltip content="Search nearby places" position="left">
                      <motion.button
                        initial={{ scale: 0.9 }}
                        animate={{ scale: 1 }}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setShowNearbyPanel(true)}
                        className="p-3 bg-white shadow-lg rounded-full border border-gray-200 hover:border-brand-primary hover:bg-brand-muted transition-colors group"
                      >
                        <Search className="w-5 h-5 text-gray-600 group-hover:text-brand-primary" />
                      </motion.button>
                    </Tooltip>
                  )}

                  {/* Search Panel */}
                  <AnimatePresence>
                    {showNearbyPanel && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: -10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -10 }}
                        className="bg-white rounded-xl shadow-xl border border-gray-200 p-4 min-w-64"
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                            <Search className="w-4 h-4 text-brand-primary" />
                            Search Nearby
                          </h4>
                          <button
                            onClick={() => {
                              setShowNearbyPanel(false);
                              handleClearNearby();
                            }}
                            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                          >
                            <X className="w-4 h-4 text-gray-500" />
                          </button>
                        </div>

                        {/* Radius Selector */}
                        <div className="mb-3">
                          <label className="text-xs font-medium text-gray-600 mb-1.5 block">Radius (km)</label>
                          <div className="flex gap-1">
                            {[1, 3, 5, 10].map(r => (
                              <button
                                key={r}
                                onClick={() => setNearbyRadius(r)}
                                className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                                  nearbyRadius === r 
                                    ? 'bg-brand-primary text-white' 
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                              >
                                {r} km
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Category Filter - Icon Grid */}
                        <div className="mb-3">
                          <div className="flex items-center justify-between mb-1.5">
                            <label className="text-xs font-medium text-gray-600">Category</label>
                            {nearbyCategory && (
                              <button
                                onClick={() => setNearbyCategory('')}
                                className="text-xs text-brand-primary hover:underline"
                              >
                                Clear
                              </button>
                            )}
                          </div>
                          <div className="grid grid-cols-5 gap-1.5">
                            {NEARBY_CATEGORY_OPTIONS.map((cat) => {
                              const IconComponent = cat.Icon;
                              const isSelected = nearbyCategory === cat.id;
                              return (
                                <button
                                  key={cat.id}
                                  onClick={() => setNearbyCategory(isSelected ? '' : cat.id)}
                                  title={cat.label}
                                  className={`flex flex-col items-center justify-center p-1.5 rounded-lg transition-all ${
                                    isSelected
                                      ? 'bg-brand-primary text-white shadow-sm'
                                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                                  }`}
                                >
                                  <IconComponent className="w-4 h-4" />
                                  <span className="text-[9px] mt-0.5 leading-tight truncate w-full text-center">
                                    {cat.label}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-2">
                          <button
                            onClick={handleSearchNearby}
                            disabled={nearbySearching}
                            className="flex-1 py-2 px-4 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-dark transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                          >
                            {nearbySearching ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Search className="w-4 h-4" />
                            )}
                            Search
                          </button>
                          {nearbyPOIs.length > 0 && (
                            <button
                              onClick={handleClearNearby}
                              className="py-2 px-3 bg-gray-100 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
                            >
                              Clear
                            </button>
                          )}
                        </div>

                        {/* Results Count */}
                        {nearbyPOIs.length > 0 && (
                          <p className="text-xs text-gray-500 mt-2 text-center">
                            Found {nearbyPOIs.length} place{nearbyPOIs.length > 1 ? 's' : ''}. Hover markers to add to your plan.
                          </p>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* Floating Info Panel - Fixed at bottom */}
              <AnimatePresence>
                {tripSummary && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="absolute bottom-2 left-2 right-2 lg:bottom-4 lg:left-4 lg:right-4 z-10 max-h-48 lg:max-h-56"
                  >
                    <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-xl lg:rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                      {/* Toggle Header */}
                      <button 
                        onClick={() => setShowInfoPanel(!showInfoPanel)}
                        className="w-full px-4 py-3 flex items-center justify-between bg-brand-muted dark:bg-brand-primary/20 hover:bg-brand-muted/80 dark:hover:bg-brand-primary/30 transition-colors"
                      >
                        <span className="font-poppins font-semibold text-brand-primary dark:text-brand-muted flex items-center gap-2">
                          <Settings2 className="w-4 h-4" />
                          Trip Information
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
                                  Estimated Cost
                                </h4>
                                <p className="text-lg font-bold text-brand-primary dark:text-brand-muted">
                                  {formatVND(tripSummary.totalCost)}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                  ~{formatVND(Math.round(tripSummary.totalCost / tripSummary.numDays))}/day
                                </p>
                                {tripSummary.playfulBudgetTotal > 0 && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400">Fun estimate: {formatVND(tripSummary.playfulBudgetTotal)}</p>
                                )}
                              </div>

                              {/* Accommodation Info */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase flex items-center gap-1">
                                  <Bed className="w-3 h-3" />
                                  Accommodation
                                </h4>
                                {tripSummary.accommodations.length > 0 ? (
                                  <div className="space-y-1">
                                    {tripSummary.accommodations.slice(0, 2).map((acc, i) => (
                                      <p 
                                        key={i} 
                                        className="flex items-center gap-1 text-sm font-medium text-gray-800 dark:text-gray-200 truncate cursor-pointer hover:text-brand-primary dark:hover:text-brand-muted transition-colors" 
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
                                        <Bed className="w-3 h-3" /> {acc.name}
                                      </p>
                                    ))}
                                    {tripSummary.accommodations.length > 2 && (
                                      <p className="text-xs text-gray-400 dark:text-gray-500">
                                        +{tripSummary.accommodations.length - 2} more
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <p className="text-sm text-gray-400 dark:text-gray-500">No information</p>
                                )}
                              </div>

                              {/* Preferences */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase flex items-center gap-1">
                                  <Settings2 className="w-3 h-3" />
                                  Preferences
                                </h4>
                                <div className="space-y-1 text-sm">
                                  {tripSummary.preferences.budget && (
                                    <p className="text-gray-700 dark:text-gray-300 flex items-center gap-1">
                                      <Wallet className="w-4 h-4" /> {formatVND(tripSummary.preferences.budget)}
                                    </p>
                                  )}
                                  {tripSummary.preferences.budget_level && (
                                    <p className="text-gray-700 dark:text-gray-300 capitalize flex items-center gap-1">
                                      <BarChart3 className="w-4 h-4" /> {tripSummary.preferences.budget_level}
                                    </p>
                                  )}
                                  {tripSummary.preferences.pace && (
                                    <p className="text-gray-700 dark:text-gray-300 capitalize flex items-center gap-1">
                                      <Footprints className="w-4 h-4" /> {tripSummary.preferences.pace}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Quick Stats */}
                            <div className="px-4 pb-4 flex items-center justify-center gap-6 text-sm text-gray-500 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                {tripSummary.numDays} day{tripSummary.numDays !== 1 ? 's' : ''}
                              </span>
                              <span className="flex items-center gap-1">
                                <MapPin className="w-4 h-4" />
                                {tripSummary.numPOIs} location{tripSummary.numPOIs !== 1 ? 's' : ''}
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
