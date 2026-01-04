import { AnimatePresence, motion } from 'framer-motion';
import { Camera, Clock, Globe, Loader2, Mail, User, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import userAPI from '../../services/userApi';

/**
 * ProfileSettingsModal - Modal popup for editing user profile
 * 
 * @param {boolean} isOpen - Whether modal is visible
 * @param {Function} onClose - Callback to close modal
 */
export default function ProfileSettingsModal({ isOpen, onClose }) {
  const { user, refreshUser } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    name: '',
    language: 'en',
    timezone: 'Asia/Ho_Chi_Minh'
  });
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  // Load user data when modal opens
  useEffect(() => {
    if (isOpen && user) {
      setFormData({
        username: user.username || '',
        name: user.name || '',
        language: user.language || 'en',
        timezone: user.timezone || 'Asia/Ho_Chi_Minh'
      });
      setAvatarPreview(user.avatar_url || user.profile_picture || null);
      setAvatarFile(null);
      setError('');
      setSuccess((prev) => (prev ? prev : ''));
    }
  }, [isOpen, user]);

  // Keep success message visible for at least 1s before clearing
  useEffect(() => {
    if (!success) return undefined;
    const timer = setTimeout(() => {
      setSuccess('');
    }, 1000);
    return () => clearTimeout(timer);
  }, [success]);

  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
    setSuccess('');
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) {
        setError('Image size must be less than 5MB');
        return;
      }

      setAvatarFile(file);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result);
      };
      reader.readAsDataURL(file);
      
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Prepare profile update data (text fields)
      const updateData = {};
      if (formData.username !== user?.username) updateData.username = formData.username;
      if (formData.name !== user?.name) updateData.name = formData.name;
      if (formData.language !== user?.language) updateData.language = formData.language;
      if (formData.timezone !== user?.timezone) updateData.timezone = formData.timezone;

      if (Object.keys(updateData).length === 0 && !avatarFile) {
        setError('No changes to save');
        setLoading(false);
        return;
      }

      // Update profile text fields first (if any)
      if (Object.keys(updateData).length > 0) {
        const profileResult = await userAPI.updateProfile(updateData);
        
        if (!profileResult.success) {
          setError(profileResult.errorVi || profileResult.error || 'Failed to update profile');
          setLoading(false);
          return;
        }
      }

      // Upload avatar separately (if provided)
      if (avatarFile) {
        const avatarResult = await userAPI.uploadAvatar(avatarFile);
        
        if (!avatarResult.success) {
          setError(avatarResult.errorVi || avatarResult.error || 'Failed to upload avatar');
          setLoading(false);
          return;
        }
      }

      // Refresh user context before showing success
      const refreshed = await refreshUser();
      if (!refreshed?.success) {
        setError(refreshed?.error || 'Failed to refresh user data');
        setLoading(false);
        return;
      }

      // Success
      setSuccess('Profile updated successfully!');
      setAvatarFile(null);
    } catch (err) {
      console.error('Profile update error:', err);
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleBackdropClick}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-white dark:bg-gray-800 rounded-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors z-10"
              aria-label="Close"
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>

            <div className="p-6 sm:p-8">
              <h2 className="font-poppins font-bold text-2xl text-gray-900 dark:text-white mb-6">
                Profile Settings
              </h2>

              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Avatar Upload */}
                <div className="flex flex-col items-center mb-6">
                  <div className="relative">
                    <motion.div
                      whileHover={{ scale: 1.05 }}
                      className="relative w-28 h-28 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700 cursor-pointer"
                      onClick={handleAvatarClick}
                    >
                      {avatarPreview ? (
                        <img
                          src={avatarPreview}
                          alt="Avatar"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <User className="w-14 h-14 text-gray-400 dark:text-gray-500" />
                        </div>
                      )}
                      
                      <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                        <Camera className="w-7 h-7 text-white" />
                      </div>
                    </motion.div>
                    
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleAvatarChange}
                      className="hidden"
                    />
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Click to change avatar
                  </p>
                </div>

                {/* Email (Read-only) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    <Mail className="inline w-4 h-4 mr-1.5" />
                    Email
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 cursor-not-allowed text-sm"
                  />
                </div>

                {/* Username */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    <User className="inline w-4 h-4 mr-1.5" />
                    Username
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Enter username"
                    className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white text-sm"
                    required
                    minLength={3}
                  />
                </div>

                {/* Full Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter full name"
                    className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white text-sm"
                    required
                  />
                </div>

                {/* Language & Timezone Row */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      <Globe className="inline w-4 h-4 mr-1.5" />
                      Language
                    </label>
                    <select
                      name="language"
                      value={formData.language}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white text-sm"
                    >
                      <option value="en">English</option>
                      <option value="vi">Tiếng Việt</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      <Clock className="inline w-4 h-4 mr-1.5" />
                      Timezone
                    </label>
                    <select
                      name="timezone"
                      value={formData.timezone}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white text-sm"
                    >
                      <option value="Asia/Ho_Chi_Minh">Vietnam (GMT+7)</option>
                      <option value="Asia/Bangkok">Bangkok (GMT+7)</option>
                      <option value="Asia/Singapore">Singapore (GMT+8)</option>
                      <option value="Asia/Tokyo">Tokyo (GMT+9)</option>
                    </select>
                  </div>
                </div>

                {/* Error/Success Messages */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm"
                  >
                    {error}
                  </motion.div>
                )}

                {success && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-600 dark:text-green-400 text-sm"
                  >
                    {success}
                  </motion.div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    type="submit"
                    disabled={loading}
                    className="flex-1 px-4 py-2.5 bg-brand-primary dark:bg-brand-secondary text-white rounded-lg font-semibold shadow-lg hover:shadow-xl transition-shadow disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      'Save Changes'
                    )}
                  </motion.button>
                </div>
              </form>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
