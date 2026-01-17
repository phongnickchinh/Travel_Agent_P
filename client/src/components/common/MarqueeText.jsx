import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

/**
 * MarqueeText Component
 * 
 * Automatically scrolls text when it overflows container
 * Only animates when text is actually truncated
 * 
 * @param {string} text - Text content to display
 * @param {string} className - Additional CSS classes
 * @param {number} speed - Animation speed (pixels per second)
 * @param {number} pauseDuration - Pause at start/end (seconds)
 */
export default function MarqueeText({ 
  text, 
  className = '',
  speed = 30,
  pauseDuration = 2
}) {
  const containerRef = useRef(null);
  const textRef = useRef(null);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const [textWidth, setTextWidth] = useState(0);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const checkOverflow = () => {
      if (containerRef.current && textRef.current) {
        const container = containerRef.current.offsetWidth;
        const textEl = textRef.current.scrollWidth;
        setContainerWidth(container);
        setTextWidth(textEl);
        setShouldAnimate(textEl > container);
      }
    };

    checkOverflow();
    
    // Recheck on resize
    const resizeObserver = new ResizeObserver(checkOverflow);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [text]);

  const distance = textWidth - containerWidth;
  const duration = distance / speed;

  return (
    <div 
      ref={containerRef}
      className={`overflow-hidden relative group ${className}`}
      title={shouldAnimate ? text : undefined}
    >
      {shouldAnimate ? (
        <>
          <motion.span
            ref={textRef}
            className="inline-block whitespace-nowrap"
            initial={{ x: 0 }}
            animate={{ 
              x: [0, -distance, -distance, 0, 0],
            }}
            transition={{
              duration: duration + pauseDuration * 2,
              repeat: Infinity,
              ease: "linear",
              times: [0, duration / (duration + pauseDuration * 2), (duration + pauseDuration) / (duration + pauseDuration * 2), (duration + pauseDuration) / (duration + pauseDuration * 2) + 0.01, 1]
            }}
          >
            {text}
          </motion.span>
          {/* Tooltip on hover */}
          <div className="absolute left-0 bottom-full mb-2 px-3 py-1.5 bg-brand-primary text-white text-sm rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-9999 pointer-events-none">
            {text}
          </div>
        </>
      ) : (
        <span 
          ref={textRef}
          className="block truncate"
        >
          {text}
        </span>
      )}
    </div>
  );
}
