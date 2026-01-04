import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion } from 'framer-motion';
import { Check, Clock, GripVertical, Pencil, Trash2, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

const categoryIconMap = {
  restaurant: 'Utensils',
  food: 'Utensils',
  cafe: 'Coffee',
  coffee: 'Coffee',
  bar: 'Wine',
  nightlife: 'Wine',
  shopping: 'ShoppingBag',
  retail: 'ShoppingBag',
  park: 'TreePine',
  nature: 'TreePine',
  museum: 'Landmark',
  landmark: 'Landmark',
  temple: 'Church',
  church: 'Church',
  // hotel: 'Bed',
  // accommodation: 'Bed',
  spa: 'Sparkles',
  wellness: 'Sparkles',
};

const iconComponents = {
  Utensils: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 3v7a4 4 0 0 0 4 4h1v7"></path><path d="M16 3v7"></path><path d="M19 4v6a3 3 0 0 1-3 3h-1v8"></path></svg>,
  Coffee: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v7a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4Z"></path><path d="M6 2v2"></path><path d="M10 2v2"></path><path d="M14 2v2"></path></svg>,
  Wine: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 22h8"></path><path d="M7 10h10"></path><path d="M12 15v7"></path><path d="M12 15a5 5 0 0 0 5-5V3H7v7a5 5 0 0 0 5 5Z"></path></svg>,
  ShoppingBag: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"></path><path d="M3 6h18"></path><path d="M16 10a4 4 0 0 1-8 0"></path></svg>,
  TreePine: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 6 8h12Z"></path><path d="M12 8 6 14h12Z"></path><path d="M12 14 7 20h10Z"></path><path d="M12 22v-4"></path></svg>,
  Landmark: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 22 3-3 3 3 3-3 3 3 3-3 3 3"></path><path d="M6 19V8"></path><path d="M10 19V8"></path><path d="M14 19V8"></path><path d="M18 19V8"></path><path d="M8 8h8"></path><path d="M6 11h12"></path><path d="M3 8l9-6 9 6"></path></svg>,
  Church: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22V12"></path><path d="M12 2v2"></path><path d="M10 4h4"></path><path d="m3 6 9-4 9 4"></path><path d="M4 10h16"></path><path d="M6 6v14"></path><path d="M18 6v14"></path><path d="M10 18h4"></path></svg>,
  Bed: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 4v16"></path><path d="M2 8h20v12"></path><path d="M6 8v12"></path><path d="M6 12h6"></path><path d="M16 12h2"></path></svg>,
  Sparkles: (props) => <svg {...props} viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v2"></path><path d="M16.2 7.8 14 10"></path><path d="m16.2 12.2-2.2-2.2"></path><path d="M12 13v8"></path><path d="M7.8 12.2 10 10"></path><path d="M7.8 7.8 10 10"></path><path d="M5 10h14"></path><path d="m7.8 15.8 2.2-2.2"></path><path d="m16.2 15.8-2.2-2.2"></path></svg>,
};

const getTypeIcon = (category) => {
  let key = '';
  if (Array.isArray(category)) {
    key = category.join(' ').toLowerCase();
  } else {
    key = (category || '').toLowerCase();
  }
  
  const iconKey = Object.entries(categoryIconMap).find(([k]) => key.includes(k))?.[1] || 'Landmark';
  const IconComp = iconComponents[iconKey];
  return IconComp ? <IconComp className="w-4 h-4" /> : null;
};

const ActivityItem = ({
  activity,
  estimatedTime,
  globalIndex,
  onChange,
  onDelete,
  disabled = false,
  isAccommodation = false,
  onHover,
  onLeave,
  dragHandle,
  listeners,
  attributes,
  setNodeRef,
  transform,
  transition,
  isDragging,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [localActivity, setLocalActivity] = useState(activity || {});
  const [localTime, setLocalTime] = useState(estimatedTime || '');
  const [isNameHovered, setIsNameHovered] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setLocalActivity(activity || {});
      setLocalTime(estimatedTime || '');
    }
  }, [activity, estimatedTime, isEditing]);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: isDragging ? 'none' : transition,
    zIndex: isDragging ? 9999 : undefined,
    willChange: 'transform',
  };

  const handleSave = () => {
    onChange({ ...localActivity }, localTime);
    setIsEditing(false);
  };

  const description = useMemo(() => localActivity.description || localActivity.activity || '', [localActivity]);
  const poiName = useMemo(() => localActivity.poi_name || localActivity.name || localActivity.poi?.name || 'Địa điểm', [localActivity]);
  const category = useMemo(() => localActivity.category || localActivity.poi?.category, [localActivity]);

  return (
    <motion.li
      ref={setNodeRef}
      {...attributes}
      style={style}
      className={`group border-l-3 pl-4 pr-2 py-3 rounded-r-lg bg-white dark:bg-gray-800 shadow-sm dark:shadow-gray-900/20 transition-all ${
        isDragging ? 'ring-2 ring-brand-primary/40 bg-brand-muted/50 dark:bg-brand-primary/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
      } ${isAccommodation ? 'border-l-purple-400' : 'border-l-brand-primary'}`}
    >
      <div className="flex items-start gap-3">
        {!disabled && (
          <div
            {...dragHandle}
            {...listeners}
            className={`mt-1 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'} text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300`}
            aria-label="Kéo để sắp xếp"
          >
            <GripVertical className="w-4 h-4" />
          </div>
        )}
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold rounded-full bg-brand-primary text-white">
              {globalIndex}
            </span>
            <span className="text-gray-500 dark:text-gray-400">{getTypeIcon(category)}</span>
            <span
              className={`font-semibold cursor-pointer transition-all duration-100 ${
                isNameHovered 
                  ? ('text-brand-primary dark:text-brand-secondary underline')
                  : ('text-gray-900 dark:text-white')
              }`}
              
              onMouseEnter={() => {
                setIsNameHovered(true);
                onHover?.(globalIndex);
              }}
              onMouseLeave={() => {
                setIsNameHovered(false);
                onLeave?.();
              }}
            >
              {poiName}
            </span>
            {localTime && <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">{localTime}</span>}
          </div>

          {isEditing ? (
            <div className="space-y-2">
              <label className="block text-xs text-gray-500 dark:text-gray-400">Khung giờ (HH:MM-HH:MM)</label>
              <input
                value={localTime}
                onChange={(e) => setLocalTime(e.target.value)}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-primary"
                placeholder="09:00-10:30"
                disabled={disabled}
              />
              <label className="block text-xs text-gray-500 dark:text-gray-400">Mô tả</label>
              <textarea
                value={description}
                onChange={(e) => setLocalActivity((prev) => ({ ...prev, description: e.target.value }))}
                className="w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-primary"
                rows={2}
                disabled={disabled}
              />
              <div className="flex items-center gap-2">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSave}
                  disabled={disabled}
                  className="inline-flex items-center gap-1 px-3 py-2 bg-brand-primary text-white rounded-lg text-sm"
                >
                  <Check className="w-4 h-4" /> Lưu
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setIsEditing(false)}
                  className="inline-flex items-center gap-1 px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm"
                >
                  <X className="w-4 h-4" /> Hủy
                </motion.button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {description && <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>}
              {localActivity.address && (
                <p className="text-xs text-gray-400 dark:text-gray-500">📍 {localActivity.address}</p>
              )}
            </div>
          )}

          {!disabled && !isEditing && (
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <Pencil className="w-3 h-3" /> Chỉnh sửa
              </button>
              <span className="text-gray-300 dark:text-gray-600">•</span>
              <button
                onClick={onDelete}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400"
              >
                <Trash2 className="w-3 h-3" /> Xóa
              </button>
              {localTime === '' && (
                <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                  <Clock className="w-3 h-3" /> Thêm khung giờ để sắp xếp tối ưu
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.li>
  );
};

export const SortableActivityItem = (props) => {
  const sortable = useSortable({ id: props.id, disabled: props.disabled });
  return (
    <ActivityItem
      {...props}
      dragHandle={{ ref: sortable.setActivatorNodeRef }}
      setNodeRef={sortable.setNodeRef}
      attributes={sortable.attributes}
      listeners={sortable.listeners}
      transform={sortable.transform}
      transition={sortable.transition}
      isDragging={sortable.isDragging}
    />
  );
};

export default ActivityItem;
