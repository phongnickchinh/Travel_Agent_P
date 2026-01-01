import { motion } from 'framer-motion';
import { Loader2, Lock, Mail } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { getAuthConfigApi } from '../../services/authApi';

// Load Google Sign-In script
const loadGoogleScript = () => {
  return new Promise((resolve, reject) => {
    if (window.google) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

export default function Login({ isModal = false }) {
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [googleClientId, setGoogleClientId] = useState(null);

  // Fetch Google Client ID from backend
  useEffect(() => {
    const fetchAuthConfig = async () => {
      try {
        const result = await getAuthConfigApi();
        if (result.success && result.data.google_client_id) {
          setGoogleClientId(result.data.google_client_id);
        }
      } catch (err) {
        console.error('Failed to fetch auth config:', err);
      }
    };
    fetchAuthConfig();
  }, []);

  // Initialize Google Sign-In
  useEffect(() => {
    if (!googleClientId) return;

    loadGoogleScript().then(() => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleGoogleLogin,
          auto_select: false,
        });
        window.google.accounts.id.renderButton(
          document.getElementById('googleSignInButton'),
          { 
            type: 'standard',
            shape: 'rectangular',
            theme: 'outline',
            text: 'signin_with',
            size: 'large',
            logo_alignment: 'left'
          }
        );
      }
    }).catch(err => {
      console.error('Failed to load Google Sign-In script:', err);
    });
  }, [googleClientId]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    // Clear field-specific errors
    if (e.target.name === 'email') setEmailError('');
    if (e.target.name === 'password') setPasswordError('');
    setError('');
  };

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setEmailError('');
    setPasswordError('');

    // Validation
    if (!form.email) {
      setEmailError('Email is required');
      return;
    }

    if (!validateEmail(form.email)) {
      setEmailError('Please enter a valid email');
      return;
    }

    if (!form.password) {
      setPasswordError('Password is required');
      return;
    }

    setLoading(true);
    try {
      const loggedInUser = await login(form);
      setSuccess('Login successful! Redirecting...');
      setTimeout(() => {
        navigate(`/dashboard/${loggedInUser.username}`);
      }, 1000);
    } catch (err) {
      setError(err.message || 'Email or password is incorrect.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async (response) => {
    const id_token = response.credential;
    try {
      const loggedInUser = await googleLogin(id_token);
      setSuccess('Google login successful! Redirecting...');
      setTimeout(() => {
        navigate(`/dashboard/${loggedInUser.username}/`);
      }, 1000);
    } catch (error) {
      console.error('Google login error:', error);
      setError(error.message || 'An error occurred during Google login');
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
        <div className="bg-linear-to-br from-brand-primary to-brand-secondary text-white px-6 py-6">
          <div className="flex items-center justify-center">
            <div className="justify-center">
              <p className="text-xs uppercase tracking-[0.2em] text-white/70">Chào mừng trở lại</p>
              <h1 className="font-poppins font-semibold text-2xl mt-1">Travel Agent P</h1>
              <p className="text-sm text-white/80">Đăng nhập để tiếp tục hành trình của bạn</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6 space-y-5">
          {success && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-800 text-sm">
              {success}
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-800 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="Nhập email"
                  required
                  className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                />
              </div>
              {emailError && <p className="text-xs text-red-500">{emailError}</p>}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-800 dark:text-gray-100">Mật khẩu</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Nhập mật khẩu"
                  required
                  className="w-full rounded-xl border border-gray-200 bg-white/90 px-11 py-3 text-sm text-gray-900 placeholder:text-gray-400 shadow-sm transition focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100"
                />
              </div>
              {passwordError && <p className="text-xs text-red-500">{passwordError}</p>}
            </div>

            <div className="text-right text-sm">
              <Link to="/reset-password" className="text-brand-primary hover:text-brand-secondary dark:text-brand-muted dark:hover:text-white">Quên mật khẩu?</Link>
            </div>

            <motion.button
              whileHover={{ scale: 1.01, y: -2 }}
              whileTap={{ scale: 0.99 }}
              type="submit"
              disabled={loading}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-3 text-white font-semibold shadow-lg transition hover:bg-brand-secondary disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
              <span>{loading ? 'Đang đăng nhập...' : 'Đăng nhập'}</span>
            </motion.button>
          </form>

          <div className="flex items-center gap-3 text-xs uppercase tracking-[0.2em] text-gray-400">
            <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
            hoặc
            <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
          </div>

          <div className="flex justify-center">
            <div id="googleSignInButton" className="flex w-full max-w-xs items-center justify-center" />
          </div>

          <div className="text-center text-sm text-gray-600 dark:text-gray-300">
            Chưa có tài khoản?
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="ml-1 font-semibold text-brand-primary hover:text-brand-secondary dark:text-brand-muted dark:hover:text-white"
            >
              Đăng ký ngay
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
