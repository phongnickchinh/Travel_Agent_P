import { motion } from 'framer-motion';
import { ArrowLeft, CheckCircle2, KeyRound, Loader2, Lock, Mail, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
    requestPasswordResetApi,
    resendResetCodeApi,
    resetPasswordApi,
    validateEmail,
    validatePassword,
    validateResetCodeApi
} from '../../services/authApi';

export default function ResetPassword({ isModal = false, onClose }) {
  const navigate = useNavigate();

  // Form state
  const [email, setEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // UI state
  const [currentStep, setCurrentStep] = useState(1); // 1: email, 2: verify, 3: new password, 4: success
  const [loading, setLoading] = useState(false);
  const [resetToken, setResetToken] = useState('');
  const [tempAccessToken, setTempAccessToken] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);
  const [resendTimer, setResendTimer] = useState(null);

  // Error state
  const [errors, setErrors] = useState({
    email: '',
    resetCode: '',
    newPassword: '',
    confirmPassword: ''
  });

  const [alert, setAlert] = useState({ message: '', type: '' });

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (resendTimer) {
        clearInterval(resendTimer);
      }
    };
  }, [resendTimer]);

  // Show alert
  const showAlert = (message, type = 'info') => {
    setAlert({ message, type });
    setTimeout(() => {
      setAlert({ message: '', type: '' });
    }, 5000);
  };

  // Clear errors
  const clearErrors = () => {
    setErrors({
      email: '',
      resetCode: '',
      newPassword: '',
      confirmPassword: ''
    });
  };

  // Step 1: Send verification code
  const handleSendCode = async (e) => {
    e.preventDefault();
    clearErrors();

    const emailError = validateEmail(email);
    if (emailError) {
      setErrors(prev => ({ ...prev, email: emailError }));
      return;
    }

    setLoading(true);

    try {
      // Use requestPasswordResetApi from authApi
      const data = await requestPasswordResetApi(email.trim());
      const responseData = data.data || data;
      
      setResetToken(responseData.resetToken);
      setCurrentStep(2);
      startResendTimer();
      showAlert('Verification code sent to your email!', 'success');

    } catch (error) {
      console.error('Send code error:', error);
      const errorMessage = error.response?.data?.resultMessage?.en || 
                           error.response?.data?.message || 
                           'An error occurred. Please try again.';
      showAlert(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify code
  const handleVerifyCode = async (e) => {
    e.preventDefault();
    clearErrors();

    if (!resetCode || resetCode.length !== 6) {
      setErrors(prev => ({ ...prev, resetCode: 'Please enter a valid 6-digit code' }));
      return;
    }

    setLoading(true);

    try {
      // Use validateResetCodeApi from authApi
      const data = await validateResetCodeApi(resetToken, resetCode);
      
      setTempAccessToken(data.tempAccessToken);
      setCurrentStep(3);
      showAlert('Code verified successfully!', 'success');

    } catch (error) {
      console.error('Verify code error:', error);
      const errorMessage = error.response?.data?.resultMessage?.en || 
                           error.response?.data?.message || 
                           'Invalid verification code';
      setErrors(prev => ({ ...prev, resetCode: errorMessage }));
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Reset password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    clearErrors();

    // Validate password using authApi function
    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setErrors(prev => ({ ...prev, newPassword: passwordError }));
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrors(prev => ({ ...prev, confirmPassword: 'Passwords do not match' }));
      return;
    }

    setLoading(true);

    try {
      // Use resetPasswordApi from authApi
      await resetPasswordApi(tempAccessToken, newPassword);
      
      setCurrentStep(4);

    } catch (error) {
      console.error('Reset password error:', error);
      const errorMessage = error.response?.data?.resultMessage?.en || 
                           error.response?.data?.message || 
                           'Failed to reset password';
      showAlert(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Resend code
  const handleResendCode = async () => {
    try {
      // Use resendResetCodeApi from authApi
      const data = await resendResetCodeApi(email);
      const responseData = data.data || data;
      
      setResetToken(responseData.resetToken);
      showAlert('New verification code sent!', 'success');
      startResendTimer();

    } catch (error) {
      console.error('Resend error:', error);
      const errorMessage = error.response?.data?.resultMessage?.en || 
                           error.response?.data?.message || 
                           'Failed to resend code';
      showAlert(errorMessage, 'error');
    }
  };

  // Start resend timer
  const startResendTimer = () => {
    setResendCountdown(60);

    const timer = setInterval(() => {
      setResendCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    setResendTimer(timer);
  };

  // Back to step 1
  const handleBackToStep1 = () => {
    setCurrentStep(1);
    setResetCode('');
    clearErrors();
    
    if (resendTimer) {
      clearInterval(resendTimer);
      setResendTimer(null);
      setResendCountdown(0);
    }
  };

  const cardClasses = `relative w-full ${isModal ? 'max-h-[90vh]' : 'min-h-[60vh]'} max-w-xl overflow-hidden rounded-3xl bg-white/90 dark:bg-gray-900/90 shadow-2xl ring-1 ring-black/5 backdrop-blur-md`;

  return (
    <div className={`${isModal ? 'w-full' : 'min-h-screen bg-gray-50 dark:bg-gray-950'} flex items-center justify-center px-4 py-10`}>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className={cardClasses}
      >
        {/* Header */}
        <div className="relative bg-linear-to-br from-brand-primary to-brand-secondary text-white px-6 py-6">
          {/* Close button inside header */}
          {isModal && onClose && (
            <button
              onClick={onClose}
              aria-label="Đóng"
              className="absolute right-4 top-4 p-1.5 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white/50"
            >
              <X className="h-5 w-5" />
            </button>
          )}
          <div className="flex items-center justify-center">
            <div className="justify-center text-center">
              <div className="mx-auto mb-2 w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                <KeyRound className="h-6 w-6" />
              </div>
              <h1 className="font-poppins font-semibold text-2xl mt-1">Đặt lại mật khẩu</h1>
              <p className="text-sm text-white/80">Khôi phục tài khoản của bạn</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6 space-y-5 overflow-y-auto">
          {alert.message && (
            <div
              className={`rounded-xl border px-4 py-3 text-sm ${
                alert.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800'
                  : alert.type === 'error'
                  ? 'border-red-200 bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800'
                  : 'border-blue-200 bg-blue-50 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800'
              }`}
            >
              {alert.message}
            </div>
          )}

          {/* Step 1: Enter Email */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                Nhập địa chỉ email của bạn và chúng tôi sẽ gửi mã xác minh để đặt lại mật khẩu.
              </p>

              <form onSubmit={handleSendCode} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setErrors(prev => ({ ...prev, email: '' }));
                      }}
                      placeholder="Nhập email"
                      required
                      className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                    />
                  </div>
                  {errors.email && <p className="text-xs text-red-500">{errors.email}</p>}
                </div>

                <motion.button
                  whileHover={{ scale: 1.01, y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={loading}
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                  <span>{loading ? 'Đang gửi...' : 'Gửi mã xác minh'}</span>
                </motion.button>

                <Link
                  to="/login"
                  className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-brand-primary transition"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Quay lại đăng nhập
                </Link>
              </form>
            </div>
          )}

          {/* Step 2: Verify Code */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                Chúng tôi đã gửi mã xác minh 6 chữ số đến<br />
                <strong className="text-gray-800 dark:text-gray-200">{email}</strong>
              </p>

              <form onSubmit={handleVerifyCode} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Mã xác minh</label>
                  <input
                    type="text"
                    value={resetCode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').substring(0, 6);
                      setResetCode(value);
                      setErrors(prev => ({ ...prev, resetCode: '' }));
                    }}
                    placeholder="Nhập mã 6 chữ số"
                    maxLength="6"
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-4 py-3 text-center text-lg tracking-widest font-mono text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                  {errors.resetCode && <p className="text-xs text-red-500 text-center">{errors.resetCode}</p>}
                </div>

                <motion.button
                  whileHover={{ scale: 1.01, y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={loading}
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                  <span>{loading ? 'Đang xác minh...' : 'Xác minh mã'}</span>
                </motion.button>

                <div className="text-center space-y-2">
                  <p className="text-sm text-gray-500 dark:text-gray-400">Chưa nhận được mã?</p>
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={resendCountdown > 0}
                    className="text-sm font-semibold text-brand-primary hover:text-brand-secondary disabled:text-gray-400 disabled:cursor-not-allowed transition"
                  >
                    {resendCountdown > 0 ? `Gửi lại sau ${resendCountdown}s` : 'Gửi lại mã'}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleBackToStep1}
                  className="flex items-center justify-center gap-2 w-full text-sm text-gray-600 dark:text-gray-400 hover:text-brand-primary transition"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Thay đổi email
                </button>
              </form>
            </div>
          )}

          {/* Step 3: New Password */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                Tạo mật khẩu mới cho tài khoản của bạn.
              </p>

              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Mật khẩu mới</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => {
                        setNewPassword(e.target.value);
                        setErrors(prev => ({ ...prev, newPassword: '' }));
                      }}
                      placeholder="Nhập mật khẩu mới"
                      required
                      className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                    />
                  </div>
                  {errors.newPassword && <p className="text-xs text-red-500">{errors.newPassword}</p>}
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Mật khẩu phải từ 6-20 ký tự, bao gồm chữ và số
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Xác nhận mật khẩu</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        setErrors(prev => ({ ...prev, confirmPassword: '' }));
                      }}
                      placeholder="Nhập lại mật khẩu"
                      required
                      className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                    />
                  </div>
                  {errors.confirmPassword && <p className="text-xs text-red-500">{errors.confirmPassword}</p>}
                </div>

                <motion.button
                  whileHover={{ scale: 1.01, y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={loading}
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                  <span>{loading ? 'Đang đặt lại...' : 'Đặt lại mật khẩu'}</span>
                </motion.button>
              </form>
            </div>
          )}

          {/* Step 4: Success */}
          {currentStep === 4 && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h2 className="font-poppins font-semibold text-xl text-gray-900 dark:text-white">
                Đặt lại mật khẩu thành công!
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Mật khẩu của bạn đã được đặt lại thành công. Bây giờ bạn có thể đăng nhập với mật khẩu mới.
              </p>
              <motion.button
                whileHover={{ scale: 1.01, y: -2 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => isModal && onClose ? onClose() : navigate('/login')}
                className="group flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary"
              >
                Đăng nhập ngay
              </motion.button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
