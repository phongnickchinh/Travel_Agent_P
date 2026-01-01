import { motion } from 'framer-motion';
import { Compass, Home, Settings, Trash2 } from 'lucide-react';
import { NavLink } from 'react-router-dom';

/**
 * DashboardSidebar Component
 * 
 * Navigation sidebar with menu items and recent plans
 */
export default function DashboardSidebar({ recentPlans = [], onPlanClick }) {
  const menuItems = [
    { icon: Home, label: 'Home', path: '/dashboard' },
    { icon: Compass, label: 'Explore', path: '/dashboard/explore' },
    { icon: Trash2, label: 'Trash can', path: '/dashboard/trash' },
    { icon: Settings, label: 'Setting', path: '/dashboard/settings' },
  ];

  return (
    <aside className="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col h-screen shrink-0">
      {/* Logo */}
      <div className="px-6 py-8">
        <h1 className="font-poppins font-bold text-2xl text-brand-primary dark:text-brand-muted">
          Travel Agent P
        </h1>
      </div>

      {/* Navigation Section */}
      <nav className="flex-1 px-4 flex flex-col">
        {/* Menu Items Group */}
        <div className="space-y-1 mb-8">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/dashboard'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all no-underline ${
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
        <div className="mb-8">
          <h3 className="px-4 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">
            Recent
          </h3>
          <div className="space-y-1">
            {recentPlans.length > 0 ? (
              recentPlans.slice(0, 4).map((plan) => (
                <motion.button
                  key={plan.plan_id}
                  whileHover={{ x: 4 }}
                  onClick={() => onPlanClick?.(plan.plan_id)}
                  className="w-full text-left px-4 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-200 line-clamp-1">
                    {plan.num_days} ngày • {plan.destination}
                  </p>
                </motion.button>
              ))
            ) : (
              <p className="px-4 py-2 text-sm text-gray-400 dark:text-gray-500 italic">
                No recent plans
              </p>
            )}
          </div>
        </div>
      </nav>

      {/* Upgrade Section */}
      <div className="p-4 mt-auto">
        <div className="bg-linear-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl p-4">
          <p className="text-sm mb-3 text-gray-600 dark:text-gray-400">
            Upgrade to get more quota and create more plan trip
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full bg-white dark:bg-gray-900 border-2 border-gray-900 dark:border-gray-600 text-gray-900 dark:text-white font-semibold py-2.5 rounded-xl hover:bg-gray-900 dark:hover:bg-brand-primary hover:border-gray-900 dark:hover:border-brand-primary hover:text-white transition-all"
          >
            Upgrade
          </motion.button>
        </div>
      </div>
    </aside>
  );
}
