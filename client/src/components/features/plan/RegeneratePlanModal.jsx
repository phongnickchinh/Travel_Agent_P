/**
 * RegeneratePlanModal - Compact plan regeneration with essential controls
 * 
 * Features:
 * - Number of days input
 * - Budget slider
 * - Interest selection (text-only, no icons)
 * - Pace options
 * - Shows current/old values
 * - Dark theme support
 */

import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, ChevronUp, Loader2, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

// Interest options (text-only, no icons)
const INTEREST_OPTIONS = [
  { id: 'beach', label: 'Biển', googleType: 'beach' },
  { id: 'museum', label: 'Văn hóa', googleType: 'museum' },
  { id: 'restaurant', label: 'Ẩm thực', googleType: 'restaurant' },
  { id: 'night_club', label: 'Nightlife', googleType: 'night_club' },
  { id: 'park', label: 'Thiên nhiên', googleType: 'park' },
  { id: 'amusement_park', label: 'Vui chơi', googleType: 'amusement_park' },
  { id: 'shopping_mall', label: 'Mua sắm', googleType: 'shopping_mall' },
  { id: 'spa', label: 'Thư giãn', googleType: 'spa' },
  { id: 'historical_landmark', label: 'Lịch sử', googleType: 'historical_landmark' },
  { id: 'tourist_attraction', label: 'Tham quan', googleType: 'tourist_attraction' },
  { id: 'zoo', label: 'Gia đình', googleType: 'zoo' },
  { id: 'cafe', label: 'Cafe', googleType: 'cafe' },
];

// Budget levels
const BUDGET_MARKS = [
  { position: 0, value: 500000, label: '500K' },
  { position: 15, value: 1000000, label: '1M' },
  { position: 30, value: 2000000, label: '2M' },
  { position: 45, value: 3500000, label: '3.5M' },
  { position: 60, value: 5000000, label: '5M' },
  { position: 75, value: 10000000, label: '10M' },
  { position: 90, value: 20000000, label: '20M' },
  { position: 100, value: 50000000, label: '50M+' },
];

// Pace options (text-only)
const PACE_OPTIONS = [
  { value: 'relaxed', label: 'Thư thả', description: '2-3 địa điểm/ngày' },
  { value: 'moderate', label: 'Vừa phải', description: '3-4 địa điểm/ngày' },
  { value: 'intensive', label: 'Khám phá', description: '5+ địa điểm/ngày' },
];

