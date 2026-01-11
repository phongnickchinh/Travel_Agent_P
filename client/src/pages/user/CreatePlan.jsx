/**
 * CreatePlan Page - Travel Plan Creation Form
 * 
 * Features:
 * - Destination autocomplete via Elasticsearch
 * - Num days slider (1-30)
 * - Start date calendar picker
 * - Origin placeholder (future: Google Maps embed)
 * - Preferences: Multi-choice interests + Budget slider
 * - Supports both modal mode (isModal=true) and route mode
 * 
 * Author: Travel Agent P Team
 */

import { motion } from 'framer-motion';
import {
  Calendar,
  Camera,
  ChevronLeft,
  Coffee,
  Heart,
  Landmark,
  Loader2,
  MapPin,
  Moon,
  Mountain,
  Palmtree,
  PiggyBank,
  Scroll,
  Search,
  ShoppingBag,
  Sparkles,
  Timer,
  TreePine,
  Users,
  Utensils,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import planAPI from '../../services/planApi';
import searchAPI from '../../services/searchApi';

// Available interest options with lucide-react icons
const INTEREST_OPTIONS = [
  { id: 'beach', label: 'Biển', Icon: Palmtree },
  { id: 'culture', label: 'Văn hóa', Icon: Landmark },
  { id: 'food', label: 'Ẩm thực', Icon: Utensils },
  { id: 'cafe', label: 'Cafe', Icon: Coffee },
  { id: 'nightlife', label: 'Giải trí đêm', Icon: Moon },
  { id: 'nature', label: 'Thiên nhiên', Icon: TreePine },
  { id: 'adventure', label: 'Phiêu lưu', Icon: Mountain },
  { id: 'shopping', label: 'Mua sắm', Icon: ShoppingBag },
  { id: 'relaxation', label: 'Thư giãn', Icon: Sparkles },
  { id: 'history', label: 'Lịch sử', Icon: Scroll },
  { id: 'photography', label: 'Chụp ảnh', Icon: Camera },
  { id: 'family', label: 'Gia đình', Icon: Users },
  { id: 'romantic', label: 'Lãng mạn', Icon: Heart },
];

// Budget levels with non-linear values (VND)
// Slider position 0-100 maps to these budget values
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
  { value: 'relaxed', label: 'Thư thả', description: '2-3 địa điểm/ngày' },
  { value: 'moderate', label: 'Vừa phải', description: '3-4 địa điểm/ngày' },
  { value: 'intensive', label: 'Khám phá nhiều', description: '5+ địa điểm/ngày' },
];

const LOCAL_STORAGE_KEY = 'ta:create-plan:last-entry';

const createEmptyForm = () => ({
  title: '',
  destination: '',
  destinationId: null,
  numDays: 3,
  startDate: '',
  origin: null,
  preferences: {
    interests: [],
    budget: 3500000,
    budgetLevel: 'medium',
    pace: 'moderate',
    userNotes: '',
    customInterests: '',
  },
});

/**
 * CreatePlan Component
 * 
 * @param {boolean} isModal - When true, renders as modal overlay without route navigation
 * @param {Function} onClose - Callback to close modal (required if isModal=true)
 * @param {Function} onSuccess - Callback after successful creation (optional, for modal mode)
 */
