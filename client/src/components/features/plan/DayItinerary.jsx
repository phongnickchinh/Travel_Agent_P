import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, arrayMove, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { EditableNotes } from '../../ui/EditableField';
import { SortableActivityItem } from './ActivityItem';
import AddActivityModal from './AddActivityModal';
const DayItinerary = ({
  day,
  dayNumber,
  startIndex,
  isPublicView,
  onSave,
  location,
  onHover,
  onLeave
}) => {
  const mergeActivitiesWithTypes = (activities, types, poiIds) => {
    if (!activities) return [];
    return activities.map((activity, index) => {
      let item = typeof activity === 'string' ? { activity } : { ...activity };
      
      // Ensure we have a description/activity field
      if (!item.activity && typeof activity === 'string') item.activity = activity;
      
      // Merge category
      if (types && types[index]) {
        item.category = types[index];
      }
      
      // Merge POI ID
      if (poiIds && poiIds[index]) {
        item.poi_id = poiIds[index];
      }
      
      return item;
    });
  };

  const [items, setItems] = useState(mergeActivitiesWithTypes(day.activities, day.types, day.poi_ids));
  const [times, setTimes] = useState(day.estimated_times || []);
  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setItems(mergeActivitiesWithTypes(day.activities, day.types, day.poi_ids));
    setTimes(day.estimated_times || []);
  }, [day]);

  const handlePersist = async (nextItems, nextTimes) => {
    setItems(nextItems);
    setTimes(nextTimes);
    if (isPublicView) return;
    setSaving(true);
    try {
      const nextActivities = nextItems.map(item => item.activity || item.description || '');
      const nextPoiIds = nextItems.map(item => item.poi_id || null);
      await onSave(dayNumber, nextActivities, nextTimes, nextPoiIds);
    } finally {
      setSaving(false);
    }
  };

  const handleDragEnd = (event) => {
    if (isPublicView) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex((_, idx) => `act-${idx}` === active.id);
    const newIndex = items.findIndex((_, idx) => `act-${idx}` === over.id);
    const nextItems = arrayMove(items, oldIndex, newIndex);
    const nextTimes = arrayMove(times, oldIndex, newIndex);
    handlePersist(nextItems, nextTimes);
  };

  const handleUpdate = (index, updatedActivity, updatedTime) => {
    const nextItems = items.map((item, idx) => (idx === index ? updatedActivity : item));
    const nextTimes = times.map((t, idx) => (idx === index ? updatedTime : t));
    handlePersist(nextItems, nextTimes);
  };

  const handleDelete = (index) => {
    const nextItems = items.filter((_, idx) => idx !== index);
    const nextTimes = times.filter((_, idx) => idx !== index);
    handlePersist(nextItems, nextTimes);
  };

  const handleAdd = (activity) => {
    const nextItems = [...items, activity];
    const nextTimes = [...times, ''];
    handlePersist(nextItems, nextTimes);
  };

  const estimatedItems = useMemo(() => items.map((item, idx) => ({ id: `act-${idx}`, item, time: times[idx] || '' })), [items, times]);

  const isAccommodationCategory = (category) => {
    if (!category) return false;
    const catStr = Array.isArray(category) ? category.join(' ').toLowerCase() : String(category).toLowerCase();
    return catStr.includes('hotel') || catStr.includes('accommodation');
  };

  return (
    <div className="p-6">
    {/* Day Notes - Editable for owner */}
    <div className="px-6">
        <div className="border-b border-gray-100 pb-6">
            {isPublicView ? (
            // Public view - static display
            day.notes && (
                <p className="text-sm text-gray-500 italic">
                💡 {day.notes}
                </p>
            )
            ) : (
            // Owner view - editable
            <EditableNotes
                value={day.notes || ''}
                onSave={(newNotes) => handleSaveDayNotes(dayIndex + 1, newNotes)}
                maxLength={500}
            />
            )}
        </div>
    </div>
      {estimatedItems.length === 0 ? (
        <p className="text-gray-500 text-center py-4">Chưa có hoạt động cho ngày này</p>
      ) : (
        <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={estimatedItems.map((it) => it.id)} strategy={verticalListSortingStrategy}>
            <ul className="space-y-3">
              {estimatedItems.map(({ id, item, time }, idx) => (
                <SortableActivityItem
                  key={id}
                  id={id}
                  activity={item}
                  estimatedTime={time}
                  globalIndex={startIndex + idx + 1}
                  disabled={isPublicView}
                  isAccommodation={isAccommodationCategory(item?.category)}
                  onChange={(updatedActivity, updatedTime) => handleUpdate(idx, updatedActivity, updatedTime)}
                  onDelete={() => handleDelete(idx)}
                  onHover={onHover}
                  onLeave={onLeave}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
      )}

    <div className="flex items-center justify-between mt-3">
        <div className="text-sm text-gray-500">
          {saving && !isPublicView ? 'Đang lưu...' : null}
        </div>
        {!isPublicView && (
          <motion.button
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-primary text-white text-sm shadow"
          >
            <Plus className="w-4 h-4" /> Thêm hoạt động
          </motion.button>
        )}
    </div>

      <AddActivityModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAdd}
        location={location}
      />
    </div>
  );
};

export default DayItinerary;