const RegeneratePlanModal = ({ 
  isOpen, 
  onClose, 
  onSubmit, 
  initialPreferences = {}, 
  loading = false,
  planTitle = '',
  currentNumDays = 3  // Current number of days from plan
}) => {
  // Form state (initialized from current plan preferences)
  const [numDays, setNumDays] = useState(currentNumDays);
  const [interests, setInterests] = useState(initialPreferences.interests || initialPreferences.types || []);
  const [budget, setBudget] = useState(initialPreferences.budget || 3500000);
  const [budgetPosition, setBudgetPosition] = useState(() => {
    const initBudget = initialPreferences.budget || 3500000;
    for (let i = BUDGET_MARKS.length - 1; i >= 0; i--) {
      if (initBudget >= BUDGET_MARKS[i].value) {
        return BUDGET_MARKS[i].position;
      }
    }
    return 45;
  });
  const [pace, setPace] = useState(initialPreferences.pace || 'moderate');
  const [dietary, setDietary] = useState(initialPreferences.dietary || '');
  
  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Reset form when modal opens with new initialPreferences
  useEffect(() => {
    if (isOpen) {
      setNumDays(currentNumDays);
      setInterests(initialPreferences.interests || initialPreferences.types || []);
      setBudget(initialPreferences.budget || 3500000);
      setPace(initialPreferences.pace || 'moderate');
      setDietary(initialPreferences.dietary || '');
    }
  }, [isOpen, currentNumDays, initialPreferences]);

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

  const formatBudget = (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 1)}M`;
    }
    return `${(value / 1000).toFixed(0)}K`;
  };

  const handleBudgetChange = (e) => {
    const pos = Number(e.target.value);
    setBudgetPosition(pos);
    setBudget(getBudgetFromPosition(pos));
  };

  const toggleInterest = (interestId) => {
    setInterests(prev => 
      prev.includes(interestId) 
        ? prev.filter(id => id !== interestId) 
        : [...prev, interestId]
    );
  };

  const handleSubmit = () => {
    onSubmit({
      num_days: numDays,
      preferences: {
        interests,
        types: interests, // Keep backward compatibility
        budget,
        pace,
        dietary: dietary.trim() || undefined,
      },
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ scale: 0.95, y: 10, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: 10, opacity: 0 }}
            className="w-full max-w-xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 className="font-poppins font-semibold text-gray-900 dark:text-white">
                  Tái tạo kế hoạch
                </h3>
                {planTitle && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">
                    {planTitle}
                  </p>
                )}
              </div>
              <motion.button 
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose} 
                className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              </motion.button>
            </div>

            {/* Content - Scrollable */}
            <div className="px-5 py-4 max-h-[65vh] overflow-y-auto space-y-4">
              
              {/* Number of Days */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Số ngày
                  </label>
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    (hiện tại: {currentNumDays} ngày)
                  </span>
                </div>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={numDays}
                  onChange={(e) => setNumDays(Math.max(1, Math.min(30, parseInt(e.target.value) || 1)))}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                />
              </div>

              {/* Budget Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Ngân sách / ngày
                  </label>
                  <span className="text-sm font-bold text-brand-primary dark:text-brand-secondary">
                    {formatBudget(budget)} VND
                  </span>
                </div>
                
                <div className="relative pt-1">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={budgetPosition}
                    onChange={handleBudgetChange}
                    className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer accent-brand-primary"
                  />
                  {/* Budget marks */}
                  <div className="flex justify-between mt-1.5 px-0.5">
                    {BUDGET_MARKS.filter((_, i) => i % 2 === 0).map((mark) => (
                      <span 
                        key={mark.position} 
                        className="text-xs text-gray-400 dark:text-gray-500"
                      >
                        {mark.label}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Pace Selection */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Nhịp độ chuyến đi
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {PACE_OPTIONS.map((option) => (
                    <motion.button
                      key={option.value}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setPace(option.value)}
                      className={`p-2.5 rounded-xl border-2 transition-all text-center ${
                        pace === option.value
                          ? 'border-brand-primary bg-brand-muted dark:bg-brand-primary/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-brand-primary/50 dark:hover:border-brand-primary/50'
                      }`}
                    >
                      <p className={`text-xs font-medium ${
                        pace === option.value 
                          ? 'text-brand-primary dark:text-brand-secondary' 
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {option.label}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                        {option.description}
                      </p>
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Interests Grid */}
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Sở thích ({interests.length} đã chọn)
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {INTEREST_OPTIONS.map((option) => {
                    const isActive = interests.includes(option.id);
                    return (
                      <motion.button
                        key={option.id}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => toggleInterest(option.id)}
                        className={`px-2 py-1.5 rounded-lg border transition-all text-center ${
                          isActive
                            ? 'border-brand-primary bg-brand-muted dark:bg-brand-primary/20'
                            : 'border-gray-200 dark:border-gray-600 hover:border-brand-primary/50'
                        }`}
                      >
                        <p className={`text-xs font-medium truncate ${
                          isActive 
                            ? 'text-brand-primary dark:text-brand-secondary' 
                            : 'text-gray-600 dark:text-gray-400'
                        }`}>
                          {option.label}
                        </p>
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Advanced Options (Collapsible) */}
              <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                >
                  {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  Tùy chọn nâng cao
                </button>
                
                <AnimatePresence>
                  {showAdvanced && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 space-y-3">
                        {/* Dietary Preferences */}
                        <div className="space-y-1.5">
                          <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            Chế độ ăn đặc biệt
                          </label>
                          <input
                            type="text"
                            value={dietary}
                            onChange={(e) => setDietary(e.target.value)}
                            placeholder="VD: Chay, không gluten, halal..."
                            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                          />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-2">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Hủy
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSubmit}
                disabled={loading}
                className="px-4 py-1.5 rounded-lg bg-brand-primary text-white text-sm font-medium inline-flex items-center gap-1.5 hover:bg-brand-dark transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Đang tạo...
                  </>
                ) : (
                  'Tái tạo'
                )}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RegeneratePlanModal;
