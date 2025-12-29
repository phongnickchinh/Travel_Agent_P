import { AnimatePresence, motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardHeader from '../../components/ui/DashboardHeader';
import DashboardSidebar from '../../components/ui/DashboardSidebar';
import PlanCard from '../../components/ui/PlanCard';
import planAPI from '../../services/planApi';

/**
 * Dashboard Component
 * 
 * Main dashboard view with plan grid and pagination
 */
export default function Dashboard() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [recentPlans, setRecentPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const PLANS_PER_PAGE = 8;

  // Fetch plans
  const fetchPlans = async (pageNum = 1, append = false) => {
    try {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      const result = await planAPI.getPlans({
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
        console.error('Failed to fetch plans:', result.error);
      }
    } catch (error) {
      console.error('Error fetching plans:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Fetch recent plans (for sidebar)
  const fetchRecentPlans = async () => {
    try {
      const result = await planAPI.getPlans({
        page: 1,
        limit: 4,
      });

      if (result.success && result.data) {
        // Sort by created_at descending (most recent first)
        const sorted = (result.data.plans || []).sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        setRecentPlans(sorted);
      }
    } catch (error) {
      console.error('Error fetching recent plans:', error);
    }
  };

  // Initial load
  useEffect(() => {
    fetchPlans(1);
    fetchRecentPlans();
  }, []);

  // Load more handler
  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchPlans(nextPage, true);
  };

  // Delete plan handler (called after successful delete in PlanCard)
  const handlePlanDeleted = (planId) => {
    // Remove from list
    setPlans((prev) => prev.filter((p) => p.plan_id !== planId));
    setTotal((prev) => prev - 1);
    
    // Refresh recent plans
    fetchRecentPlans();
  };

  // Navigate to create plan
  const handleNewPlan = () => {
    navigate('/dashboard/create-plan');
  };

  // Navigate to plan detail
  const handlePlanClick = (planId) => {
    navigate(`/dashboard/plan/${planId}`);
  };

  return (
    <div className="flex h-screen w-full bg-gray-50">
      {/* Sidebar */}
      <DashboardSidebar
        recentPlans={recentPlans}
        onPlanClick={handlePlanClick}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        <DashboardHeader
          onNewPlan={handleNewPlan}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="h-full px-8 py-6">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="font-poppins font-bold text-3xl text-gray-900 mb-1 text-justify">
                Travel Plan List
              </h1>
              <p className="text-gray-500 text-sm text-justify">
                Your travel itineraries
              </p>
            </div>

            {/* Loading State */}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : plans.length === 0 ? (
              /* Empty State */
              <div className="text-center py-20">
                <p className="text-gray-500 text-lg mb-4">
                  Bạn chưa có kế hoạch nào
                </p>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleNewPlan}
                  className="px-8 py-3 bg-black text-white rounded-full font-semibold shadow-lg hover:shadow-xl transition-shadow"
                >
                  Tạo kế hoạch đầu tiên
                </motion.button>
              </div>
            ) : (
              <>  
                {/* Plans Grid - 3 columns for larger cards */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 mb-8"
                >
                  <AnimatePresence>
                    {plans.map((plan, index) => (
                      <motion.div
                        key={plan.plan_id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <PlanCard
                          plan={plan}
                          onDelete={handlePlanDeleted}
                        />
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>

                {/* Load More Button */}
                {hasMore && (
                  <div className="text-center py-8">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleLoadMore}
                      disabled={loadingMore}
                      className="px-8 py-3 bg-white border border-gray-300 text-gray-700 rounded-full font-medium shadow-sm hover:shadow-md transition-shadow disabled:opacity-50"
                    >
                      {loadingMore ? (
                        <span className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Loading...
                        </span>
                      ) : (
                        'Load more'
                      )}
                    </motion.button>
                    <p className="text-sm text-gray-500 mt-3">
                      Showing {plans.length} of {total}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
