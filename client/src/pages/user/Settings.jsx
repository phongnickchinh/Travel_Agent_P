/**
 * Settings Page - Unified Settings View
 *
 * Features:
 * - Profile Settings (username, name, avatar)
 * - Password Change
 * - Theme Toggle (Light/Dark)
 * - Language Selection
 *
 * Author: Travel Agent P Team
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
    Camera,
    Check,
    Clock,
    Eye,
    EyeOff,
    Globe,
    Loader2,
    Lock,
    Mail,
    Moon,
    Palette,
    Sun,
    User,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import userAPI from '../../services/userApi';

// Tab definitions
const TABS = [
  { id: 'profile', label: 'Hồ sơ', icon: User },
  { id: 'password', label: 'Mật khẩu', icon: Lock },
  { id: 'appearance', label: 'Giao diện', icon: Palette },
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState('profile');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-inter font-bold text-3xl text-gray-900 dark:text-white mb-2">
            Cài đặt
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Quản lý thông tin cá nhân và tùy chỉnh ứng dụng
          </p>
        </motion.div>

        {/* Content */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Tab Navigation */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:w-64 shrink-0"
          >
            <nav className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-2 space-y-1">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <motion.button
                    key={tab.id}
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-left ${
                      isActive
                        ? 'bg-brand-primary text-white shadow-md'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </motion.button>
                );
              })}
            </nav>
          </motion.div>

          {/* Tab Content */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex-1"
          >
            <AnimatePresence mode="wait">
              {activeTab === 'profile' && <ProfileTab key="profile" />}
              {activeTab === 'password' && <PasswordTab key="password" />}
              {activeTab === 'appearance' && <AppearanceTab key="appearance" />}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/**
 * Profile Tab - Edit profile information
 */
function ProfileTab() {
  const { user, login } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    name: '',
    language: 'en',
    timezone: 'Asia/Ho_Chi_Minh',
  });
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  // Load user data on mount
  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username || '',
        name: user.name || '',
        language: user.language || 'en',
        timezone: user.timezone || 'Asia/Ho_Chi_Minh',
      });
      setAvatarPreview(user.profile_picture || user.avatar_url || null);
    }
  }, [user]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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
        setError('Vui lòng chọn file ảnh');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError('Kích thước ảnh tối đa 5MB');
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
      const updateData = {};
      if (formData.username !== user.username) updateData.username = formData.username;
      if (formData.name !== user.name) updateData.name = formData.name;
      if (formData.language !== user.language) updateData.language = formData.language;
      if (formData.timezone !== user.timezone) updateData.timezone = formData.timezone;

      if (Object.keys(updateData).length === 0 && !avatarFile) {
        setError('Không có thay đổi nào');
        setLoading(false);
        return;
      }

      const result = await userAPI.updateProfile(updateData, avatarFile);

      if (result.success) {
        setSuccess('Cập nhật thành công!');
        const profileResult = await userAPI.getProfile();
        if (profileResult.success) {
          const accessToken = localStorage.getItem('access_token');
          const refreshToken = localStorage.getItem('refresh_token');
          await login({
            email: profileResult.data.email,
            _skipAuth: true,
            _userData: profileResult.data,
            _accessToken: accessToken,
            _refreshToken: refreshToken,
          });
        }
        setAvatarFile(null);
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(result.error || 'Cập nhật thất bại');
      }
    } catch (err) {
      console.error('Profile update error:', err);
      setError('Đã xảy ra lỗi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 lg:p-8"
    >
      <h2 className="font-poppins font-bold text-xl text-gray-900 dark:text-white mb-6">
        Thông tin hồ sơ
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Avatar Upload */}
        <div className="flex flex-col items-center mb-6">
          <div className="relative">
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="relative w-28 h-28 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700 cursor-pointer"
              onClick={handleAvatarClick}
            >
              {avatarPreview ? (
                <img src={avatarPreview} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <User className="w-12 h-12 text-gray-400 dark:text-gray-500" />
                </div>
              )}
              <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                <Camera className="w-6 h-6 text-white" />
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
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Nhấn để thay đổi</p>
        </div>

        {/* Email (Read-only) */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <Mail className="w-4 h-4" />
            Email
          </label>
          <input
            type="email"
            value={user?.email || ''}
            disabled
            className="w-full px-4 py-2.5 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-gray-500 dark:text-gray-400 cursor-not-allowed"
          />
        </div>

        {/* Username */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <User className="w-4 h-4" />
            Tên người dùng
          </label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleInputChange}
            placeholder="Nhập tên người dùng"
            className="w-full px-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white transition"
          />
        </div>

        {/* Full Name */}
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
            Họ và tên
          </label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="Nhập họ và tên"
            className="w-full px-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white transition"
          />
        </div>

        {/* Language & Timezone Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Globe className="w-4 h-4" />
              Ngôn ngữ
            </label>
            <select
              name="language"
              value={formData.language}
              onChange={handleInputChange}
              className="w-full px-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white transition"
            >
              <option value="en">English</option>
              <option value="vi">Tiếng Việt</option>
            </select>
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Clock className="w-4 h-4" />
              Múi giờ
            </label>
            <select
              name="timezone"
              value={formData.timezone}
              onChange={handleInputChange}
              className="w-full px-4 py-2.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white transition"
            >
              <option value="Asia/Ho_Chi_Minh">Việt Nam (GMT+7)</option>
              <option value="Asia/Bangkok">Bangkok (GMT+7)</option>
              <option value="Asia/Singapore">Singapore (GMT+8)</option>
              <option value="Asia/Tokyo">Tokyo (GMT+9)</option>
              <option value="America/New_York">New York (GMT-5)</option>
              <option value="Europe/London">London (GMT+0)</option>
            </select>
          </div>
        </div>

        {/* Messages */}
        <AlertMessage type="error" message={error} />
        <AlertMessage type="success" message={success} />

        {/* Submit */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={loading}
          className="w-full px-6 py-3 bg-brand-primary dark:bg-brand-secondary text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Đang lưu...
            </>
          ) : (
            <>
              <Check className="w-5 h-5" />
              Lưu thay đổi
            </>
          )}
        </motion.button>
      </form>
    </motion.div>
  );
}

