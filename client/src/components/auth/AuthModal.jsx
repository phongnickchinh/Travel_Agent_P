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
        onClick={(e) => {
          // Close when clicking outside the modal content
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          key="auth-modal-card"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 24 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          className="relative w-full max-w-xl"
        >
          <Content isModal onClose={onClose} />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
