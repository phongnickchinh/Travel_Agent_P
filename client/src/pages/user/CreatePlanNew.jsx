/**
 * CreatePlanNew - Elegant Travel Plan Creation
 * 
 * Minimalist design with Tailwind CSS, Framer Motion animations
 * Following the design system: white/black/gray palette
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
    AlertTriangle,
    ArrowLeft,
    Calendar,
    Loader2,
    MapPin,
    Sparkles,
    Utensils,
    Wallet
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import planAPI from '../../services/planApi';
import searchAPI from '../../services/searchApi';

// Interest options with Google Places API types
// Ref: https://developers.google.com/maps/documentation/places/web-service/place-types (Table A)
const INTEREST_OPTIONS = [
  { id: 'beach', label: 'Biển', icon: '🏖️', googleType: 'beach' },
  { id: 'museum', label: 'Văn hóa & Bảo tàng', icon: '🏛️', googleType: 'museum' },
  { id: 'restaurant', label: 'Ẩm thực', icon: '🍜', googleType: 'restaurant' },
  { id: 'night_club', label: 'Giải trí đêm', icon: '🌙', googleType: 'night_club' },
  { id: 'park', label: 'Thiên nhiên & Công viên', icon: '🌿', googleType: 'park' },
  { id: 'amusement_park', label: 'Phiêu lưu & Vui chơi', icon: '🧗', googleType: 'amusement_park' },
  { id: 'shopping_mall', label: 'Mua sắm', icon: '🛍️', googleType: 'shopping_mall' },
  { id: 'spa', label: 'Thư giãn & Spa', icon: '🧘', googleType: 'spa' },
  { id: 'historical_landmark', label: 'Lịch sử', icon: '📜', googleType: 'historical_landmark' },
  { id: 'tourist_attraction', label: 'Điểm tham quan', icon: '📸', googleType: 'tourist_attraction' },
  { id: 'zoo', label: 'Gia đình & Trẻ em', icon: '👨‍👩‍👧‍👦', googleType: 'zoo' },
  { id: 'cafe', label: 'Cafe & Lãng mạn', icon: '☕', googleType: 'cafe' },
];

// Budget levels
const BUDGET_MARKS = [
  { position: 0, value: 500000, label: 'Siêu tiết kiệm', sublabel: '500K' },
  { position: 15, value: 1000000, label: 'Tiết kiệm', sublabel: '1M' },
  { position: 30, value: 2000000, label: 'Bình dân', sublabel: '2M' },
  { position: 45, value: 3500000, label: 'Thoải mái', sublabel: '3.5M' },
  { position: 60, value: 5000000, label: 'Khá giả', sublabel: '5M' },
  { position: 75, value: 10000000, label: 'Cao cấp', sublabel: '10M' },
  { position: 90, value: 20000000, label: 'Sang trọng', sublabel: '20M' },
  { position: 100, value: 50000000, label: 'Không giới hạn', sublabel: '50M+' },
];

// Pace options
const PACE_OPTIONS = [
  { value: 'relaxed', label: 'Thư thả', description: '2-3 địa điểm/ngày', icon: '🧘' },
  { value: 'moderate', label: 'Vừa phải', description: '3-4 địa điểm/ngày', icon: '🚶' },
  { value: 'intensive', label: 'Khám phá nhiều', description: '5+ địa điểm/ngày', icon: '🏃' },
];

export default function CreatePlanNew() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    destination: '',
    destinationId: null,
    destinationName: '',
    destinationTypes: [],
    numDays: 3,
    startDate: '',
    preferences: {
      interests: [],
      budget: 3500000,
      budgetLevel: 'medium',
      pace: 'moderate',
      userNotes: '',
      customInterests: '',
      deepSearch: false
    }
  });

  // Autocomplete state
  const [destinationQuery, setDestinationQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);

  // UI state
  const [budgetPosition, setBudgetPosition] = useState(45);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Refs
  const destinationInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  const today = new Date().toISOString().split('T')[0];

  // Budget helpers
  const getBudgetFromPosition = useCallback((position) => {
    for (let i = 0; i < BUDGET_MARKS.length - 1; i++) {
      const current = BUDGET_MARKS[i];
      const next = BUDGET_MARKS[i + 1];
      if (position >= current.position && position <= next.position) {
        const ratio = (position - current.position) / (next.position - current.position);
        const value = current.value + ratio * (next.value - current.value);
        return Math.round(value / 100000) * 100000;
      }
    }
    return BUDGET_MARKS[BUDGET_MARKS.length - 1].value;
  }, []);

  const getBudgetLabel = useCallback((value) => {
    let closest = BUDGET_MARKS[0];
    let minDiff = Math.abs(value - closest.value);
    for (const mark of BUDGET_MARKS) {
      const diff = Math.abs(value - mark.value);
      if (diff < minDiff) {
        minDiff = diff;
        closest = mark;
      }
    }
    return closest.label;
  }, []);

  const formatCurrency = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1)}M VNĐ`;
    }
    return `${(value / 1000).toFixed(0)}K VNĐ`;
  };

  // Destination search
  const handleDestinationChange = useCallback(async (value) => {
    setDestinationQuery(value);
    setFormData(prev => ({ ...prev, destination: value, destinationId: null }));
    setSelectedSuggestionIndex(-1);

    if (value.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setIsSearching(true);
    setShowSuggestions(true);

    try {
      const results = await searchAPI.debouncedAutocomplete(value, { limit: 6 });
      setSuggestions(results.suggestions || []);
    } catch (err) {
      console.error('Search error:', err);
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handleSelectSuggestion = useCallback((suggestion) => {
    const displayName = suggestion.main_text || suggestion.description || suggestion.name;
    setDestinationQuery(displayName);
    setFormData(prev => ({
      ...prev,
      destination: displayName,
      destinationId: suggestion.place_id || suggestion.poi_id || suggestion._id || null,
      destinationName: displayName,
      destinationTypes: suggestion.types || []
    }));
    setSuggestions([]);
    setShowSuggestions(false);
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => prev < suggestions.length - 1 ? prev + 1 : 0);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => prev > 0 ? prev - 1 : suggestions.length - 1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSuggestionIndex >= 0) {
          handleSelectSuggestion(suggestions[selectedSuggestionIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
      default:
        break;
    }
  }, [showSuggestions, suggestions, selectedSuggestionIndex, handleSelectSuggestion]);

  // Handlers
  const handleInterestToggle = useCallback((interestId) => {
    setFormData(prev => {
      const interests = prev.preferences.interests;
      const newInterests = interests.includes(interestId)
        ? interests.filter(id => id !== interestId)
        : [...interests, interestId];
      return {
        ...prev,
        preferences: { ...prev.preferences, interests: newInterests }
      };
    });
  }, []);

  const handleBudgetChange = useCallback((position) => {
    const value = getBudgetFromPosition(position);
    setBudgetPosition(position);
    setFormData(prev => ({
      ...prev,
      preferences: {
        ...prev.preferences,
        budget: value,
        budgetLevel: position <= 30 ? 'low' : position <= 60 ? 'medium' : position <= 85 ? 'high' : 'luxury'
      }
    }));
  }, [getBudgetFromPosition]);

  const handlePaceChange = useCallback((pace) => {
    setFormData(prev => ({
      ...prev,
      preferences: { ...prev.preferences, pace }
    }));
  }, []);

  // Submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.destination.trim()) {
      setError('Vui lòng chọn điểm đến');
      return;
    }
    if (!formData.destinationId) {
      setError('Vui lòng chọn điểm đến từ danh sách gợi ý');
      return;
    }
    if (!formData.startDate) {
      setError('Vui lòng chọn ngày bắt đầu');
      return;
    }
    if (formData.preferences.interests.length === 0) {
      setError('Vui lòng chọn ít nhất một sở thích');
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        title: formData.title || `Chuyến đi ${formData.destination}`,
        destination_place_id: formData.destinationId,
        destination_name: formData.destinationName || formData.destination,
        destination_types: formData.destinationTypes,
        destination: formData.destination,
        num_days: formData.numDays,
        start_date: formData.startDate,
        preferences: {
          interests: formData.preferences.interests,
          budget: formData.preferences.budget,
          budget_level: formData.preferences.budgetLevel,
          pace: formData.preferences.pace,
          user_notes: formData.preferences.userNotes || null,
          deep_search: formData.preferences.deepSearch
        }
      };

      if (formData.preferences.customInterests.trim()) {
        const custom = formData.preferences.customInterests.split(',').map(s => s.trim()).filter(Boolean);
        payload.preferences.interests = [...payload.preferences.interests, ...custom];
      }

      const result = await planAPI.createPlan(payload);

      if (result.success) {
        setSuccess('Đã tạo kế hoạch thành công!');
        setTimeout(() => {
          navigate(`/dashboard`);
        }, 1500);
      } else {
        setError(result.errorVi || result.error || 'Không thể tạo kế hoạch');
      }
    } catch (err) {
      console.error('Submit error:', err);
      setError(err.message || 'Đã xảy ra lỗi');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target) &&
        !destinationInputRef.current?.contains(e.target)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <motion.button
            whileHover={{ x: -4 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-medium">Quay lại</span>
          </motion.button>
          <h1 className="font-poppins font-bold text-xl text-gray-900">
            Tạo kế hoạch
          </h1>
          <div className="w-20" /> {/* Spacer */}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Hero Section */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-sm">
              <Sparkles className="w-4 h-4 text-yellow-500" />
              AI-Powered Planning
            </div>
            <h2 className="font-poppins font-bold text-3xl text-gray-900 mb-2">
              Để AI lên lịch trình hoàn hảo
            </h2>
            <p className="text-gray-500">
              Điền thông tin bên dưới để bắt đầu
            </p>
          </div>

          {/* Form Card */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Messages */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm"
                  >
                    {error}
                  </motion.div>
                )}
                {success && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm"
                  >
                    {success}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Trip Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Tên chuyến đi
                  <span className="text-gray-400 font-normal ml-1">(Tùy chọn)</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="VD: Nghỉ dưỡng Đà Nẵng cùng gia đình"
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                  maxLength={200}
                />
              </div>

              {/* Destination */}
              <div className="relative">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  <MapPin className="w-4 h-4 inline mr-1" />
                  Điểm đến
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <div className="relative">
                  <input
                    ref={destinationInputRef}
                    type="text"
                    value={destinationQuery}
                    onChange={(e) => handleDestinationChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => destinationQuery.length >= 2 && setShowSuggestions(true)}
                    placeholder="Nhập tên thành phố, địa điểm..."
                    autoComplete="off"
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all pr-10"
                  />
                  {isSearching && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 animate-spin" />
                  )}
                </div>

                {/* Suggestions Dropdown */}
                <AnimatePresence>
                  {showSuggestions && suggestions.length > 0 && (
                    <motion.ul
                      ref={suggestionsRef}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl overflow-hidden"
                    >
                      {suggestions.map((suggestion, index) => {
                        const types = suggestion.types || [];
                        const icon = types.includes('locality') ? '🏙️' :
                          types.includes('natural_feature') ? '🏖️' :
                          types.includes('restaurant') ? '🍽️' :
                          types.includes('lodging') ? '🏨' : '📍';

                        return (
                          <motion.li
                            key={suggestion.place_id || index}
                            whileHover={{ backgroundColor: '#f9fafb' }}
                            onClick={() => handleSelectSuggestion(suggestion)}
                            onMouseEnter={() => setSelectedSuggestionIndex(index)}
                            className={`px-4 py-3 cursor-pointer flex items-start gap-3 border-b border-gray-100 last:border-b-0 ${
                              index === selectedSuggestionIndex ? 'bg-gray-50' : ''
                            }`}
                          >
                            <span className="text-xl">{icon}</span>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate">
                                {suggestion.main_text || suggestion.description}
                              </p>
                              {suggestion.secondary_text && (
                                <p className="text-sm text-gray-500 truncate">
                                  {suggestion.secondary_text}
                                </p>
                              )}
                            </div>
                          </motion.li>
                        );
                      })}
                    </motion.ul>
                  )}
                </AnimatePresence>
              </div>

              {/* Duration & Date Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Number of Days */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    <Calendar className="w-4 h-4 inline mr-1" />
                    Số ngày
                  </label>
                  <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-2xl font-bold text-gray-900">{formData.numDays}</span>
                      <span className="text-gray-500">ngày</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="30"
                      value={formData.numDays}
                      onChange={(e) => setFormData(prev => ({ ...prev, numDays: parseInt(e.target.value) }))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-gray-900"
                    />
                    <div className="flex justify-between text-xs text-gray-400 mt-2">
                      <span>1</span>
                      <span>15</span>
                      <span>30</span>
                    </div>
                  </div>
                </div>

                {/* Start Date */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    <Calendar className="w-4 h-4 inline mr-1" />
                    Ngày bắt đầu
                    <span className="text-red-500 ml-1">*</span>
                  </label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
                    min={today}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {/* Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-white px-4 text-sm font-medium text-gray-500">
                    Sở thích & Ngân sách
                  </span>
                </div>
              </div>

              {/* Interests */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  Sở thích của bạn
                  <span className="text-red-500 ml-1">*</span>
                  <span className="text-gray-400 font-normal ml-2">(Chọn nhiều)</span>
                </label>
                <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
                  {INTEREST_OPTIONS.map((interest) => {
                    const isSelected = formData.preferences.interests.includes(interest.id);
                    return (
                      <motion.button
                        key={interest.id}
                        type="button"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => handleInterestToggle(interest.id)}
                        className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all ${
                          isSelected
                            ? 'border-gray-900 bg-gray-100 text-gray-900 shadow-md'
                            : 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                        }`}
                      >
                        <span className="text-xl">{interest.icon}</span>
                        <span className="text-xs font-medium">{interest.label}</span>
                      </motion.button>
                    );
                  })}
                </div>

                {/* Custom Interests */}
                <input
                  type="text"
                  value={formData.preferences.customInterests}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    preferences: { ...prev.preferences, customInterests: e.target.value }
                  }))}
                  placeholder="Thêm sở thích khác (cách nhau bằng dấu phẩy)"
                  className="w-full mt-3 px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                />
              </div>

              {/* Budget */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  <Wallet className="w-4 h-4 inline mr-1" />
                  Ngân sách / ngày
                </label>
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-2xl font-bold text-gray-900">
                      {formatCurrency(formData.preferences.budget)}
                    </span>
                    <span className="px-3 py-1 bg-gray-100 border border-gray-300 text-gray-700 text-sm font-medium rounded-full">
                      {getBudgetLabel(formData.preferences.budget)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={budgetPosition}
                    onChange={(e) => handleBudgetChange(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-gray-900"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-2">
                    <span>500K</span>
                    <span>5M</span>
                    <span>50M+</span>
                  </div>
                </div>
              </div>

              {/* Pace */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  Nhịp độ du lịch
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {PACE_OPTIONS.map((option) => {
                    const isSelected = formData.preferences.pace === option.value;
                    return (
                      <motion.button
                        key={option.value}
                        type="button"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => handlePaceChange(option.value)}
                        className={`flex flex-col items-center gap-1 p-4 rounded-xl border-2 transition-all ${
                          isSelected
                            ? 'border-gray-900 bg-gray-100 text-gray-900 shadow-md'
                            : 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                        }`}
                      >
                        <span className="text-2xl mb-1">{option.icon}</span>
                        <span className="font-medium">{option.label}</span>
                        <span className={`text-xs ${isSelected ? 'text-gray-600' : 'text-gray-500'}`}>
                          {option.description}
                        </span>
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Deep Search Toggle */}
              <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-200 rounded-2xl p-6">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 mt-1">
                    <input
                      type="checkbox"
                      id="deepSearch"
                      checked={formData.preferences.deepSearch}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        preferences: { ...prev.preferences, deepSearch: e.target.checked }
                      }))}
                      className="w-5 h-5 rounded border-2 border-amber-400 text-amber-600 focus:ring-2 focus:ring-amber-500 focus:ring-offset-0 cursor-pointer"
                    />
                  </div>
                  <div className="flex-1">
                    <label htmlFor="deepSearch" className="flex items-center gap-2 text-base font-bold text-gray-900 cursor-pointer mb-1">
                      <span>🔍 Tìm kiếm sâu (Deep Search)</span>
                    </label>
                    <p className="text-sm text-gray-600 mb-2">
                      Sử dụng dữ liệu mới nhất từ Google Places API thay vì dữ liệu có sẵn trong hệ thống
                    </p>
                    <AnimatePresence>
                      {formData.preferences.deepSearch && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="flex items-start gap-2 p-3 bg-amber-100 border border-amber-300 rounded-xl mt-2"
                        >
                          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                          <div className="text-sm text-amber-800">
                            <p className="font-semibold mb-1">⚠️ Lưu ý quan trọng:</p>
                            <ul className="list-disc list-inside space-y-0.5 text-xs">
                              <li>Thời gian xử lý có thể <strong>lâu hơn 30-60 giây</strong></li>
                              <li>Chi phí API <strong>cao hơn</strong> do gọi Google Places trực tiếp</li>
                              <li>Dữ liệu mới nhất nhưng có thể tốn kém hơn</li>
                            </ul>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>

              {/* Dietary */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  <Utensils className="w-4 h-4 inline mr-1" />
                  Yêu cầu ăn uống
                  <span className="text-gray-400 font-normal ml-1">(Tùy chọn)</span>
                </label>
                <input
                  type="text"
                  value={formData.preferences.dietary}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    preferences: { ...prev.preferences, userNotes: e.target.value }
                  }))}
                  placeholder="VD: Chay, không gluten, halal..."
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all"
                />
              </div>

              {/* Submit Button */}
              <motion.button
                type="submit"
                disabled={isSubmitting}
                whileHover={{ scale: 1.01, y: -2 }}
                whileTap={{ scale: 0.99 }}
                className="w-full flex items-center justify-center gap-3 px-8 py-4 bg-white border-2 border-gray-900 text-gray-900 font-semibold rounded-xl hover:bg-gray-900 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-lg"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Đang tạo...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>Tạo Kế Hoạch</span>
                  </>
                )}
              </motion.button>
            </form>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
