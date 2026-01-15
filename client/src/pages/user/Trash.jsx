import { AnimatePresence, motion } from 'framer-motion';
import { Calendar, FolderOpen, Loader2, MapPin, RotateCcw, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import ConfirmModal from '../../components/common/ConfirmModal';
import DashboardHeader from '../../components/layout/DashboardHeader';
import DashboardSidebar from '../../components/layout/DashboardSidebar';
import planAPI from '../../services/planApi';

/**
 * TrashPlanCard Component
 * 
 * Simplified card for trash view - no navigation to detail
 * Shows basic info and restore/permanent delete actions
 */
function TrashPlanCard({ plan, onRestore, onPermanentDelete }) {
  const [isRestoring, setIsRestoring] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const formatDeletedAt = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const handleRestore = async () => {
    if (isRestoring) return;
    setIsRestoring(true);
    try {
      const result = await planAPI.restorePlan(plan.plan_id);
      if (result.success) {
        onRestore?.(plan.plan_id);
      } else {
        alert('Unable to restore plan. Please try again.');
      }
    } catch (error) {
      console.error('Restore error:', error);
      alert('Error restoring plan.');
    } finally {
      setIsRestoring(false);
    }
  };

  const handlePermanentDelete = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      const result = await planAPI.permanentDeletePlan(plan.plan_id);
      if (result.success) {
        onPermanentDelete?.(plan.plan_id);
      } else {
        alert('Unable to permanently delete plan. Please try again.');
      }
    } catch (error) {
      console.error('Permanent delete error:', error);
      alert('Error permanently deleting plan.');
    } finally {
      setIsDeleting(false);
      setConfirmDeleteOpen(false);
    }
  };

  // Get first featured image or fallback
  const thumbnailUrl = plan.featured_images?.[0] || null;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="group relative bg-white dark:bg-gray-800 rounded-2xl shadow-md hover:shadow-lg dark:shadow-gray-900/30 overflow-hidden"
      >
        {/* Thumbnail Image */}
        <div className="relative aspect-[4/2.3] bg-gray-200 dark:bg-gray-700 overflow-hidden">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt={plan.destination}
              className="w-full h-full object-cover opacity-70 grayscale-30"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500">
              <MapPin className="w-16 h-16" />
            </div>
          )}
          
          {/* Deleted Badge */}
          <div className="absolute top-3 left-3">
            <span className="px-3 py-1 rounded-full text-xs font-medium text-white bg-red-500 dark:bg-red-600">
              Deleted
            </span>
          </div>

          {/* Deleted date */}
          <div className="absolute top-3 right-3">
            <span className="px-3 py-1 rounded-full text-xs font-medium text-gray-700 dark:text-gray-200 bg-white/90 dark:bg-gray-800/90">
              {formatDeletedAt(plan.deleted_at)}
            </span>
          </div>
        </div>

        {/* Card Content */}
        <div className="p-4">
          {/* Title */}
          <h3 className="font-poppins font-bold text-lg text-gray-900 dark:text-white mb-3 line-clamp-1">
            {plan.title || plan.destination}
          </h3>

          {/* Info Row */}
          <div className="space-y-2 mb-4">
            {/* Destination & Duration */}
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <MapPin className="w-4 h-4" />
              <span className="line-clamp-1">{plan.destination}</span>
              <span>•</span>
              <span>{plan.num_days} {plan.num_days === 1 ? 'day' : 'days'}</span>
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

          {/* Action Buttons */}
          <div className="flex gap-2">
            {/* Restore Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRestore}
              disabled={isRestoring || isDeleting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 min-h-11 bg-brand-primary dark:bg-brand-secondary text-white rounded-lg font-medium text-sm hover:bg-brand-dark dark:hover:bg-brand-primary transition disabled:opacity-60"
            >
              {isRestoring ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RotateCcw className="w-4 h-4" />
              )}
              Restore
            </motion.button>

            {/* Permanent Delete Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={isRestoring || isDeleting}
              className="flex items-center justify-center gap-2 px-4 py-2.5 min-h-11 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg font-medium text-sm hover:bg-red-100 dark:hover:bg-red-900/50 transition disabled:opacity-60"
            >
              <Trash2 className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Confirm Permanent Delete Modal */}
      <ConfirmModal
        open={confirmDeleteOpen}
        title="Delete Permanently?"
        message="This plan will be permanently deleted and cannot be recovered. Are you sure?"
        confirmLabel={isDeleting ? 'Deleting...' : 'Delete Permanently'}
        cancelLabel="Cancel"
        onConfirm={handlePermanentDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
        loading={isDeleting}
      />
    </>
  );
}

