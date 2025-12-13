/**
 * CreatePlan Page - Travel Plan Creation Form
 * 
 * Features:
 * - Destination autocomplete via Elasticsearch
 * - Num days slider (1-30)
 * - Start date calendar picker
 * - Origin placeholder (future: Google Maps embed)
 * - Preferences: Multi-choice interests + Budget slider
 * 
 * Author: Travel Agent P Team
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import planAPI from '../../services/planApi';
import searchAPI from '../../services/searchApi';
import './CreatePlan.css';

// Available interest options
const INTEREST_OPTIONS = [
  { id: 'beach', label: 'Biển', icon: '🏖️' },
  { id: 'culture', label: 'Văn hóa', icon: '🏛️' },
  { id: 'food', label: 'Ẩm thực', icon: '🍜' },
  { id: 'nightlife', label: 'Giải trí đêm', icon: '🌙' },
  { id: 'nature', label: 'Thiên nhiên', icon: '🌿' },
  { id: 'adventure', label: 'Phiêu lưu', icon: '🧗' },
  { id: 'shopping', label: 'Mua sắm', icon: '🛍️' },
  { id: 'relaxation', label: 'Thư giãn', icon: '🧘' },
  { id: 'history', label: 'Lịch sử', icon: '📜' },
  { id: 'photography', label: 'Chụp ảnh', icon: '📸' },
  { id: 'family', label: 'Gia đình', icon: '👨‍👩‍👧‍👦' },
  { id: 'romantic', label: 'Lãng mạn', icon: '💑' },
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

export default function CreatePlan() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    destination: '',
    destinationId: null, // POI ID if selected from autocomplete
    numDays: 3,
    startDate: '',
    origin: null, // Future: Google Maps location
    preferences: {
      interests: [],
      budget: 3500000, // Default: Thoải mái
      budgetLevel: 'medium',
      pace: 'moderate',
      dietary: '',
      customInterests: '',
    }
  });

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

  // Refs
  const destinationInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Calculate min date (today)
  const today = new Date().toISOString().split('T')[0];

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
      const results = await searchAPI.debouncedAutocomplete(value, { limit: 8 });
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
    const displayName = suggestion.name_vi || suggestion.name_en || suggestion.name || suggestion.query;
    setDestinationQuery(displayName);
    setFormData(prev => ({
      ...prev,
      destination: displayName,
      destinationId: suggestion.poi_id || suggestion._id || null
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
        destination: formData.destination,
        num_days: formData.numDays,
        start_date: formData.startDate,
        origin: formData.origin, // null for now
        preferences: {
          interests: formData.preferences.interests,
          budget: formData.preferences.budget,
          budget_level: formData.preferences.budgetLevel,
          pace: formData.preferences.pace,
          dietary: formData.preferences.dietary || null,
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
        // Navigate to plan detail or list after short delay
        setTimeout(() => {
          navigate(`/dashboard/${user?.username}?plan=${result.data.plan_id}`);
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

  return (
    <div className="create-plan-container">
      <div className="create-plan-card">
        {/* Header */}
        <div className="create-plan-header">
          <button className="back-button" onClick={() => navigate(-1)}>
            ← Quay lại
          </button>
          <h1>✨ Tạo Kế Hoạch Du Lịch</h1>
          <p>Để AI lên lịch trình hoàn hảo cho bạn</p>
        </div>

        {/* Form */}
        <form className="create-plan-form" onSubmit={handleSubmit}>
          {/* Error/Success Messages */}
          {error && <div className="message error-message">{error}</div>}
          {success && <div className="message success-message">{success}</div>}

          {/* Title (Optional) */}
          <div className="form-group">
            <label className="form-label">
              📝 Tên chuyến đi <span className="optional">(Tùy chọn)</span>
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="VD: Nghỉ dưỡng Đà Nẵng cùng gia đình"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              maxLength={200}
            />
          </div>

          {/* Destination with Autocomplete */}
          <div className="form-group destination-group">
            <label className="form-label">
              📍 Điểm đến <span className="required">*</span>
            </label>
            <div className="autocomplete-wrapper">
              <input
                ref={destinationInputRef}
                type="text"
                className="form-input destination-input"
                placeholder="Nhập tên thành phố, địa điểm..."
                value={destinationQuery}
                onChange={(e) => handleDestinationChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => destinationQuery.length >= 2 && setShowSuggestions(true)}
                autoComplete="off"
              />
              {isSearching && <span className="search-spinner">🔍</span>}
              
              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <ul className="suggestions-list" ref={suggestionsRef}>
                  {suggestions.map((suggestion, index) => (
                    <li
                      key={suggestion.poi_id || suggestion._id || index}
                      className={`suggestion-item ${index === selectedSuggestionIndex ? 'selected' : ''}`}
                      onClick={() => handleSelectSuggestion(suggestion)}
                      onMouseEnter={() => setSelectedSuggestionIndex(index)}
                    >
                      <span className="suggestion-icon">
                        {suggestion.category === 'beach' ? '🏖️' :
                         suggestion.category === 'restaurant' ? '🍽️' :
                         suggestion.category === 'hotel' ? '🏨' :
                         suggestion.category === 'attraction' ? '🎡' : '📍'}
                      </span>
                      <div className="suggestion-content">
                        <span className="suggestion-name">
                          {suggestion.name_vi || suggestion.name_en || suggestion.name}
                        </span>
                        {suggestion.address && (
                          <span className="suggestion-address">{suggestion.address}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Number of Days Slider */}
          <div className="form-group">
            <label className="form-label">
              📅 Số ngày: <span className="value-display">{formData.numDays} ngày</span>
            </label>
            <div className="slider-container">
              <input
                type="range"
                className="slider days-slider"
                min="1"
                max="30"
                value={formData.numDays}
                onChange={(e) => handleNumDaysChange(e.target.value)}
              />
              <div className="slider-labels">
                <span>1 ngày</span>
                <span>15 ngày</span>
                <span>30 ngày</span>
              </div>
            </div>
          </div>

          {/* Start Date */}
          <div className="form-group">
            <label className="form-label">
              🗓️ Ngày bắt đầu <span className="required">*</span>
            </label>
            <input
              type="date"
              className="form-input date-input"
              value={formData.startDate}
              onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
              min={today}
            />
          </div>

          {/* Origin (Placeholder) */}
          <div className="form-group origin-group">
            <label className="form-label">
              🚗 Điểm xuất phát <span className="optional">(Tùy chọn)</span>
            </label>
            <div className="origin-placeholder">
              <div className="placeholder-icon">🗺️</div>
              <p>Tính năng Google Maps sẽ sớm ra mắt!</p>
              <span className="placeholder-note">Cho phép chọn địa điểm xuất phát để tối ưu lịch trình</span>
            </div>
          </div>

          {/* Divider */}
          <div className="form-divider">
            <span>Sở thích & Ngân sách</span>
          </div>

          {/* Interests Multi-Choice */}
          <div className="form-group">
            <label className="form-label">
              ❤️ Sở thích <span className="required">*</span>
              <span className="hint">(Chọn nhiều)</span>
            </label>
            <div className="interests-grid">
              {INTEREST_OPTIONS.map((interest) => (
                <button
                  key={interest.id}
                  type="button"
                  className={`interest-chip ${formData.preferences.interests.includes(interest.id) ? 'selected' : ''}`}
                  onClick={() => handleInterestToggle(interest.id)}
                >
                  <span className="chip-icon">{interest.icon}</span>
                  <span className="chip-label">{interest.label}</span>
                </button>
              ))}
            </div>
            
            {/* Custom Interests */}
            <div className="custom-interests">
              <input
                type="text"
                className="form-input custom-input"
                placeholder="Thêm sở thích khác (cách nhau bằng dấu phẩy)"
                value={formData.preferences.customInterests}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  preferences: { ...prev.preferences, customInterests: e.target.value }
                }))}
              />
            </div>
          </div>

          {/* Budget Slider (Non-linear) */}
          <div className="form-group">
            <label className="form-label">
              💰 Ngân sách / ngày
            </label>
            <div className="budget-display">
              <span className="budget-value">{formatCurrency(formData.preferences.budget)}</span>
              <span className="budget-label">{getBudgetLabel(formData.preferences.budget)}</span>
            </div>
            <div className="slider-container budget-slider-container">
              <input
                type="range"
                className="slider budget-slider"
                min="0"
                max="100"
                value={budgetPosition}
                onChange={(e) => handleBudgetChange(parseInt(e.target.value, 10))}
              />
              <div className="budget-marks">
                {BUDGET_MARKS.filter((_, i) => i % 2 === 0).map((mark) => (
                  <div 
                    key={mark.position} 
                    className="budget-mark"
                    style={{ left: `${mark.position}%` }}
                  >
                    <span className="mark-dot"></span>
                    <span className="mark-label">{mark.sublabel}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Pace Selection */}
          <div className="form-group">
            <label className="form-label">
              🏃 Nhịp độ du lịch
            </label>
            <div className="pace-options">
              {PACE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={`pace-option ${formData.preferences.pace === option.value ? 'selected' : ''}`}
                  onClick={() => handlePaceChange(option.value)}
                >
                  <span className="pace-label">{option.label}</span>
                  <span className="pace-description">{option.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Dietary (Optional) */}
          <div className="form-group">
            <label className="form-label">
              🥗 Yêu cầu ăn uống <span className="optional">(Tùy chọn)</span>
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="VD: Chay, không gluten, halal..."
              value={formData.preferences.dietary}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                preferences: { ...prev.preferences, dietary: e.target.value }
              }))}
            />
          </div>

          {/* Submit Button */}
          <button 
            type="submit" 
            className={`btn btn-submit ${isSubmitting ? 'loading' : ''}`}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner"></span>
                <span>Đang tạo...</span>
              </>
            ) : (
              <>
                <span>🚀</span>
                <span>Tạo Kế Hoạch</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
