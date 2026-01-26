import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, LogOut, Menu, Moon, Plus, Search, Settings, Sun, User, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import searchAPI from '../../services/searchApi';

/**
 * DashboardHeader Component
 * 
 * Top navigation bar with New Plan button and user info
 * 
 * @param {Function} onNewPlan - Callback to open create plan modal
 * @param {Function} onMenuToggle - Callback to toggle mobile sidebar
 * @param {Function} onOpenProfile - Callback to open profile settings modal
 * @param {Function} onOpenPassword - Callback to open change password modal
 */
export default function DashboardHeader({ onNewPlan, onMenuToggle, onOpenProfile, onOpenPassword }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [showMenu, setShowMenu] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const searchRef = useRef(null);
  const mobileSearchRef = useRef(null);

  const avatarUrl = user?.avatar_url || user?.profile_picture;
  const displayName = user?.name || user?.display_name || user?.email?.split('@')[0] || 'User';

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSearchDropdown(false);
      }
      if (mobileSearchRef.current && !mobileSearchRef.current.contains(e.target)) {
        setShowMobileSearch(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = useCallback(async (query) => {
    setSearchQuery(query);
    setSelectedIndex(-1);
    if (query.trim().length < 2) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }
    setIsSearching(true);
    const result = await searchAPI.searchPlans(query);
    setIsSearching(false);
    if (result?.results) {
      setSearchResults(result.results);
      setShowSearchDropdown(true);
    } else {
      setSearchResults([]);
    }
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (!showSearchDropdown || searchResults.length === 0) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < searchResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : searchResults.length - 1));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleSelectPlan(searchResults[selectedIndex]);
    } else if (e.key === 'Escape') {
      setShowSearchDropdown(false);
      setSelectedIndex(-1);
    }
  }, [showSearchDropdown, searchResults, selectedIndex]);

  const handleSelectPlan = (plan) => {
    setShowSearchDropdown(false);
    setShowMobileSearch(false);
    setSearchQuery('');
    setSearchResults([]);
    setSelectedIndex(-1);
    navigate(`/dashboard/plan/${plan.plan_id}`);
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const menuItems = [
    { label: 'Edit Profile', icon: User, action: () => onOpenProfile?.() },
    { label: 'Change Password', icon: Settings, action: () => onOpenPassword?.() },
    { label: 'Logout', icon: LogOut, action: handleLogout, danger: true },
  ];

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-20">
      <div className="flex items-center justify-between px-4 lg:px-6 xl:px-8 py-3 lg:py-4">
        {/* Mobile Menu Toggle */}
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2.5 min-h-11 min-w-11 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          aria-label="Toggle menu"
        >
          <Menu className="w-6 h-6 text-gray-700 dark:text-gray-300" />
        </button>

        {/* Spacer for alignment */}
        <div className="flex-1" />

        {/* Desktop Search Bar */}
        <div ref={searchRef} className="hidden md:block relative mr-4 lg:mr-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => searchQuery.length >= 2 && setShowSearchDropdown(true)}
              placeholder="Search plans..."
              className="w-48 lg:w-64 xl:w-80 pl-9 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 border border-transparent focus:border-brand-primary focus:bg-white dark:focus:bg-gray-900 rounded-full outline-none transition-all text-gray-900 dark:text-white placeholder-gray-500"
            />
            {isSearching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }} className="w-4 h-4 border-2 border-gray-300 border-t-brand-primary rounded-full" />
              </div>
            )}
          </div>

          <AnimatePresence>
            {showSearchDropdown && searchResults.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="absolute top-full mt-2 w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden max-h-80 overflow-y-auto"
              >
                {searchResults.map((plan, index) => (
                  <motion.button
                    key={plan.plan_id}
                    whileHover={{ backgroundColor: 'rgba(46, 87, 28, 0.1)' }}
                    onClick={() => handleSelectPlan(plan)}
                    className={`w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-0 ${index === selectedIndex ? 'bg-brand-muted dark:bg-brand-primary/20' : ''}`}
                  >
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{plan.title}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{plan.destination}</p>
                  </motion.button>
                ))}
              </motion.div>
            )}
            {showSearchDropdown && searchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="absolute top-full mt-2 w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-4"
              >
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center">No plans found</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Mobile Search Icon */}
        <button
          onClick={() => setShowMobileSearch(true)}
          className="md:hidden p-2.5 min-h-11 min-w-11 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg mr-2"
          aria-label="Search plans"
        >
          <Search className="w-5 h-5 text-gray-700 dark:text-gray-300" />
        </button>

        {/* Mobile Search Modal */}
        <AnimatePresence>
          {showMobileSearch && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-50 md:hidden"
            >
              <motion.div
                ref={mobileSearchRef}
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                exit={{ y: -100 }}
                className="bg-white dark:bg-gray-900 p-4"
              >
                <div className="flex items-center gap-3">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Search plans..."
                      autoFocus
                      className="w-full pl-9 pr-4 py-2.5 text-sm bg-gray-100 dark:bg-gray-800 rounded-full outline-none text-gray-900 dark:text-white placeholder-gray-500"
                    />
                  </div>
                  <button onClick={() => { setShowMobileSearch(false); setSearchQuery(''); setSearchResults([]); setSelectedIndex(-1); }} className="p-2">
                    <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>
                {searchResults.length > 0 && (
                  <div className="mt-3 max-h-64 overflow-y-auto">
                    {searchResults.map((plan, index) => (
                      <button
                        key={plan.plan_id}
                        onClick={() => handleSelectPlan(plan)}
                        className={`w-full text-left px-3 py-3 border-b border-gray-100 dark:border-gray-800 ${index === selectedIndex ? 'bg-brand-muted dark:bg-brand-primary/20' : ''}`}
                      >
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{plan.title}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{plan.destination}</p>
                      </button>
                    ))}
                  </div>
                )}
                {searchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
                  <p className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">No plans found</p>
                )}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* New Plan Button */}
        <motion.button
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.97 }}
          onClick={onNewPlan}
          className="flex items-center gap-1.5 lg:gap-2 px-4 lg:px-5 xl:px-6 py-2 lg:py-2.5 bg-white dark:bg-gray-800 border-2 border-gray-900 dark:border-gray-600 text-gray-900 dark:text-white rounded-full font-semibold hover:bg-brand-primary hover:border-brand-primary hover:text-white dark:hover:bg-brand-primary dark:hover:border-brand-primary transition-all mr-4 lg:mr-6 text-sm lg:text-base"
        >
          <Plus className="w-5 h-5" />
          <span>New Plan</span>
        </motion.button>

        {/* User Info with Dropdown */}
        <div
          className="relative"
          onMouseEnter={() => {
            // Hover only for desktop (pointer: fine)
            if (window.matchMedia('(pointer: fine)').matches) {
              setShowMenu(true);
            }
          }}
          onMouseLeave={() => {
            if (window.matchMedia('(pointer: fine)').matches) {
              setShowMenu(false);
            }
          }}
        >
          <div 
            onClick={() => setShowMenu(!showMenu)}
            className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
          >
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

                {/* Menu Items (non-danger items) */}
                {menuItems.filter(item => !item.danger).map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setShowMenu(false);
                      item.action();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-brand-primary/10 dark:hover:bg-brand-primary/20 hover:text-brand-primary dark:hover:text-brand-muted transition"
                  >
                    <item.icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                ))}

                {/* Theme Toggle */}
                <button
                  onClick={() => {
                    toggleTheme();
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-brand-primary/10 dark:hover:bg-brand-primary/20 hover:text-brand-primary dark:hover:text-brand-muted transition"
                >
                  {theme === 'dark' ? (
                    <>
                      <Sun className="w-4 h-4" />
                      <span>Light Mode</span>
                    </>
                  ) : (
                    <>
                      <Moon className="w-4 h-4" />
                      <span>Dark Mode</span>
                    </>
                  )}
                </button>

                {/* Logout (danger items) */}
                <div className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1">
                  {menuItems.filter(item => item.danger).map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setShowMenu(false);
                        item.action();
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition"
                    >
                      <item.icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
