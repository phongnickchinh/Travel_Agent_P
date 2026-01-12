import { AnimatePresence, motion } from 'framer-motion';
import { Plus, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import SearchAutocomplete from '../../SearchAutocomplete';

const AddActivityModal = ({ isOpen, onClose, onAdd, location }) => {
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setSelected(null);
      setNote('');
    }
  }, [isOpen]);

  const handleSelect = (item) => {
    setSelected(item);
  };

  const handleAdd = () => {
    if (!selected) return;
    
    // Debug: Log selected item to check available fields
    console.log('[AddActivityModal] Selected item:', selected);
    console.log('[AddActivityModal] place_id:', selected.place_id);
    console.log('[AddActivityModal] id:', selected.id);
    console.log('[AddActivityModal] poi_id:', selected.poi_id);
    
    // Extract place_id from multiple possible fields
    const placeId = selected.place_id || selected.id || selected.poi_id;
    console.log('[AddActivityModal] Extracted placeId:', placeId);
    
    const newActivity = {
      poi_name: selected.name || selected.text,
      place_id: placeId,  // Use extracted place_id
      description: note || selected.description,
      address: selected.address || selected.description,
      category: Array.isArray(selected.types) ? selected.types[0] : selected.primary_type,
      location: selected.location || (selected.lat && selected.lng
        ? { latitude: selected.lat, longitude: selected.lng }
        : null),
      rating: selected.rating,
    };
    console.log('[AddActivityModal] newActivity:', newActivity);
    onAdd(newActivity);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <motion.div
            initial={{ scale: 0.95, y: 10, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: 10, opacity: 0 }}
            className="w-full max-w-xl max-h-[90vh] overflow-y-auto bg-white rounded-2xl shadow-2xl p-4 lg:p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-poppins font-semibold text-lg text-gray-900">Thêm hoạt động</h3>
              <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <SearchAutocomplete
                placeholder="Tìm địa điểm, nhà hàng, khách sạn..."
                onSelect={handleSelect}
                location={location}
              />

              <textarea
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
                rows={3}
                placeholder="Ghi chú thêm (tuỳ chọn)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700"
              >
                Hủy
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  handleAdd();
                  onClose();
                }}
                disabled={!selected}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white ${selected ? 'bg-brand-primary' : 'bg-gray-300 cursor-not-allowed'}`}
              >
                <Plus className="w-4 h-4" /> Thêm
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AddActivityModal;