export default function CreatePlan({ isModal = false, onClose, onSuccess }) {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Form state
  const [formData, setFormData] = useState(() => createEmptyForm());

  // Autocomplete state
  const [destinationQuery, setDestinationQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  
  // UI state
  const [budgetPosition, setBudgetPosition] = useState(45); // Default position
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [interestSearch, setInterestSearch] = useState('');
  const [showInterestSuggestions, setShowInterestSuggestions] = useState(false);

  // Refs
  const destinationInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Calculate min date (today)
  const today = new Date().toISOString().split('T')[0];

  const filteredInterestOptions = useMemo(() => {
    const query = interestSearch.toLowerCase().trim();
    return INTEREST_OPTIONS.filter((option) => {
      const notSelected = !formData.preferences.interests.includes(option.id);
      if (!query) return notSelected;
      return notSelected && option.label.toLowerCase().includes(query);
    });
  }, [interestSearch, formData.preferences.interests]);

  // Convert slider position to budget value (non-linear)
  const getBudgetFromPosition = useCallback((position) => {
    // Find the two marks that bracket the position
    for (let i = 0; i < BUDGET_MARKS.length - 1; i++) {
      const current = BUDGET_MARKS[i];
      const next = BUDGET_MARKS[i + 1];
      
      if (position >= current.position && position <= next.position) {
        // Linear interpolation between marks
        const ratio = (position - current.position) / (next.position - current.position);
        const value = current.value + ratio * (next.value - current.value);
        return Math.round(value / 100000) * 100000; // Round to 100K
      }
    }
    return BUDGET_MARKS[BUDGET_MARKS.length - 1].value;
  }, []);

  // Get budget label from value
  const getBudgetLabel = useCallback((value) => {
    // Find closest mark
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

  // Format currency
  const formatCurrency = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1)}M VNĐ`;
    }
    return `${(value / 1000).toFixed(0)}K VNĐ`;
  };

  const estimatedTotalCost = useMemo(() => {
    const perDay = Math.max(0, Number(formData.preferences?.budget) || 0);
    const days = Math.max(0, Number(formData.numDays) || 0);
    return perDay * days;
  }, [formData.preferences?.budget, formData.numDays]);

  const getPositionFromBudget = useCallback((budgetValue) => {
    if (budgetValue === undefined || budgetValue === null) return BUDGET_MARKS[3].position;
    for (let i = 0; i < BUDGET_MARKS.length - 1; i++) {
      const current = BUDGET_MARKS[i];
      const next = BUDGET_MARKS[i + 1];
      if (budgetValue >= current.value && budgetValue <= next.value) {
        const ratio = (budgetValue - current.value) / (next.value - current.value);
        return Math.round(current.position + ratio * (next.position - current.position));
      }
    }
    return BUDGET_MARKS[BUDGET_MARKS.length - 1].position;
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved);
      if (parsed?.formData) {
        setFormData((prev) => ({
          ...prev,
          ...parsed.formData,
          preferences: {
            ...prev.preferences,
            ...parsed.formData.preferences,
          },
        }));

        if (parsed.formData?.preferences?.budget) {
          setBudgetPosition(parsed.budgetPosition ?? getPositionFromBudget(parsed.formData.preferences.budget));
        }

        if (typeof parsed.destinationQuery === 'string') {
          setDestinationQuery(parsed.destinationQuery);
        }
      }
    } catch (err) {
      console.warn('Unable to load saved plan draft', err);
    }
  }, [getPositionFromBudget]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const payload = {
      formData,
      budgetPosition,
      destinationQuery,
    };
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(payload));
  }, [formData, budgetPosition, destinationQuery]);

  // Handle destination search with debounce
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
      const response = await searchAPI.debouncedAutocomplete(value, { limit: 8 });
      
      // API returns { suggestions: [], total, sources }
      const results = response?.suggestions || response || [];
      
      setSuggestions(results);
    } catch (err) {
      console.error('Search error:', err);
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Handle suggestion selection
  const handleSelectSuggestion = useCallback((suggestion) => {
    // Normalize field names from different API sources
    const displayName = suggestion.main_text || suggestion.name_vi || suggestion.name_en || suggestion.name || suggestion.query;
    const suggestionId = suggestion.place_id || suggestion.poi_id || suggestion._id || null;
    const suggestionTypesList = suggestion.types || suggestion.type || [];
    
    setDestinationQuery(displayName);
    setFormData(prev => ({
      ...prev,
      destination: displayName,
      destinationId: suggestionId,
      destinationTypes: suggestionTypesList
    }));
    setSuggestions([]);
    setShowSuggestions(false);
  }, []);

  // Handle keyboard navigation in suggestions
  const handleKeyDown = useCallback((e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSuggestionIndex >= 0) {
          handleSelectSuggestion(suggestions[selectedSuggestionIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedSuggestionIndex(-1);
        break;
      default:
        break;
    }
  }, [showSuggestions, suggestions, selectedSuggestionIndex, handleSelectSuggestion]);

  // Handle interest toggle
  const handleInterestToggle = useCallback((interestId) => {
    setFormData(prev => {
      const currentInterests = prev.preferences.interests;
      const newInterests = currentInterests.includes(interestId)
        ? currentInterests.filter(id => id !== interestId)
        : [...currentInterests, interestId];
      
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          interests: newInterests
        }
      };
    });
  }, []);

  // Handle budget slider change
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

  // Handle num days change
  const handleNumDaysChange = useCallback((value) => {
    setFormData(prev => ({
      ...prev,
      numDays: parseInt(value, 10)
    }));
  }, []);

  // Handle pace change
  const handlePaceChange = useCallback((pace) => {
    setFormData(prev => ({
      ...prev,
      preferences: {
        ...prev.preferences,
        pace
      }
    }));
  }, []);

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validation
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
      // Prepare API payload
      const payload = {
        title: formData.title || `Chuyến đi ${formData.destination}`,
        destination_place_id: formData.destinationId,
        destination_name: formData.destination,
        destination_types: formData.destinationTypes || [],
        num_days: formData.numDays,
        start_date: formData.startDate,
        origin: formData.origin, // null for now
        preferences: {
          interests: formData.preferences.interests,
          budget: formData.preferences.budget,
          budget_level: formData.preferences.budgetLevel,
          pace: formData.preferences.pace,
          user_notes: formData.preferences.userNotes || null,
        }
      };

      // Add custom interests if provided
      if (formData.preferences.customInterests.trim()) {
        const customInterests = formData.preferences.customInterests
          .split(',')
          .map(s => s.trim())
          .filter(s => s.length > 0);
        payload.preferences.interests = [...payload.preferences.interests, ...customInterests];
      }

      const result = await planAPI.createPlan(payload);

      if (result.success) {
        setSuccess('Đã tạo kế hoạch! Đang xử lý trong nền...');
        
        // Clear saved draft
        if (typeof window !== 'undefined') {
          localStorage.removeItem(LOCAL_STORAGE_KEY);
        }
        
        // Handle modal vs route mode
        if (isModal) {
          // In modal mode: call success callback and close
          setTimeout(() => {
            onSuccess?.(result.data);
            onClose?.();
          }, 1000);
        } else {
          // In route mode: navigate to plan detail
          setTimeout(() => {
            navigate(`/dashboard/${user?.username}?plan=${result.data.plan_id}`);
          }, 1500);
        }
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

  // Close suggestions when clicking outside
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

  // Handle close action (modal or route)
  const handleClose = useCallback(() => {
    if (isModal) {
      onClose?.();
    } else {
      navigate(-1);
    }
  }, [isModal, onClose, navigate]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4 md:p-6 dark:bg-black/60" onClick={handleClose}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-5xl rounded-2xl bg-white shadow-2xl border border-brand-primary dark:bg-gray-900 dark:border-brand-primary"
      >
        <div className="flex items-start justify-between gap-3 border-b border-brand-primary/20 px-5 py-4 dark:border-brand-primary/30">
          <div className="space-y-1">
            {/* <div className="inline-flex items-center gap-2 rounded-full bg-brand-muted px-3 py-1 text-xs font-medium text-brand-primary">
              <Sparkles className="h-4 w-4" />
              <span>Nhập nhanh trên dashboard</span>
            </div> */}
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-inter font-bold text-brand-secondary dark:text-white">Tạo kế hoạch</h1>
              {/* <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-700 shadow-sm">
                <CheckCircle2 className="h-4 w-4 text-brand-primary" />
                <span>Tự lưu bản nháp</span>
              </div> */}
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300">Bạn yêu cầu, chúng tôi thực hiện</p>
          </div>
          <div className="flex items-center gap-2">
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleClose}
              className="hidden md:inline-flex items-center gap-2 rounded-full border border-brand-primary/30 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm hover:border-brand-primary hover:text-brand-primary dark:border-brand-primary/50 dark:bg-gray-800 dark:text-gray-100 dark:hover:border-white"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Quay lại</span>
            </motion.button>
            <motion.button
              whileHover={{ rotate: 90 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleClose}
              aria-label="Đóng"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-brand-primary/30 bg-white text-gray-700 shadow-sm hover:border-brand-primary hover:text-brand-primary dark:border-brand-primary/50 dark:bg-gray-800 dark:text-gray-100 dark:hover:border-white"
            >
              <X className="h-4 w-4" />
            </motion.button>
          </div>
        </div>

        <div className="grid gap-4 p-5 md:p-6 lg:p-7 lg:grid-cols-[1fr_260px]">
          <div className="max-h-[70vh] overflow-y-auto pr-1 space-y-4">
            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950/60 dark:text-red-200">
                {error}
              </div>
            )}
            {success && (
              <div className="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-700 dark:bg-emerald-950/50 dark:text-emerald-200">
                {success}
              </div>
            )}

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-100">
                    <MapPin className="h-4 w-4 text-brand-secondary" />
                    Điểm đến <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      ref={destinationInputRef}
                      type="text"
                      className="w-full rounded-xl border border-brand-primary/30 bg-white/80 px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-white"
                      placeholder="Nhập thành phố hoặc địa điểm"
                      value={destinationQuery}
                      onChange={(e) => handleDestinationChange(e.target.value)}
                      onKeyDown={handleKeyDown}
                      onFocus={() => destinationQuery.length >= 2 && setShowSuggestions(true)}
                      autoComplete="off"
                    />
                    {isSearching && (
                      <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
                    )}

                    {showSuggestions && suggestions.length > 0 && (
                      <ul
                        ref={suggestionsRef}
                        className="absolute z-50 mt-2 w-full overflow-hidden rounded-xl border border-brand-primary/30 bg-white shadow-xl divide-y divide-brand-primary/10 dark:border-brand-primary/50 dark:bg-gray-900 dark:divide-brand-primary/20"
                      >
                        {suggestions.map((suggestion, index) => {
                          // Normalize field names from different sources
                          const displayName = suggestion.main_text || suggestion.name_vi || suggestion.name_en || suggestion.name || suggestion.query;
                          const displayAddress = suggestion.secondary_text || suggestion.description || suggestion.address || '';
                          const suggestionId = suggestion.place_id || suggestion.poi_id || suggestion._id || index;
                          
                          return (
                            <li
                              key={suggestionId}
                              className={`flex cursor-pointer items-start gap-3 px-3.5 py-3 text-sm transition hover:bg-gray-50 dark:hover:bg-gray-800 ${index === selectedSuggestionIndex ? 'bg-gray-50 dark:bg-gray-800' : ''}`}
                              onClick={() => handleSelectSuggestion(suggestion)}
                              onMouseEnter={() => setSelectedSuggestionIndex(index)}
                            >
                              <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                                <MapPin className="h-4 w-4" />
                              </div>
                              <div className="flex-1">
                                <p className="font-semibold text-gray-900 line-clamp-1 dark:text-gray-100">{displayName}</p>
                                {displayAddress && (
                                  <p className="text-xs text-gray-600 line-clamp-2 dark:text-gray-400">{displayAddress}</p>
                                )}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-100">
                    <Calendar className="h-4 w-4 text-brand-secondary" />
                    Ngày bắt đầu <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    className="w-full rounded-xl border border-brand-primary/30 bg-white/80 px-3.5 py-2.5 text-sm text-gray-900 shadow-sm transition focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-white"
                    value={formData.startDate}
                    onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
                    min={today}
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-brand-primary/20 bg-gray-50/80 p-4 shadow-sm space-y-3 dark:border-brand-primary/30 dark:bg-gray-800/60">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-gray-800 font-semibold dark:text-gray-100">
                      <Timer className="h-4 w-4 text-brand-secondary" />
                      <span>Số ngày</span>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={formData.numDays}
                      onChange={(e) => handleNumDaysChange(e.target.value)}
                      className="w-20 rounded-lg border border-brand-primary/30 px-2.5 py-1.5 text-sm text-gray-800 focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-white"
                    />
                  </div>
                  <input
                    type="range"
                    className="w-full accent-brand-primary"
                    min="1"
                    max="30"
                    value={formData.numDays}
                    onChange={(e) => handleNumDaysChange(e.target.value)}
                  />
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>1</span>
                    <span>15</span>
                    <span>30</span>
                  </div>
                </div>

                <div className="rounded-2xl border border-dashed border-brand-primary/30 bg-white/60 p-4 shadow-sm dark:border-brand-primary/40 dark:bg-gray-800/60">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Điểm xuất phát (tùy chọn)</p>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Sắp ra mắt: chọn vị trí xuất phát để AI tối ưu quãng đường.</p>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-800 dark:text-gray-100">Tên chuyến đi <span className="text-gray-400">(tuỳ chọn)</span></label>
                <input
                  type="text"
                  className="w-full rounded-xl border border-brand-primary/30 bg-white/80 px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-white"
                  placeholder="VD: Nghỉ dưỡng Đà Nẵng cùng gia đình"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  maxLength={200}
                />
              </div>

              <div className="rounded-2xl border border-brand-primary/20 bg-white p-4 shadow-sm space-y-3 dark:border-brand-primary/30 dark:bg-gray-800/80">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-gray-900 font-semibold dark:text-gray-100">
                    <PiggyBank className="h-4 w-4 text-brand-secondary" />
                    <span>Ngân sách / ngày</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    step="50000"
                    value={formData.preferences.budget}
                    onChange={(e) => {
                      const typed = Math.max(0, Number(e.target.value) || 0);
                      setFormData(prev => ({
                        ...prev,
                        preferences: { ...prev.preferences, budget: typed },
                      }));
                      setBudgetPosition(getPositionFromBudget(typed));
                    }}
                    className="w-32 rounded-lg border border-brand-primary/30 px-2.5 py-1.5 text-sm text-gray-800 focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-white"
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
                  <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(formData.preferences.budget)}</span>
                  <span className="dark:text-gray-300">{getBudgetLabel(formData.preferences.budget)}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-300">Ước tính tổng: {formatCurrency(estimatedTotalCost)}</p>
                <input
                  type="range"
                  className="w-full accent-brand-primary"
                  min="0"
                  max="100"
                  value={budgetPosition}
                  onChange={(e) => handleBudgetChange(parseInt(e.target.value, 10))}
                />
                <div className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400">
                  {BUDGET_MARKS.filter((_, idx) => idx % 2 === 0).map((mark) => (
                    <span key={mark.position}>{mark.sublabel}</span>
                  ))}
                </div>
              </div>

              <div className="space-y-3 rounded-2xl border border-brand-primary/20 bg-gray-50/70 p-4 shadow-sm dark:border-brand-primary/30 dark:bg-gray-800/60">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 text-gray-900 font-semibold dark:text-gray-100">
                    <Sparkles className="h-4 w-4 text-brand-secondary" />
                    <span>Sở thích</span>
                    <span className="text-red-500">*</span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-300">{formData.preferences.interests.length} lựa chọn</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {INTEREST_OPTIONS.map((interest) => {
                    const isSelected = formData.preferences.interests.includes(interest.id);
                    const IconComponent = interest.Icon;
                    return (
                      <motion.button
                        key={interest.id}
                        type="button"
                        whileHover={{ y: -2 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => handleInterestToggle(interest.id)}
                        className={`flex items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition ${
                          isSelected
                            ? 'border-brand-primary bg-brand-primary text-white shadow-sm'
                            : 'border-brand-primary/30 bg-white text-gray-800 hover:border-brand-primary hover:text-brand-primary dark:border-brand-primary/50 dark:bg-gray-900 dark:text-white dark:hover:border-brand-primary dark:hover:text-white'
                        }`}
                      >
                        <IconComponent className="h-4 w-4" />
                        <span>{interest.label}</span>
                      </motion.button>
                    );
                  })}
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-700 dark:text-gray-200">Thêm từ gợi ý (autocomplete)</label>
                  <div className="relative">
                    <div className="flex items-center gap-2 rounded-xl border border-brand-primary/30 bg-white px-3.5 py-2 shadow-sm focus-within:border-brand-primary dark:border-brand-primary/50 dark:bg-gray-900 dark:focus-within:border-white">
                      <Search className="h-4 w-4 text-gray-500 dark:text-gray-300" />
                      <input
                        type="text"
                        value={interestSearch}
                        onChange={(e) => {
                          setInterestSearch(e.target.value);
                          setShowInterestSuggestions(true);
                        }}
                        onFocus={() => setShowInterestSuggestions(true)}
                        onBlur={() => setTimeout(() => setShowInterestSuggestions(false), 120)}
                        className="w-full bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder:text-gray-500"
                        placeholder="Nhập để tìm nhanh (biển, ẩm thực...)"
                      />
                    </div>
                    {showInterestSuggestions && filteredInterestOptions.length > 0 && (
                      <div className="absolute z-10 mt-2 w-full rounded-xl border border-brand-primary/30 bg-white shadow-lg dark:border-brand-primary/50 dark:bg-gray-900">
                        {filteredInterestOptions.map((item) => {
                          const ItemIcon = item.Icon;
                          return (
                            <button
                              type="button"
                              key={item.id}
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => {
                                handleInterestToggle(item.id);
                                setInterestSearch('');
                              }}
                              className="flex w-full items-center gap-2 px-3.5 py-2 text-sm text-left hover:bg-gray-50 dark:text-gray-100 dark:hover:bg-gray-800"
                            >
                              <ItemIcon className="h-4 w-4" />
                              <span>{item.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-700 dark:text-gray-200">Thêm sở thích khác (tùy chọn)</label>
                  <input
                    type="text"
                    className="w-full rounded-xl border border-brand-primary/30 bg-white px-3.5 py-2 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-white"
                    placeholder="Cách nhau bằng dấu phẩy"
                    value={formData.preferences.customInterests}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      preferences: { ...prev.preferences, customInterests: e.target.value },
                    }))}
                  />
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Nhịp độ du lịch</p>
                  <select
                    value={formData.preferences.pace}
                    onChange={(e) => handlePaceChange(e.target.value)}
                    className="rounded-lg border border-brand-primary/30 bg-white px-2.5 py-1.5 text-sm text-gray-800 focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-white"
                  >
                    {PACE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {PACE_OPTIONS.map((option) => {
                    const active = formData.preferences.pace === option.value;
                    return (
                      <motion.button
                        key={option.value}
                        type="button"
                        whileHover={{ y: -2 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => handlePaceChange(option.value)}
                        className={`flex h-full flex-col items-start gap-1 rounded-2xl border p-3 text-left transition ${
                          active
                            ? 'border-brand-primary bg-brand-primary text-white shadow-sm'
                            : 'border-brand-primary/30 bg-white text-gray-800 hover:border-brand-primary hover:text-brand-primary dark:border-brand-primary/50 dark:bg-gray-900 dark:text-white dark:hover:border-white dark:hover:text-white'
                        }`}
                      >
                        <span className="text-sm font-semibold">{option.label}</span>
                        <span
                            className={`text-sm line-clamp-2 ${active ? 'text-gray-100' : 'text-gray-500 dark:text-gray-300'}`}
                        >
                          {option.description}
                        </span>
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-gray-900 dark:text-gray-100">Lưu ý của người dùng<span className="text-gray-400"></span></label>
                <input
                  type="text"
                  className="w-full rounded-xl border border-brand-primary/30 bg-white px-3.5 py-2 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none dark:border-brand-primary/50 dark:bg-gray-900 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-white"
                  placeholder="VD: Muốn đi dạo nhiều, ưu tiên món chay, tránh hoạt động ngoài trời..."
                  value={formData.preferences.userNotes}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    preferences: { ...prev.preferences, userNotes: e.target.value },
                  }))}
                />
              </div>

              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <p className="text-sm text-gray-600 dark:text-gray-300"></p>
                <motion.button
                  type="submit"
                  whileHover={{ scale: 1.01, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition disabled:opacity-70 dark:bg-white dark:text-gray-900"
                >
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  <span>{isSubmitting ? 'Đang tạo...' : 'Tạo kế hoạch'}</span>
                </motion.button>
              </div>
            </form>
          </div>

          <div className="hidden lg:block space-y-3 rounded-2xl border border-brand-primary/20 bg-gray-50 p-4 text-sm text-gray-700 shadow-inner dark:border-brand-primary/30 dark:bg-gray-800/80 dark:text-gray-200">
            <div className="flex items-center gap-3">
              <PiggyBank className="h-5 w-5 text-brand-secondary" />
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Ngân sách / ngày</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(formData.preferences.budget)}</p>
                <p className="text-gray-500 dark:text-gray-300">{getBudgetLabel(formData.preferences.budget)}</p>
              </div>
            </div>
            <div className="rounded-xl border border-brand-primary/30 bg-white px-3 py-2 dark:border-brand-primary/50 dark:bg-gray-900/80">
              <p className="font-semibold text-gray-900 dark:text-gray-100">Tóm tắt nhanh</p>
              <ul className="mt-2 space-y-1 text-gray-600 dark:text-gray-300">
                <li>- {formData.numDays} ngày • {formData.startDate ? 'Khởi hành ' + formData.startDate : 'Chưa chọn ngày'}</li>
                <li>- {formData.preferences.interests.length} sở thích đã chọn</li>
                <li>- Nhịp độ: {PACE_OPTIONS.find(p => p.value === formData.preferences.pace)?.label || '...'}</li>
              </ul>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
