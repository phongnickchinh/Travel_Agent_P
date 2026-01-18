import { AnimatePresence, motion } from 'framer-motion';
import { Compass, Home, Settings, Trash2, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';

/**
 * DashboardSidebar Component
 * 
 * Navigation sidebar - desktop: always visible, mobile: slide-out drawer
 * 
 * @param {boolean} isOpen - Mobile drawer open state
 * @param {Function} onClose - Close mobile drawer
 */
export default function DashboardSidebar({ isOpen, onClose, recentPlans = [], onPlanClick }) {
  const menuItems = [
    { icon: Home, label: 'Home', path: '/dashboard' },
    // { icon: Compass, label: 'Explore', path: '/dashboard/explore' },
    { icon: Trash2, label: 'Trash can', path: '/dashboard/trash' },
    { icon: Settings, label: 'Setting', path: '/dashboard/settings' },
  ];

  const handleNavClick = () => {
    onClose?.();
  };

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="px-4 xl:px-6 py-6 xl:py-8 flex items-center justify-between">
        <h1 className="font-poppins font-bold text-xl xl:text-2xl text-brand-primary dark:text-brand-muted">
          Travel Agent P
        </h1>
        {/* Mobile close button */}
        <button
          onClick={onClose}
          className="lg:hidden p-2.5 min-h-11 min-w-11 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          aria-label="Close menu"
        >
          <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      {/* Navigation Section */}
      <nav className="flex-1 px-3 xl:px-4 flex flex-col overflow-y-auto">
        {/* Menu Items Group */}
        <div className="space-y-1 mb-6 xl:mb-8">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/dashboard'}
              onClick={handleNavClick}
              className={({ isActive }) =>
                `flex items-center gap-2.5 xl:gap-3 px-3 xl:px-4 py-2.5 xl:py-3 rounded-xl transition-all no-underline ${
                  isActive
                    ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white font-semibold'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </div>

        {/* Recent Plans Section */}
        <div className="mb-6 xl:mb-8">
          <h3 className="px-3 xl:px-4 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 xl:mb-3">
            Recent
          </h3>
          <div className="space-y-1">
            {recentPlans.length > 0 ? (
              recentPlans.slice(0, 4).map((plan) => (
                <motion.button
                  key={plan.plan_id}
                  whileHover={{ x: 4 }}
                  onClick={() => {
                    onPlanClick?.(plan.plan_id);
                    onClose?.();
                  }}
                  className="w-full text-left px-3 xl:px-4 py-2.5 xl:py-3 min-h-11 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-200 line-clamp-1">
                    {plan.num_days} ngày • {plan.destination}
                  </p>
                </motion.button>
              ))
            ) : (
              <p className="px-3 xl:px-4 py-1.5 xl:py-2 text-sm text-gray-400 dark:text-gray-500 italic">
                No recent plans
              </p>
            )}
          </div>
        </div>
      </nav>

      {/* Upgrade Section */}
      <div className="p-3 xl:p-4 mt-auto shrink-0">
        <div className="bg-linear-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl xl:rounded-2xl p-3 xl:p-4">
          <p className="text-xs xl:text-sm mb-2 xl:mb-3 text-gray-600 dark:text-gray-400">
            Upgrade to get more quota and create more plan trip
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full bg-white dark:bg-gray-900 border-2 border-gray-900 dark:border-gray-600 text-gray-900 dark:text-white font-semibold py-2 xl:py-2.5 rounded-xl hover:bg-gray-900 dark:hover:bg-brand-primary hover:border-gray-900 dark:hover:border-brand-primary hover:text-white transition-all text-sm xl:text-base"
          >
            Upgrade
          </motion.button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop Sidebar - Always visible on lg+ */}
      <aside className="hidden lg:flex w-56 xl:w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex-col h-screen shrink-0 overflow-hidden">
        <SidebarContent />
      </aside>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="lg:hidden fixed inset-0 bg-black/50 z-40"
            />
            {/* Drawer */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="lg:hidden fixed left-0 top-0 h-full w-72 bg-white dark:bg-gray-900 z-50 flex flex-col shadow-xl"
            >
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
