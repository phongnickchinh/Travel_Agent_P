import { AnimatePresence, motion } from 'framer-motion';
import { useState } from 'react';

/**
 * Tooltip Component
 * 
 * Shows tooltip on hover (desktop) or long-press (mobile)
 * 
 * @param {ReactNode} children - Element to wrap with tooltip
 * @param {string} content - Tooltip text content
 * @param {string} position - Tooltip position: 'top' | 'bottom' | 'left' | 'right'
 * @param {number} delay - Delay before showing tooltip (ms)
 */
export default function Tooltip({ 
  children, 
  content, 
  position = 'bottom',
  delay = 300,
  className = ''
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [timeoutId, setTimeoutId] = useState(null);

  const showTooltip = () => {
    const id = setTimeout(() => setIsVisible(true), delay);
    setTimeoutId(id);
  };

  const hideTooltip = () => {
    if (timeoutId) clearTimeout(timeoutId);
    setIsVisible(false);
  };

  // Long press for mobile
  const handleTouchStart = () => {
    const id = setTimeout(() => setIsVisible(true), 500);
    setTimeoutId(id);
  };

  const handleTouchEnd = () => {
    if (timeoutId) clearTimeout(timeoutId);
    // Keep tooltip visible for 2 seconds after touch end
    setTimeout(() => setIsVisible(false), 2000);
  };

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  const arrowClasses = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 dark:border-t-gray-700 border-x-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 dark:border-b-gray-700 border-x-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 dark:border-l-gray-700 border-y-transparent border-r-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 dark:border-r-gray-700 border-y-transparent border-l-transparent',
  };

  return (
    <div 
      className={`relative inline-flex ${className}`}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {children}
      
      <AnimatePresence>
        {isVisible && content && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={`absolute z-50 ${positionClasses[position]} pointer-events-none`}
          >
            <div className="relative">
              <div className="px-2.5 py-1.5 bg-gray-800 dark:bg-gray-700 text-white text-xs font-medium rounded-lg whitespace-nowrap shadow-lg">
                {content}
              </div>
              {/* Arrow */}
              <div 
                className={`absolute w-0 h-0 border-4 ${arrowClasses[position]}`}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
