import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, LogOut, Menu, Plus, Settings, User } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

/**
 * DashboardHeader Component
 * 
 * Top navigation bar with New Plan button and user info
 */
export default function DashboardHeader({ onNewPlan, onMenuToggle }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showMenu, setShowMenu] = useState(false);

  // Get user avatar - prefer profile_picture (Google), fallback to avatar_url
  const avatarUrl = user?.profile_picture || user?.avatar_url;
  // Get user display name - prefer name, fallback to display_name or email
  const displayName = user?.name || user?.display_name || user?.email?.split('@')[0] || 'User';

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const menuItems = [
    { label: 'Chỉnh sửa hồ sơ', icon: User, action: () => navigate('/dashboard/profile') },
    { label: 'Đổi mật khẩu', icon: Settings, action: () => navigate('/dashboard/change-password') },
    { label: 'Đăng xuất', icon: LogOut, action: handleLogout, danger: true },
  ];

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
      <div className="flex items-center justify-between px-8 py-4">
        {/* Mobile Menu Toggle */}
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
          aria-label="Toggle menu"
        >
          <Menu className="w-6 h-6 text-gray-700" />
        </button>

        {/* Spacer for alignment */}
        <div className="flex-1" />

        {/* New Plan Button */}
        <motion.button
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.97 }}
          onClick={onNewPlan}
          className="flex items-center gap-2 px-6 py-2.5 bg-white border-2 border-gray-900 text-gray-900 rounded-full font-semibold hover:bg-[#2E571C] hover:border-[#2E571C] hover:text-white transition-all mr-6"
        >
          <Plus className="w-5 h-5" />
          <span>New Plan</span>
        </motion.button>

        {/* User Info with Dropdown */}
        <div
          className="relative"
          onMouseEnter={() => setShowMenu(true)}
          onMouseLeave={() => setShowMenu(false)}
        >
          <div className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition">
            {/* User Avatar */}
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={displayName}
                className="w-10 h-10 rounded-full object-cover border-2 border-gray-200"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-10 h-10 bg-gradient-to-br from-[#2E571C] to-[#4a8c2e] rounded-full flex items-center justify-center text-white font-semibold">
                {displayName[0]?.toUpperCase() || 'U'}
              </div>
            )}

            {/* Username */}
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-900">
                {displayName}
              </p>
            </div>

            {/* Dropdown Icon */}
            <motion.div
              animate={{ rotate: showMenu ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="hidden md:block"
            >
              <ChevronDown className="w-4 h-4 text-gray-600" />
            </motion.div>
          </div>

          {/* Dropdown Menu */}
          <AnimatePresence>
            {showMenu && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 w-56 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden py-2"
              >
                {/* User Info Header */}
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                </div>

                {/* Menu Items */}
                {menuItems.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setShowMenu(false);
                      item.action();
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition ${
                      item.danger
                        ? 'text-red-600 hover:bg-red-50'
                        : 'text-gray-700 hover:bg-[#2E571C]/10 hover:text-[#2E571C]'
                    }`}
                  >
                    <item.icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