/**
 * Password Tab - Change password
 */
function PasswordTab() {
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
    setSuccess('');
  };

  const validateForm = () => {
    if (!formData.oldPassword || !formData.newPassword || !formData.confirmPassword) {
      setError('Vui lòng điền tất cả các trường');
      return false;
    }
    if (formData.newPassword.length < 6 || formData.newPassword.length > 20) {
      setError('Mật khẩu mới phải từ 6-20 ký tự');
      return false;
    }
    if (formData.newPassword !== formData.confirmPassword) {
      setError('Mật khẩu xác nhận không khớp');
      return false;
    }
    if (formData.oldPassword === formData.newPassword) {
      setError('Mật khẩu mới phải khác mật khẩu cũ');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await userAPI.changePassword(formData.oldPassword, formData.newPassword);

      if (result.success) {
        setSuccess(result.message || 'Đổi mật khẩu thành công!');
        setFormData({ oldPassword: '', newPassword: '', confirmPassword: '' });
        setTimeout(() => setSuccess(''), 5000);
      } else {
        setError(result.error || 'Đổi mật khẩu thất bại');
      }
    } catch (err) {
      console.error('Password change error:', err);
      setError('Đã xảy ra lỗi');
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrength = () => {
    const len = formData.newPassword.length;
    if (len >= 15) return { label: 'Mạnh', color: 'bg-green-500', bars: 3 };
    if (len >= 10) return { label: 'Tốt', color: 'bg-yellow-500', bars: 2 };
    if (len >= 6) return { label: 'Yếu', color: 'bg-red-500', bars: 1 };
    return { label: 'Quá ngắn', color: 'bg-gray-300', bars: 0 };
  };

  const strength = getPasswordStrength();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 lg:p-8"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 bg-brand-primary/10 dark:bg-brand-secondary/10 rounded-full flex items-center justify-center">
          <Lock className="w-6 h-6 text-brand-primary dark:text-brand-secondary" />
        </div>
        <div>
          <h2 className="font-poppins font-bold text-xl text-gray-900 dark:text-white">
            Đổi mật khẩu
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Cập nhật mật khẩu để bảo vệ tài khoản
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Old Password */}
        <PasswordField
          label="Mật khẩu hiện tại"
          name="oldPassword"
          value={formData.oldPassword}
          onChange={handleInputChange}
          show={showOldPassword}
          onToggle={() => setShowOldPassword(!showOldPassword)}
          placeholder="Nhập mật khẩu hiện tại"
        />

        {/* New Password */}
        <PasswordField
          label="Mật khẩu mới"
          name="newPassword"
          value={formData.newPassword}
          onChange={handleInputChange}
          show={showNewPassword}
          onToggle={() => setShowNewPassword(!showNewPassword)}
          placeholder="Nhập mật khẩu mới (6-20 ký tự)"
        />

        {/* Password Strength */}
        {formData.newPassword && (
          <div className="space-y-2">
            <div className="flex gap-2">
              {[1, 2, 3].map((bar) => (
                <div
                  key={bar}
                  className={`h-1.5 flex-1 rounded-full transition-colors ${
                    bar <= strength.bars ? strength.color : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">{strength.label}</p>
          </div>
        )}

        {/* Confirm Password */}
        <PasswordField
          label="Xác nhận mật khẩu mới"
          name="confirmPassword"
          value={formData.confirmPassword}
          onChange={handleInputChange}
          show={showConfirmPassword}
          onToggle={() => setShowConfirmPassword(!showConfirmPassword)}
          placeholder="Nhập lại mật khẩu mới"
        />

        {/* Messages */}
        <AlertMessage type="error" message={error} />
        <AlertMessage type="success" message={success} />

        {/* Submit */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={loading}
          className="w-full px-6 py-3 bg-brand-primary dark:bg-brand-secondary text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Đang đổi...
            </>
          ) : (
            <>
              <Lock className="w-5 h-5" />
              Đổi mật khẩu
            </>
          )}
        </motion.button>
      </form>
    </motion.div>
  );
}

/**
 * Appearance Tab - Theme and language settings
 */
function AppearanceTab() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 lg:p-8"
    >
      <h2 className="font-poppins font-bold text-xl text-gray-900 dark:text-white mb-6">
        Giao diện
      </h2>

      <div className="space-y-6">
        {/* Theme Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
          <div className="flex items-center gap-3">
            {isDark ? (
              <Moon className="w-6 h-6 text-brand-primary dark:text-brand-secondary" />
            ) : (
              <Sun className="w-6 h-6 text-amber-500" />
            )}
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Chế độ tối</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {isDark ? 'Đang bật chế độ tối' : 'Đang dùng chế độ sáng'}
              </p>
            </div>
          </div>

          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={toggleTheme}
            className={`relative w-14 h-7 rounded-full transition-colors ${
              isDark ? 'bg-brand-primary' : 'bg-gray-300'
            }`}
          >
            <motion.span
              layout
              className="absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white shadow flex items-center justify-center"
              animate={{ x: isDark ? 26 : 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 22 }}
            >
              {isDark ? (
                <Moon className="w-3.5 h-3.5 text-gray-700" />
              ) : (
                <Sun className="w-3.5 h-3.5 text-amber-500" />
              )}
            </motion.span>
          </motion.button>
        </div>

        {/* Theme Preview Cards */}
        <div className="grid grid-cols-2 gap-4">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => isDark && toggleTheme()}
            className={`p-4 rounded-xl border-2 transition ${
              !isDark
                ? 'border-brand-primary bg-white'
                : 'border-gray-300 dark:border-gray-600 bg-white'
            }`}
          >
            <div className="flex items-center gap-2 mb-3">
              <Sun className="w-5 h-5 text-amber-500" />
              <span className="font-medium text-gray-900">Sáng</span>
            </div>
            <div className="space-y-2">
              <div className="h-2 w-full bg-gray-200 rounded" />
              <div className="h-2 w-3/4 bg-gray-200 rounded" />
              <div className="h-2 w-1/2 bg-gray-200 rounded" />
            </div>
            <div className="mt-3 flex items-center justify-center gap-1 text-brand-primary text-sm font-medium dark:text-white">
            <Check className="w-4 h-4" /> Đang dùng
            </div>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => !isDark && toggleTheme()}
            className={`p-4 rounded-xl border-2 transition ${
              isDark
                ? 'border-brand-primary bg-gray-800'
                : 'border-gray-300 bg-gray-800'
            }`}
          >
            <div className="flex items-center gap-2 mb-3">
              <Moon className="w-5 h-5 text-brand-secondary" />
              <span className="font-medium text-white">Tối</span>
            </div>
            <div className="space-y-2">
              <div className="h-2 w-full bg-gray-600 rounded" />
              <div className="h-2 w-3/4 bg-gray-600 rounded" />
              <div className="h-2 w-1/2 bg-gray-600 rounded" />
            </div>
            <div className="mt-3 flex items-center justify-center gap-1 text-gray-800 dark:text-brand-secondary text-sm font-medium">
            <Check className="w-4 h-4" /> Đang dùng
            </div>
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Helper Components
 */
function PasswordField({ label, name, value, onChange, show, onToggle, placeholder }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {label}
      </label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          name={name}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 pr-12 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-brand-primary dark:focus:ring-brand-secondary focus:border-transparent text-gray-900 dark:text-white transition"
          required
          minLength={6}
          maxLength={20}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          {show ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
}

function AlertMessage({ type, message }) {
  if (!message) return null;

  const styles =
    type === 'error'
      ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400'
      : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-600 dark:text-green-400';

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 border rounded-xl text-sm ${styles}`}
    >
      {message}
    </motion.div>
  );
}
