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
      className="fixed bottom-6 right-12 z-50 flex items-center rounded-full shadow-lg border bg-white/90 backdrop-blur dark:bg-gray-900/90 dark:border-gray-700 text-gray-700 dark:text-gray-100"
    >
      <div className="relative w-12 h-6 rounded-full bg-gray-200 dark:bg-gray-700 transition-colors">
        <motion.span
          layout
          className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow flex items-center justify-center"
          animate={{ x: isDark ? 22 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 22 }}
        >
          {isDark ? <Moon className="w-3.5 h-3.5 text-gray-700" /> : <Sun className="w-3.5 h-3.5 text-amber-500" />}
        </motion.span>
      </div>
    </motion.button>
  );
}
