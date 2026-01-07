import { DndContext, DragOverlay, closestCenter } from '@dnd-kit/core';
import { SortableContext, arrayMove, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { motion } from 'framer-motion';
import { GripVertical, Plus } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { EditableNotes } from '../../ui/EditableField';
import { SortableActivityItem } from './ActivityItem';
import AddActivityModal from './AddActivityModal';
const DayItinerary = ({
  day,
  dayNumber,
  startIndex,
  isPublicView,
  onSave,
  onAddActivityFromPOI,
  location,
  onHover,
  onLeave
}) => {
  const mergeActivitiesWithTypes = (activities, types, poiIds, estimatedTimes) => {
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

      // Attach estimated time locally (does not mean we'll send it on reorder)
      item.estimated_time = (estimatedTimes && estimatedTimes[index]) || '';

      return item;
    });
  };

  const [items, setItems] = useState(mergeActivitiesWithTypes(day.activities, day.types, day.poi_ids, day.estimated_times));
  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const isPendingUpdate = useRef(false); // Track optimistic updates
  const [activeId, setActiveId] = useState(null);

  // Memoized estimated items with stable IDs for DnD
  const estimatedItems = useMemo(
    () => items.map((item, idx) => ({
      // Use stable ID: poi_id if exists, otherwise activity content hash
      id: item.poi_id || `act-${item.activity || item.description || ''}-${idx}`,
      item,
      time: item.estimated_time || ''
    })),
    [items]
  );

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
    console.log('[DayItinerary] Drag started:', event.active.id);
  };

  const handleDragCancel = () => {
    setActiveId(null);
    console.log('[DayItinerary] Drag cancelled');
  };

  useEffect(() => {
    // Skip prop sync if we're in the middle of an optimistic update
    // This prevents the "bounce back" effect during drag operations
    if (isPendingUpdate.current) {
      console.log('[DayItinerary] Skipping prop sync - pending update');
      return;
    }
    
    console.log('[DayItinerary] Syncing props to state');
    setItems(mergeActivitiesWithTypes(day.activities, day.types, day.poi_ids, day.estimated_times));
  }, [day]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePersist = async (nextItems, options = { sendTimes: false }) => {
    console.log('[DayItinerary] handlePersist called', options);

    // Store previous state for rollback on error
    const prevItems = items;

    // Optimistic update: immediately update UI
    setItems(nextItems);

    if (isPublicView) return;

    // Mark as pending to prevent prop sync from overwriting
    isPendingUpdate.current = true;
    setSaving(true);
    console.log('[DayItinerary] isPendingUpdate set to TRUE');

    try {
      const nextActivities = nextItems.map(item => item.activity || item.description || '');
      const nextPoiIds = nextItems.map(item => item.poi_id || null);
      const nextTimes = options.sendTimes ? nextItems.map(item => item.estimated_time || '') : undefined;
      await onSave(dayNumber, nextActivities, nextTimes, nextPoiIds);
      console.log('[DayItinerary] Save successful');
      // Success: keep the optimistic update
    } catch (error) {
      // Error: rollback to previous state
      console.error('[DayItinerary] Save failed, rolling back:', error);
      setItems(prevItems);
      // Optionally show error toast here
    } finally {
      setSaving(false);
      isPendingUpdate.current = false;
      console.log('[DayItinerary] isPendingUpdate set to FALSE');
    }
  }; 

  const handleDragEnd = (event) => {
    if (isPublicView) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    console.log('[DayItinerary] handleDragEnd - active:', active.id, 'over:', over.id);

    // Find indices by matching the stable IDs from estimatedItems
    const oldIndex = estimatedItems.findIndex(item => item.id === active.id);
    const newIndex = estimatedItems.findIndex(item => item.id === over.id);
    
    console.log('[DayItinerary] Moving from index', oldIndex, 'to', newIndex);
    
    if (oldIndex === -1 || newIndex === -1) {
      console.error('[DayItinerary] Invalid drag indices');
      return;
    }
    
    const nextItems = arrayMove(items, oldIndex, newIndex);
    // DO NOT move estimated times array on reorder - we keep times unchanged unless explicitly edited
    handlePersist(nextItems, { sendTimes: false });
    // Clear active overlay immediately after drop so overlay follows cursor cleanly
    setActiveId(null);
  };

  const handleUpdate = (index, updatedActivity, updatedTime) => {
    const nextItems = items.map((item, idx) => (
      idx === index ? { ...item, ...updatedActivity, estimated_time: updatedTime ?? item.estimated_time } : item
    ));

    const sendTimes = typeof updatedTime !== 'undefined' && updatedTime !== items[index].estimated_time;

    handlePersist(nextItems, { sendTimes });
  };

  const handleDelete = (index) => {
    const nextItems = items.filter((_, idx) => idx !== index);
    // Do not change estimated_times on delete unless explicitly edited
    handlePersist(nextItems, { sendTimes: false });
  };

  const handleAdd = async (activity) => {
    // Debug: Log activity and callback availability
    console.log('[DayItinerary] handleAdd called with activity:', activity);
    console.log('[DayItinerary] place_id:', activity.place_id);
    console.log('[DayItinerary] onAddActivityFromPOI exists:', !!onAddActivityFromPOI);
    
    // If activity has place_id, use new API endpoint
    if (activity.place_id && onAddActivityFromPOI) {
      console.log('[DayItinerary] Using NEW POST API for place_id:', activity.place_id);
      try {
        setSaving(true);
        await onAddActivityFromPOI(dayNumber, activity.place_id, activity.description || activity.note);
        // Plan will be updated by parent component
        console.log('[DayItinerary] Successfully added activity via POST API');
        setSaving(false);
      } catch (error) {
        console.error('[DayItinerary] Failed to add activity from POI:', error);
        alert('Không thể thêm hoạt động. Vui lòng thử lại.');
        setSaving(false);
      }
    } else {
      // Fallback to old method for manually entered activities
      console.log('[DayItinerary] Using OLD PATCH method. Reason:', !activity.place_id ? 'No place_id' : 'No callback');
      const nextItems = [...items, activity];
      handlePersist(nextItems, { sendTimes: false });
    }
  };

  const isAccommodationCategory = (category) => {
    if (!category) return false;
    const catStr = Array.isArray(category) ? category.join(' ').toLowerCase() : String(category).toLowerCase();
    return catStr.includes('hotel') || catStr.includes('accommodation');
  };

  return (
    <div className="p-6">
    {/* Day Notes - Editable for owner */}
    <div className="px-6">
        <div className="border-b border-gray-100 dark:border-gray-700 pb-6">
            {isPublicView ? (
            // Public view - static display
            day.notes && (
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">
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
        <p className="text-gray-500 dark:text-gray-400 text-center py-4">Chưa có hoạt động cho ngày này</p>
      ) : (
        <DndContext
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
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

          <DragOverlay dropAnimation={null}>
            {activeId ? (
              (() => {
                const active = estimatedItems.find((it) => it.id === activeId);
                if (!active) return null;
                const { item, time } = active;
                return (
                  <div className="w-full shadow-lg rounded-lg bg-white dark:bg-gray-700 p-3 pointer-events-none" style={{ transform: 'none' }}>
                    <div className="flex items-start gap-3">
                      <div className="mt-1 cursor-grabbing text-gray-600 dark:text-gray-400">
                        <GripVertical className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold rounded-full bg-brand-primary text-white">•</span>
                          <span className="font-semibold text-gray-900 dark:text-white">{item.poi_name || item.name || item.activity}</span>
                          {time && <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 px-2 py-0.5 rounded-full">{time}</span>}
                        </div>
                        {item.description && <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">{item.description}</p>}
                      </div>
                    </div>
                  </div>
                );
              })()
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

    <div className="flex items-center justify-between mt-3">
        <div className="text-sm text-gray-500 dark:text-gray-400">
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
