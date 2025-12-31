import { motion } from 'framer-motion';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * ThemeToggle - Floating switch for light/dark modes
 */
export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <motion.button
      aria-label={isDark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
      onClick={toggleTheme}
      whileHover={{ scale: 1.03, y: -2 }}
      whileTap={{ scale: 0.97 }}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2 rounded-full shadow-lg border bg-white/90 backdrop-blur dark:bg-gray-900/90 dark:border-gray-700 text-gray-700 dark:text-gray-100"
    >
      <div className="relative w-10 h-5 rounded-full bg-gray-200 dark:bg-gray-700 transition-colors">
        <motion.span
          layout
          className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow"
          animate={{ x: isDark ? 20 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 22 }}
        />
      </div>
      {isDark ? (
        <span className="flex items-center gap-1 text-sm font-medium"><Moon className="w-4 h-4" /> Dark</span>
      ) : (
        <span className="flex items-center gap-1 text-sm font-medium"><Sun className="w-4 h-4" /> Light</span>
      )}
    </motion.button>
  );
}
