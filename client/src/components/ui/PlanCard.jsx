import { motion } from 'framer-motion';
import { Calendar, ChevronRight, MapPin, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import planAPI from '../../services/planApi';
import { getCachedImage, preloadAndCacheImage } from '../../utils/imageCache';
import ConfirmModal from './ConfirmModal';

/**
 * PlanCard Component
 * 
 * Minimalist travel plan card with destination thumbnail
 * Displays plan title, destination, dates, and status
 */
export default function PlanCard({ plan, onDelete }) {
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cachedThumbnail, setCachedThumbnail] = useState(null);

  // Preload and cache thumbnail on mount
  useEffect(() => {
    if (plan.thumbnail_url) {
      // TEMP: Disable Google Photo API calls to prevent costs
      // Check if URL is likely a Google Photo URL
      if (plan.thumbnail_url.includes('google') || plan.thumbnail_url.startsWith('places/')) {
        const destName = typeof plan.destination === 'string' ? plan.destination : (plan.destination?.city || 'Plan');
        setCachedThumbnail(`https://placehold.co/600x400?text=${encodeURIComponent(destName)}`);
        return;
      }

      // Check if already cached
      const cached = getCachedImage(plan.thumbnail_url);
      if (cached) {
        setCachedThumbnail(cached);
      } else {
        // Preload and cache (TTL: 7 days for thumbnails)
        preloadAndCacheImage(plan.thumbnail_url, 'thumbnail')
          .then(() => setCachedThumbnail(plan.thumbnail_url))
          .catch(() => setCachedThumbnail(plan.thumbnail_url)); // Fallback to original URL
      }
    }
  }, [plan.thumbnail_url, plan.destination]);

  const handleClick = () => {
    navigate(`/dashboard/plan/${plan.plan_id}`);
  };

  const performDelete = () => {
    if (isDeleting) return;
    setIsDeleting(true);
    planAPI.deletePlan(plan.plan_id)
      .then((res) => {
        if (!res?.success) {
          throw new Error(res?.error || 'Delete failed');
        }
        onDelete?.(plan.plan_id);
      })
      .catch((err) => {
        console.error('Delete plan error:', err);
        window.alert('Không thể xoá kế hoạch, vui lòng thử lại.');
      })
      .finally(() => {
        setIsDeleting(false);
        setConfirmOpen(false);
      });
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    if (isDeleting) return;
    setConfirmOpen(true);
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Not set';
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
  };

  // Get status color
  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-gray-400',
      processing: 'bg-yellow-500',
      completed: 'bg-brand-primary',
      failed: 'bg-red-500'
    };
    return colors[status] || 'bg-gray-400';
  };

  return (
    <>
    <motion.div
      whileHover={{ y: -6 }}
      transition={{ duration: 0.2 }}
      className="group relative bg-white dark:bg-gray-800 rounded-2xl shadow-md hover:shadow-[0_20px_35px_-10px_rgba(46,87,28,0.45)] dark:hover:shadow-[0_20px_35px_-10px_rgba(46,87,28,0.25)] overflow-hidden cursor-pointer"
      onClick={handleClick}
    >
      {/* Thumbnail Image - Aspect ratio 4:3 horizontal rectangle */}
      <div className="relative aspect-[4/2.3] bg-gray-200 dark:bg-gray-700 overflow-hidden">
        {cachedThumbnail ? (
          <img
            src={cachedThumbnail}
            alt={plan.destination}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : plan.thumbnail_url ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-gray-300 border-t-brand-primary rounded-full animate-spin" />
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500">
            <MapPin className="w-16 h-16" />
          </div>
        )}
        
        {/* Delete Button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={handleDeleteClick}
          disabled={isDeleting}
          className="absolute top-3 right-3 p-2 bg-white/90 dark:bg-gray-800/90 hover:bg-red-50 dark:hover:bg-red-900/50 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-60 z-10"
          aria-label="Delete plan"
        >
          <Trash2 className="w-4 h-4 text-gray-700 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400" />
        </motion.button>

        {/* Status Badge */}
        <div className="absolute top-3 left-3">
          <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${getStatusColor(plan.status)}`}>
            {plan.status}
          </span>
        </div>

        {/* Gradient Overlay on Hover */}
        <div className="pointer-events-none absolute inset-0 bg-linear-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* Card Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="font-poppins font-bold text-lg text-gray-900 dark:text-white mb-3 line-clamp-1 text-justify">
          {plan.title || plan.destination}
        </h3>

        {/* Bottom Row: Info + Button */}
        <div className="flex items-center justify-between gap-3">
          {/* Destination & Dates */}
          <div className="flex-1 space-y-2">
            {/* Destination & Duration */}
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <MapPin className="w-4 h-4" />
              <span className="line-clamp-1">{plan.destination}</span>
              <span>•</span>
              <span>{plan.num_days} ngày</span>
            </div>

            {/* Dates */}
            {plan.start_date && (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-500">
                <Calendar className="w-4 h-4" />
                <span>
                  {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                </span>
              </div>
            )}
          </div>

          {/* View Button */}
          <motion.button
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.97 }}
            onClick={(e) => { e.stopPropagation(); handleClick(); }}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-brand-primary hover:border-brand-primary hover:text-white dark:hover:bg-brand-primary dark:hover:border-brand-primary transition font-bold text-lg self-center"
            aria-label="View plan"
          >
            <ChevronRight className="w-6 h-6" />
          </motion.button>
        </div>
      </div>
    </motion.div>
    <ConfirmModal
      open={confirmOpen}
      title="Chuyển và thùng rác"
      message="Bạn có muốn chuyển plan này vào thùng rác?"
      confirmLabel="Xoá"
      cancelLabel="Huỷ"
      onConfirm={performDelete}
      onCancel={() => !isDeleting && setConfirmOpen(false)}
      loading={isDeleting}
    />
    </>
  );
}
