import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, Loader2, X } from 'lucide-react';
import { useState } from 'react';

const paceOptions = [
  { value: 'relaxed', label: 'Thoải mái' },
  { value: 'balanced', label: 'Vừa phải' },
  { value: 'fast', label: 'Nhanh' },
];

const typeOptions = [
  'nature',
  'beach',
  'culture',
  'food',
  'shopping',
  'nightlife',
  'museum',
  'temple',
];

const RegeneratePlanModal = ({ isOpen, onClose, onSubmit, initialPreferences = {}, loading = false }) => {
  const [budget, setBudget] = useState(initialPreferences.budget || '');
  const [pace, setPace] = useState(initialPreferences.pace || 'balanced');
  const [types, setTypes] = useState(initialPreferences.types || []);

  const toggleType = (type) => {
    setTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSubmit = () => {
    onSubmit({
      preferences: {
        budget: budget ? Number(budget) : undefined,
        pace,
        types,
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
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center"
        >
          <motion.div
            initial={{ scale: 0.95, y: 10, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: 10, opacity: 0 }}
            className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl p-6 space-y-5"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-poppins font-semibold text-lg text-gray-900">Tái tạo kế hoạch</h3>
                <p className="text-sm text-gray-500">Cập nhật ngân sách, nhịp độ và sở thích để AI tạo lại lịch trình.</p>
              </div>
              <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Ngân sách (VND)</label>
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-primary"
                  placeholder="5,000,000"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-gray-700">Nhịp độ chuyến đi</label>
                <div className="grid grid-cols-3 gap-2">
                  {paceOptions.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => setPace(p.value)}
                      className={`px-3 py-2 rounded-lg border text-sm flex items-center gap-1 justify-center ${
                        pace === p.value
                          ? 'border-brand-primary bg-brand-muted text-brand-primary'
                          : 'border-gray-200 hover:border-brand-primary hover:bg-brand-muted/50'
                      }`}
                    >
                      {pace === p.value && <CheckCircle2 className="w-4 h-4" />} {p.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700">Sở thích / Loại hình</label>
              <div className="flex flex-wrap gap-2">
                {typeOptions.map((t) => {
                  const active = types.includes(t);
                  return (
                    <button
                      key={t}
                      onClick={() => toggleType(t)}
                      className={`px-3 py-2 rounded-full text-sm border ${
                        active
                          ? 'border-brand-primary bg-brand-muted text-brand-primary'
                          : 'border-gray-200 hover:border-brand-primary hover:bg-brand-muted/60'
                      }`}
                    >
                      {t}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700"
                disabled={loading}
              >
                Hủy
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSubmit}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-brand-primary text-white inline-flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Tái tạo
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RegeneratePlanModal;
