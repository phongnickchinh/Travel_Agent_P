import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import Login from '../../pages/user/Login';
import Register from '../../pages/user/Register';
import ResetPassword from '../../pages/user/ResetPassword';

const modalContent = {
  login: Login,
  register: Register,
  reset: ResetPassword,
};

export default function AuthModal({ open, mode = 'login', onClose }) {
  if (!open) return null;

  const Content = modalContent[mode] || Login;

  return (
    <AnimatePresence>
      <motion.div
        key="auth-modal-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
        role="dialog"
        aria-modal="true"
      >
        <motion.div
          key="auth-modal-card"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          className="relative w-full max-w-xl"
        >
          <button
            aria-label="Close authentication dialog"
            onClick={onClose}
            className="absolute right-3 top-3 rounded-full bg-white/80 p-2 text-gray-700 shadow hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black"
          >
            <X className="h-5 w-5" />
          </button>
          <Content isModal />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
