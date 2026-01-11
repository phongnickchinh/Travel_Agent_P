import { AnimatePresence, motion } from 'framer-motion';
import { useEffect } from 'react';

/**
 * ConfirmModal - Accessible confirmation dialog with keyboard support.
 * Enter/Space confirm, Escape or backdrop closes.
 */
export default function ConfirmModal({
  open,
  title = 'Confirm action',
  message = 'Are you sure you want to proceed?',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  loading = false,
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm?.();
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel?.();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onConfirm, onCancel]);

  if (!open) return null;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="confirm-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm px-4"
        aria-modal="true"
        role="dialog"
        onClick={onCancel}
      >
        <motion.div
          key="confirm-card"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ type: 'spring', stiffness: 300, damping: 24 }}
          className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 shadow-2xl border border-gray-200 dark:border-gray-700 p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">{title}</h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{message}</p>

          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-100 transition-colors dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              disabled={loading}
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-70 dark:bg-red-700 dark:hover:bg-red-600"
            >
              {loading ? 'Deleting...' : confirmLabel}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
