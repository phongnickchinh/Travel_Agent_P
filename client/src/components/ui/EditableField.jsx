/**
 * EditableField Component
 * 
 * Reusable inline edit component with click-to-edit behavior.
 * Follows Framer Motion + Tailwind design system.
 * 
 * Props:
 * - value: Current display value
 * - onSave: Async callback when saving (receives new value)
 * - type: 'text' | 'textarea' | 'date' (default: 'text')
 * - placeholder: Placeholder text when empty
 * - disabled: Disable editing
 * - className: Additional CSS classes for display mode
 * - inputClassName: Additional CSS classes for input
 * - renderDisplay: Custom render function for display mode
 * - maxLength: Max character limit
 * - rows: Number of rows for textarea (default: 3)
 */

import { AnimatePresence, motion } from 'framer-motion';
import { Calendar, Check, Lightbulb, Loader2, Pencil, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

export default function EditableField({
  value,
  onSave,
  type = 'text',
  placeholder = 'Click to edit...',
  disabled = false,
  className = '',
  inputClassName = '',
  renderDisplay,
  maxLength,
  rows = 3,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  // Sync local state when prop value changes
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value || '');
    }
  }, [value, isEditing]);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      // Move cursor to end for text inputs
      if (type !== 'date' && inputRef.current.setSelectionRange) {
        const len = editValue.length;
        inputRef.current.setSelectionRange(len, len);
      }
    }
  }, [isEditing, type]);

  // Enter edit mode
  const handleStartEdit = useCallback(() => {
    if (disabled || isSaving) return;
    setEditValue(value || '');
    setError(null);
    setIsEditing(true);
  }, [disabled, isSaving, value]);

  // Cancel editing
  const handleCancel = useCallback(() => {
    setEditValue(value || '');
    setError(null);
    setIsEditing(false);
  }, [value]);

  // Save changes
  const handleSave = useCallback(async () => {
    // No change, just close
    if (editValue === (value || '')) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await onSave(editValue);
      setIsEditing(false);
    } catch (err) {
      console.error('[EditableField] Save error:', err);
      setError(err.message || 'Error saving');
    } finally {
      setIsSaving(false);
    }
  }, [editValue, value, onSave]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    } else if (e.key === 'Enter' && type !== 'textarea') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Enter' && e.ctrlKey && type === 'textarea') {
      e.preventDefault();
      handleSave();
    }
  }, [type, handleCancel, handleSave]);

  // Render the input based on type
  const renderInput = () => {
    const baseInputClass = `
      w-full px-3 py-2 
      border border-gray-300 dark:border-gray-600 rounded-lg
      focus:ring-2 focus:ring-brand-primary focus:border-brand-primary
      outline-none transition-all
      bg-white dark:bg-gray-800
      text-gray-900 dark:text-white text-sm
      ${inputClassName}
      ${error ? 'border-red-400 focus:ring-red-400' : ''}
    `;

    switch (type) {
      case 'textarea':
        return (
          <textarea
            ref={inputRef}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            rows={rows}
            disabled={isSaving}
            className={`${baseInputClass} resize-none`}
          />
        );

      case 'date':
        return (
          <input
            ref={inputRef}
            type="date"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSaving}
            className={baseInputClass}
          />
        );

      default: // text
        return (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            disabled={isSaving}
            className={baseInputClass}
          />
        );
    }
  };

  // Display mode content
  const displayContent = renderDisplay 
    ? renderDisplay(value) 
    : value || <span className="text-gray-400 italic">{placeholder}</span>;

  return (
    <div className="relative group">
      <AnimatePresence mode="wait">
        {isEditing ? (
          // Edit Mode
          <motion.div
            key="edit"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="space-y-2"
          >
            {renderInput()}
            
            {/* Error message */}
            {error && (
              <p className="text-xs text-red-500">{error}</p>
            )}

            {/* Character count for textarea */}
            {type === 'textarea' && maxLength && (
              <p className="text-xs text-gray-400 text-right">
                {editValue.length}/{maxLength}
              </p>
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1 px-3 py-1.5 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-brand-dark transition-colors disabled:opacity-50"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="w-3 h-3" />
                    Save
                  </>
                )}
              </motion.button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleCancel}
                disabled={isSaving}
                className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                <X className="w-3 h-3" />
                Cancel
              </motion.button>

              {/* Hint */}
              <span className="text-xs text-gray-400 ml-2">
                {type === 'textarea' ? 'Ctrl+Enter to save' : 'Enter to save, Esc to cancel'}
              </span>
            </div>
          </motion.div>
        ) : (
          // Display Mode
          <motion.div
            key="display"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={handleStartEdit}
            className={`
              relative cursor-pointer
              rounded-lg transition-all duration-200
              ${!disabled && 'hover:bg-gray-50 dark:hover:bg-gray-700/50 group-hover:pr-8'}
              ${className}
            `}
          >
            {displayContent}
            
            {/* Edit icon on hover */}
            {!disabled && (
              <motion.span
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 0 }}
                className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Pencil className="w-4 h-4 text-gray-400" />
              </motion.span>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * EditableTitle - Pre-styled variant for headings
 */
export function EditableTitle({ value, onSave, disabled, level = 'h1' }) {
  const sizeClasses = {
    h1: 'text-xl font-bold',
    h2: 'text-lg font-bold',
    h3: 'text-base font-semibold',
  };

  return (
    <EditableField
      value={value}
      onSave={onSave}
      disabled={disabled}
      placeholder="Enter title..."
      className={`${sizeClasses[level]} text-gray-900 dark:text-white py-1 px-2 -mx-2`}
      inputClassName={sizeClasses[level]}
    />
  );
}

/**
 * EditableNotes - Pre-styled variant for notes/descriptions
 */
export function EditableNotes({ value, onSave, disabled, maxLength = 500 }) {
  return (
    <EditableField
      value={value}
      onSave={onSave}
      type="textarea"
      disabled={disabled}
      placeholder="Add notes..."
      maxLength={maxLength}
      rows={3}
      className="text-sm text-gray-500 dark:text-gray-400 italic py-1 px-2 -mx-2"
      renderDisplay={(val) => val ? (
        <span className="flex items-center gap-1"><Lightbulb className="w-4 h-4" /> {val}</span>
      ) : (
        <span className="text-gray-400 dark:text-gray-500 italic">+ Add notes...</span>
      )}
    />
  );
}

/**
 * EditableDate - Pre-styled variant for date fields
 * @param {string} variant - 'light' (default) or 'dark' (for dark backgrounds)
 */
export function EditableDate({ value, onSave, disabled, variant = 'light' }) {
  // Format date for display (DD/MM/YYYY)
  const formatDisplayDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const isDark = variant === 'dark';

  return (
    <EditableField
      value={value}
      onSave={onSave}
      type="date"
      disabled={disabled}
      className={`text-sm py-1 px-2 -mx-2 ${isDark ? 'text-white' : 'text-gray-600'}`}
      renderDisplay={(val) => (
        <span className="flex items-center gap-1 cursor-pointer hover:underline">
          <Calendar className="w-4 h-4" /> {formatDisplayDate(val) || 'Chọn ngày...'}
        </span>
      )}
    />
  );
}
