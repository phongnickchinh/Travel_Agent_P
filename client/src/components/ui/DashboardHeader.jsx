import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, LogOut, Menu, Plus, Search, Settings, User, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

/**
 * DashboardHeader Component
 * 
 * Top navigation bar with search, New Plan button and user info
 * 
 * @param {Function} onNewPlan - Callback to open create plan modal
 * @param {Function} onMenuToggle - Callback to toggle mobile sidebar
 * @param {Function} onOpenProfile - Callback to open profile settings modal
 * @param {Function} onOpenPassword - Callback to open change password modal
 * @param {Function} onSearch - Callback when search query changes (debounced)
 * @param {string} searchQuery - Current search query
 */
export default function DashboardHeader({ 
  onNewPlan, 
  onMenuToggle, 
  onOpenProfile, 
  onOpenPassword,
  onSearch,
  searchQuery = ''
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showMenu, setShowMenu] = useState(false);
  const [localSearch, setLocalSearch] = useState(searchQuery);
  const searchInputRef = useRef(null);
  const debounceRef = useRef(null);

  // Sync with external searchQuery prop
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  // Debounced search
  const handleSearchChange = (e) => {
    const value = e.target.value;
    setLocalSearch(value);
    
    // Debounce 300ms
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      onSearch?.(value);
    }, 300);
  };

  const clearSearch = () => {
    setLocalSearch('');
    onSearch?.('');
    searchInputRef.current?.focus();
  };

  // Get user avatar - prefer profile_picture (Google), fallback to avatar_url
  const avatarUrl = user?.avatar_url || user?.profile_picture;
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
    { label: 'Chỉnh sửa hồ sơ', icon: User, action: () => onOpenProfile?.() },
    { label: 'Đổi mật khẩu', icon: Settings, action: () => onOpenPassword?.() },
    { label: 'Đăng xuất', icon: LogOut, action: handleLogout, danger: true },
  ];

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-20">
      <div className="flex items-center justify-between px-8 py-4">
        {/* Mobile Menu Toggle */}
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          aria-label="Toggle menu"
        >
          <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        </button>

        {/* Search Bar */}
        <div className="flex-1 max-w-md mx-4 lg:mx-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={localSearch}
              onChange={handleSearchChange}
              placeholder="Tìm kiếm kế hoạch..."
              className="w-full pl-10 pr-10 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary transition-all"
            />
            {localSearch && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                onClick={clearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition"
                aria-label="Clear search"
              >
                <X className="w-4 h-4 text-gray-500" />
              </motion.button>
            )}
          </div>
        </div>

        {/* New Plan Button */}
        <motion.button
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.97 }}
          onClick={onNewPlan}
          className="flex items-center gap-2 px-6 py-2.5 bg-white dark:bg-gray-800 border-2 border-gray-900 dark:border-gray-600 text-gray-900 dark:text-white rounded-full font-semibold hover:bg-brand-primary hover:border-brand-primary hover:text-white dark:hover:bg-brand-primary dark:hover:border-brand-primary transition-all mr-6"
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
          <div className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition">
            {/* User Avatar */}
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={displayName}
                className="w-10 h-10 rounded-full object-cover border-2 border-gray-200 dark:border-gray-700"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-10 h-10 bg-linear-to-br from-brand-primary to-brand-secondary rounded-full flex items-center justify-center text-white font-semibold">
                {displayName[0]?.toUpperCase() || 'U'}
              </div>
            )}

            {/* Username */}
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {displayName}
              </p>
            </div>

            {/* Dropdown Icon */}
            <motion.div
              animate={{ rotate: showMenu ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="hidden md:block"
            >
              <ChevronDown className="w-4 h-4 text-gray-600 dark:text-gray-400" />
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
                className="absolute right-0 top-full mt-1 w-56 bg-white dark:bg-gray-800 rounded-xl shadow-lg dark:shadow-gray-900/50 border border-gray-100 dark:border-gray-700 overflow-hidden py-2"
              >
                {/* User Info Header */}
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{displayName}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
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
                        ? 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-brand-primary/10 dark:hover:bg-brand-primary/20 hover:text-brand-primary dark:hover:text-brand-muted'
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
