/**
 * PlanDetail - Travel Plan Detail View (Continuous Scroll)
 * 
 * Features:
 * - All days displayed as continuous scrollable cards
 * - Sequential POI numbering across all days (1 to last)
 * - Google Maps with @react-google-maps/api
 * - POI markers with InfoWindow
 * - HOVER activity → focus on map (not click)
 * - Polyline route between ALL POIs
 */

import { GoogleMap, InfoWindow, Marker, Polyline, useJsApiLoader } from '@react-google-maps/api';
import { motion } from 'framer-motion';
import {
    ArrowLeft,
    Calendar,
    Clock,
    Loader2,
    MapPin,
    Share2
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import planAPI from '../../services/planApi';

// Map container style
const mapContainerStyle = {
  width: '100%',
  height: '100%',
};

// Map options
const mapOptions = {
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: true,
  zoomControl: true,
};

export default function PlanDetail() {
  const { planId } = useParams();
  const navigate = useNavigate();

  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoveredPOI, setHoveredPOI] = useState(null); // Changed to hover-based
  const [error, setError] = useState('');
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
  // Fetch plan details
  useEffect(() => {
    const fetchPlan = async () => {
      try {
        setLoading(true);
        const result = await planAPI.getPlanById(planId);
        console.log('[PlanDetail] API Response:', result);
        
        if (result.success && result.data) {
          console.log('[PlanDetail] Plan data:', result.data);
          console.log('[PlanDetail] Itinerary:', result.data.itinerary);
          setPlan(result.data);
        } else {
          setError('Không tìm thấy kế hoạch');
        }
      } catch (err) {
        console.error('Error fetching plan:', err);
        setError('Lỗi khi tải kế hoạch');
      } finally {
        setLoading(false);
      }
    };

    if (planId) {
      fetchPlan();
    }
  }, [planId]);

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

  // Extract ALL POIs with coordinates from entire itinerary (continuous numbering)
  const allPOIs = useMemo(() => {
    if (!plan?.itinerary) return [];
    
    const pois = [];
    let globalIndex = 0;
    
    plan.itinerary.forEach((day, dayIndex) => {
      const activities = day.activities || [];
      
      activities.forEach((activity) => {
        globalIndex++;
        
        // Skip string activities
        if (typeof activity === 'string') return;
        // Skip activities without location
        if (!activity.location?.latitude || !activity.location?.longitude) return;
        
        pois.push({
          id: globalIndex,
          dayIndex: dayIndex + 1,
          name: activity.poi_name || 'Địa điểm',
          lat: activity.location.latitude,
          lng: activity.location.longitude,
          time: activity.time || null
        });
      });
    });
    
    return pois;
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

  // Polyline path - connects ALL POIs
  const polylinePath = useMemo(() => {
    return allPOIs.map(poi => ({ lat: poi.lat, lng: poi.lng }));
  }, [allPOIs]);

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
          
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <Share2 className="w-5 h-5 text-gray-600" />
          </button>
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
                  <div className="bg-gray-900 text-white px-6 py-4">
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

                  {/* Activities */}
                  <div className="p-6 space-y-4">
                    {day.activities?.length > 0 ? (
                      day.activities.map((activity, actIndex) => {
                        const globalIndex = startIndex + actIndex + 1;
                        const isString = typeof activity === 'string';
                        const activityText = isString ? activity : (activity.activity || activity.description || '');
                        const poiName = isString ? null : activity.poi_name;
                        const time = isString ? null : activity.time;
                        const duration = isString ? null : activity.duration;
                        const estimatedCost = isString ? null : activity.estimated_cost;
                        const location = isString ? null : activity.location;
                        const address = isString ? null : activity.address;
                        const rating = isString ? null : activity.rating;
                        const category = isString ? null : activity.category;
                        const hasLocation = location?.latitude && location?.longitude;

                        return (
                          <motion.div
                            key={actIndex}
                            className="flex gap-4"
                            onMouseEnter={() => hasLocation && handleActivityHover(globalIndex)}
                            onMouseLeave={handleActivityLeave}
                          >
                            {/* Timeline Number */}
                            <div className="flex flex-col items-center shrink-0">
                              <motion.div
                                whileHover={{ scale: 1.1 }}
                                className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                                  hoveredPOI === globalIndex
                                    ? 'bg-blue-600 text-white shadow-lg scale-110'
                                    : hasLocation
                                      ? 'bg-gray-900 text-white cursor-pointer hover:bg-gray-700'
                                      : 'bg-gray-300 text-gray-600'
                                }`}
                              >
                                {globalIndex}
                              </motion.div>
                              {actIndex < day.activities.length - 1 && (
                                <div className="w-px flex-1 bg-gray-200 mt-2 min-h-[20px]" />
                              )}
                            </div>

                            {/* Activity Card */}
                            <motion.div
                              whileHover={{ y: -2, boxShadow: '0 8px 25px -5px rgba(0,0,0,0.1)' }}
                              className={`flex-1 bg-white rounded-xl border p-4 transition-all ${
                                hoveredPOI === globalIndex
                                  ? 'border-blue-500 shadow-md ring-2 ring-blue-100'
                                  : 'border-gray-200 hover:shadow-md'
                              }`}
                            >
                              {/* Time */}
                              {time && (
                                <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                                  <Clock className="w-4 h-4" />
                                  {time}
                                </div>
                              )}

                              {/* POI Name with link */}
                              {poiName && (
                                <a
                                  href={getGoogleMapsLink(poiName, location)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="font-bold text-lg text-gray-900 hover:text-blue-600 transition-colors inline-flex items-center gap-1 mb-2"
                                >
                                  {poiName}
                                  <MapPin className="w-4 h-4" />
                                </a>
                              )}

                              {/* Activity Description */}
                              <p className={`text-gray-700 ${poiName ? 'text-sm' : 'text-base font-medium'} mb-2`}>
                                {activityText}
                              </p>

                              {/* Additional Info */}
                              <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                                {rating && (
                                  <span>⭐ {rating.toFixed(1)}</span>
                                )}
                                {category && (
                                  <span className="capitalize">📍 {category}</span>
                                )}
                                {duration && (
                                  <span>⏱️ {duration}</span>
                                )}
                                {estimatedCost && (
                                  <span>💰 {estimatedCost}</span>
                                )}
                              </div>
                              {address && (
                                <p className="text-xs text-gray-400 mt-2 truncate" title={address}>
                                  📍 {address}
                                </p>
                              )}
                            </motion.div>
                          </motion.div>
                        );
                      })
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

        {/* Right: Sticky Google Map */}
        <aside className="w-[60%] bg-white shrink-0 sticky top-[73px] h-[calc(100vh-73px)]">
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
            <GoogleMap
              mapContainerStyle={mapContainerStyle}
              center={mapCenter}
              zoom={13}
              options={mapOptions}
              onLoad={onMapLoad}
            >
              {/* Markers for ALL POIs */}
              {allPOIs.map((poi) => (
                <Marker
                  key={poi.id}
                  position={{ lat: poi.lat, lng: poi.lng }}
                  label={{
                    text: `${poi.id}`,
                    color: 'white',
                    fontWeight: 'bold',
                    fontSize: '12px'
                  }}
                  icon={{
                    path: window.google?.maps?.SymbolPath?.CIRCLE,
                    scale: 14,
                    fillColor: hoveredPOI === poi.id ? '#2563eb' : '#1f2937',
                    fillOpacity: 1,
                    strokeColor: 'white',
                    strokeWeight: 2,
                  }}
                  onMouseOver={() => setHoveredPOI(poi.id)}
                  onMouseOut={() => setHoveredPOI(null)}
                />
              ))}

              {/* InfoWindow for hovered POI */}
              {hoveredPOI && allPOIs.find(p => p.id === hoveredPOI) && (
                <InfoWindow
                  position={{
                    lat: allPOIs.find(p => p.id === hoveredPOI).lat,
                    lng: allPOIs.find(p => p.id === hoveredPOI).lng,
                  }}
                  onCloseClick={() => setHoveredPOI(null)}
                  options={{ disableAutoPan: true }}
                >
                  <div className="p-1 min-w-[120px]">
                    <p className="font-semibold text-gray-900">
                      {hoveredPOI}. {allPOIs.find(p => p.id === hoveredPOI).name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Ngày {allPOIs.find(p => p.id === hoveredPOI).dayIndex}
                    </p>
                    {allPOIs.find(p => p.id === hoveredPOI).time && (
                      <p className="text-xs text-gray-500">
                        {allPOIs.find(p => p.id === hoveredPOI).time}
                      </p>
                    )}
                  </div>
                </InfoWindow>
              )}

              {/* Polyline connecting ALL POIs */}
              {polylinePath.length > 1 && (
                <Polyline
                  path={polylinePath}
                  options={{
                    strokeColor: '#1f2937',
                    strokeOpacity: 0.6,
                    strokeWeight: 3,
                    geodesic: true,
                  }}
                />
              )}
            </GoogleMap>
          )}
        </aside>
      </div>
    </div>
  );
}