/**
 * Trash Component
 * 
 * Shows deleted plans with restore and permanent delete options
 * Plans in trash only show basic info (not full itinerary)
 */
export default function Trash() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const PLANS_PER_PAGE = 8;

  // Fetch trash plans
  const fetchTrashPlans = async (pageNum = 1, append = false) => {
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      const result = await planAPI.getTrashPlans({
        page: pageNum,
        limit: PLANS_PER_PAGE,
      });

      if (result.success && result.data) {
        const newPlans = result.data.plans || [];
        const totalPlans = result.data.total || 0;

        if (append) {
          setPlans((prev) => [...prev, ...newPlans]);
        } else {
          setPlans(newPlans);
        }

        setTotal(totalPlans);
        setHasMore(newPlans.length === PLANS_PER_PAGE);
      } else {
        console.error('Failed to fetch trash plans:', result.error);
      }
    } catch (error) {
      console.error('Error fetching trash plans:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchTrashPlans(1);
  }, []);

  // Load more handler
  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchTrashPlans(nextPage, true);
  };

  // Restore plan handler
  const handlePlanRestored = (planId) => {
    setPlans((prev) => prev.filter((p) => p.plan_id !== planId));
    setTotal((prev) => Math.max(0, prev - 1));
  };

  // Permanent delete handler
  const handlePlanDeleted = (planId) => {
    setPlans((prev) => prev.filter((p) => p.plan_id !== planId));
    setTotal((prev) => Math.max(0, prev - 1));
  };

  return (
    <div className="flex h-screen w-full bg-gray-50 dark:bg-black">
      {/* Sidebar */}
      <DashboardSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        <DashboardHeader onMenuToggle={() => setSidebarOpen(true)} />

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {/* Page Header */}
          <div className="mb-6 lg:mb-8">
            <div className="flex items-center gap-3 mb-2">
              <Trash2 className="w-8 h-8 text-gray-700 dark:text-gray-300" />
              <h1 className="font-poppins font-bold text-2xl md:text-3xl text-gray-900 dark:text-white">
                Trash
              </h1>
            </div>
            <p className="text-gray-500 dark:text-gray-400">
              Deleted plans are saved here. You can restore or permanently delete them.
            </p>
            {total > 0 && (
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                {total} {total === 1 ? 'plan' : 'plans'} in trash
              </p>
            )}
          </div>

          {/* Loading State */}
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              >
                <Loader2 className="w-10 h-10 text-brand-primary" />
              </motion.div>
            </div>
          ) : plans.length === 0 ? (
            /* Empty State */
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="w-24 h-24 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-6">
                <FolderOpen className="w-12 h-12 text-gray-400 dark:text-gray-500" />
              </div>
              <h2 className="font-poppins font-semibold text-xl text-gray-700 dark:text-gray-300 mb-2">
                Trash is Empty
              </h2>
              <p className="text-gray-500 dark:text-gray-400 max-w-sm">
                No plans in trash. When you delete a plan, it will appear here.
              </p>
            </motion.div>
          ) : (
            <>
              {/* Plans Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                <AnimatePresence mode="popLayout">
                  {plans.map((plan) => (
                    <TrashPlanCard
                      key={plan.plan_id}
                      plan={plan}
                      onRestore={handlePlanRestored}
                      onPermanentDelete={handlePlanDeleted}
                    />
                  ))}
                </AnimatePresence>
              </div>

              {/* Load More Button */}
              {hasMore && (
                <div className="flex justify-center mt-8">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full text-gray-700 dark:text-gray-200 font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition disabled:opacity-60"
                  >
                    {loadingMore ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </motion.button>
                </div>
              )}
            </>
          )}

          {/* Warning Note */}
          {plans.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-8 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 rounded-xl flex items-start gap-3 justify-center"
            >
              
              <div>
                <p className="text-amber-800 dark:text-amber-300 font-medium text-sm">
                  About Trash
                </p>
                <p className="text-amber-700 dark:text-amber-400/80 text-sm mt-1">
                  Plans in trash are kept until you permanently delete them. 
                  Permanently deleted plans cannot be recovered.
                </p>
              </div>
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
