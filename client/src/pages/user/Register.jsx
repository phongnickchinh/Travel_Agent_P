import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, Globe2, Lock, Mail, Shield, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
  getDeviceId,
  parseApiError,
  registerApi,
  sendVerificationCodeApi,
  validateConfirmPassword,
  validateEmail,
  validateName,
  validatePassword,
  validateRegistrationForm,
  validateUsername,
  verifyEmailApi
} from '../../services/authApi';

export default function Register({ isModal = false }) {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    username: '',
    name: '',
    language: 'en',
    timezone: 'UTC'
  });

  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [confirmToken, setConfirmToken] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);
  const [resendTimer, setResendTimer] = useState(null);

  const [errors, setErrors] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    username: '',
    name: '',
    verificationCode: '',
    general: ''
  });

  const [alert, setAlert] = useState({ message: '', type: '' });

  useEffect(() => {
    getDeviceId();
    return () => {
      if (resendTimer) {
        clearInterval(resendTimer);
      }
    };
  }, [resendTimer]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '', general: '' }));
    setAlert({ message: '', type: '' });
  };

  const showAlert = (message, type = 'info') => {
    setAlert({ message, type });
    setTimeout(() => {
      setAlert({ message: '', type: '' });
    }, 5000);
  };

  const handleBlur = (field) => {
    let error = '';
    switch (field) {
      case 'email':
        error = validateEmail(formData.email);
        break;
      case 'password':
        error = validatePassword(formData.password);
        break;
      case 'confirmPassword':
        error = validateConfirmPassword(formData.password, formData.confirmPassword);
        break;
      case 'username':
        error = validateUsername(formData.username);
        break;
      case 'name':
        error = validateName(formData.name);
        break;
      default:
        break;
    }
    setErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setErrors({
      email: '',
      password: '',
      confirmPassword: '',
      username: '',
      name: '',
      verificationCode: '',
      general: ''
    });
    setAlert({ message: '', type: '' });

    const { errors: validationErrors, isValid } = validateRegistrationForm(formData);
    if (!isValid) {
      setErrors({ ...validationErrors, verificationCode: '', general: '' });
      return;
    }

    setLoading(true);

    try {
      const data = await registerApi(formData);
      const responseData = data.data || data;

      if (responseData.confirmToken || responseData.confirm_token) {
        const token = responseData.confirmToken || responseData.confirm_token;
        localStorage.setItem('confirmToken', token);
        setConfirmToken(token);
      }

      localStorage.setItem('pendingVerificationEmail', formData.email);

      const message = data.resultMessage?.en || 'Registration successful! Please verify your email.';
      showAlert(message, 'success');
      setCurrentStep(2);
    } catch (error) {
      console.error('Registration error:', error);
      if (error.response?.data) {
        const { field, message, isFieldError } = parseApiError(error.response.data);
        if (isFieldError) {
          setErrors((prev) => ({ ...prev, [field]: message }));
        } else {
          showAlert(message, 'error');
        }
      } else {
        showAlert('An error occurred. Please try again.', 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerification = async (e) => {
    e.preventDefault();

    if (!verificationCode || verificationCode.length !== 6) {
      setErrors((prev) => ({ ...prev, verificationCode: 'Please enter a valid 6-digit code' }));
      return;
    }

    setLoading(true);

    try {
      await verifyEmailApi(confirmToken, verificationCode);

      localStorage.removeItem('confirmToken');
      localStorage.removeItem('pendingVerificationEmail');

      showAlert('Email verified successfully! Please login to continue.', 'success');

      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (error) {
      console.error('Verification error:', error);
      if (error.response?.data) {
        const { message } = parseApiError(error.response.data);
        setErrors((prev) => ({ ...prev, verificationCode: message }));
      } else {
        setErrors((prev) => ({ ...prev, verificationCode: 'An error occurred. Please try again.' }));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    try {
      const data = await sendVerificationCodeApi(formData.email);
      setConfirmToken(data.confirm_token);
      showAlert('New verification code sent to your email!', 'success');
      startResendTimer();
    } catch (error) {
      console.error('Resend error:', error);
      const message = error.response?.data?.resultMessage?.en || 'Failed to resend code';
      showAlert(message, 'error');
    }
  };

  const startResendTimer = () => {
    setResendCountdown(60);

    const timer = setInterval(() => {
      setResendCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    setResendTimer(timer);
  };

  const handleBackToRegister = () => {
    setCurrentStep(1);
    setVerificationCode('');
    setErrors((prev) => ({ ...prev, verificationCode: '' }));

    if (resendTimer) {
      clearInterval(resendTimer);
      setResendTimer(null);
    }
  };

  const cardClasses = `relative w-full ${isModal ? 'max-h-[90vh]' : 'min-h-[70vh]'} max-w-3xl overflow-hidden rounded-3xl bg-white/90 dark:bg-gray-900/90 shadow-2xl ring-1 ring-black/5 backdrop-blur-md`;

  return (
    <div className={`${isModal ? 'w-full' : 'min-h-screen bg-gray-50 dark:bg-gray-950'} flex items-center justify-center px-4 py-10`}>
      <div className={cardClasses}>
        <div className="bg-gradient-to-br from-brand-primary/90 to-brand-secondary/90 text-white px-6 py-6 flex items-center justify-center">
          <div className="justify-center">
            <p className="text-xs uppercase tracking-wide text-white">Tạo tài khoản</p>
            <h1 className="font-poppins font-semibold text-2xl mt-1">Travel Agent P</h1>
            <p className="text-sm text-white/80">Khởi động hành trình khám phá của bạn</p>
          </div>
        </div>

        <div className="px-6 py-6 space-y-5">
          {alert.message && (
            <div
              className={`rounded-xl border px-4 py-3 text-sm ${
                alert.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : alert.type === 'error'
                  ? 'border-red-200 bg-red-50 text-red-800'
                  : 'border-blue-200 bg-blue-50 text-blue-800'
              }`}
            >
              {alert.message}
            </div>
          )}

          {currentStep === 1 && (
            <form onSubmit={handleRegister} className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Họ và tên</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    onBlur={() => handleBlur('name')}
                    placeholder="Nhập họ tên"
                    required
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                </div>
                {errors.name && <p className="text-xs text-red-500">{errors.name}</p>}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Username</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    onBlur={() => handleBlur('username')}
                    placeholder="Chọn username"
                    required
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                </div>
                {errors.username && <p className="text-xs text-red-500">{errors.username}</p>}
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    onBlur={() => handleBlur('email')}
                    placeholder="name@example.com"
                    required
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                </div>
                {errors.email && <p className="text-xs text-red-500">{errors.email}</p>}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    onBlur={() => handleBlur('password')}
                    placeholder="Tạo mật khẩu"
                    required
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                </div>
                {errors.password && <p className="text-xs text-red-500">{errors.password}</p>}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Xác nhận mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    onBlur={() => handleBlur('confirmPassword')}
                    placeholder="Nhập lại mật khẩu"
                    required
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                </div>
                {errors.confirmPassword && <p className="text-xs text-red-500">{errors.confirmPassword}</p>}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Ngôn ngữ</label>
                <div className="relative">
                  <Globe2 className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <select
                    name="language"
                    value={formData.language}
                    onChange={handleChange}
                    className="w-full appearance-none rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  >
                    <option value="en">English</option>
                    <option value="vi">Tiếng Việt</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Múi giờ</label>
                <div className="relative">
                  <Globe2 className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <select
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleChange}
                    className="w-full appearance-none rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  >
                    <option value="UTC">UTC</option>
                    <option value="Asia/Ho_Chi_Minh">Asia/Ho Chi Minh</option>
                    <option value="America/New_York">America/New York</option>
                    <option value="Europe/London">Europe/London</option>
                  </select>
                </div>
              </div>

              <div className="md:col-span-2 rounded-xl bg-brand-muted/60 px-4 py-3 text-sm text-brand-primary">
                ℹ️ Bạn có thể sử dụng app ngay sau khi đăng ký. Xác minh email giúp tăng bảo mật cho tài khoản.
              </div>

              <div className="md:col-span-2 flex flex-col gap-3">
                <motion.button
                  whileHover={{ scale: 1.01, y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={loading}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Đang tạo tài khoản...' : 'Tạo tài khoản'}
                  <ArrowRight className="h-5 w-5" />
                </motion.button>

                <div className="text-center text-sm text-gray-600 dark:text-gray-300">
                  Đã có tài khoản?
                  <Link to="/login" className="ml-1 font-semibold text-brand-primary hover:text-brand-secondary dark:text-brand-muted dark:hover:text-white">Đăng nhập</Link>
                </div>
              </div>
            </form>
          )}

          {currentStep === 2 && (
            <div className="space-y-5">
              <div className="flex items-center gap-3 rounded-xl bg-brand-muted/70 px-4 py-3 text-brand-primary">
                <CheckCircle2 className="h-6 w-6" />
                <div>
                  <h2 className="font-semibold">Xác thực email</h2>
                  <p className="text-sm text-brand-primary/80">Nhập mã 6 chữ số đã gửi tới {formData.email}</p>
                </div>
              </div>

              <form onSubmit={handleVerification} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Mã xác thực</label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').substring(0, 6);
                      setVerificationCode(value);
                      setErrors((prev) => ({ ...prev, verificationCode: '' }));
                    }}
                    placeholder="Nhập 6 chữ số"
                    maxLength="6"
                    className="w-full rounded-xl border border-gray-200 bg-white/90 px-4 py-3 text-center text-lg font-semibold tracking-[0.4em] text-gray-900 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                  />
                  {errors.verificationCode && <p className="text-xs text-red-500">{errors.verificationCode}</p>}
                </div>

                <motion.button
                  whileHover={{ scale: 1.01, y: -2 }}
                  whileTap={{ scale: 0.99 }}
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Đang xác thực...' : 'Xác thực email'}
                  <CheckCircle2 className="h-5 w-5" />
                </motion.button>

                <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600 dark:text-gray-300">
                  <div className="flex items-center gap-2">
                    <span>Không nhận được mã?</span>
                    <button
                      type="button"
                      onClick={handleResendCode}
                      disabled={resendCountdown > 0}
                      className="font-semibold text-brand-primary hover:text-brand-secondary disabled:opacity-50"
                    >
                      Gửi lại
                    </button>
                  </div>
                  {resendCountdown > 0 && (
                    <span className="text-xs text-gray-500">Thử lại sau {resendCountdown}s</span>
                  )}
                </div>

                <div className="flex flex-wrap gap-3">
                  <motion.button
                    whileHover={{ scale: 1.01, y: -2 }}
                    whileTap={{ scale: 0.99 }}
                    type="button"
                    onClick={handleBackToRegister}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white/80 px-4 py-3 text-sm font-semibold text-gray-700 shadow-sm transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-700 dark:bg-gray-900/60 dark:text-gray-100"
                  >
                    Quay lại đăng ký
                  </motion.button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
