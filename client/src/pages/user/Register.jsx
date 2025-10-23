import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Register.css';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  // Form state
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    username: '',
    name: '',
    language: 'en',
    timezone: 'UTC'
  });

  // UI state
  const [currentStep, setCurrentStep] = useState(1); // 1: register, 2: verify
  const [loading, setLoading] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [confirmToken, setConfirmToken] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);
  const [resendTimer, setResendTimer] = useState(null);

  // Error state
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

  // Initialize device ID
  if (!localStorage.getItem('deviceId')) {
    localStorage.setItem('deviceId', generateDeviceId());
  }

  function generateDeviceId() {
    return 'device-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }

  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear field-specific error
    setErrors(prev => ({ ...prev, [name]: '', general: '' }));
    setAlert({ message: '', type: '' });
  };

  // Validation functions
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) return 'Email is required';
    if (!emailRegex.test(email)) return 'Please enter a valid email address';
    return '';
  };

  const validatePassword = (password) => {
    if (!password) return 'Password is required';
    if (password.length < 6 || password.length > 20) {
      return 'Password must be 6-20 characters long';
    }
    return '';
  };

  const validateConfirmPassword = () => {
    if (!formData.confirmPassword) return 'Please confirm your password';
    if (formData.password !== formData.confirmPassword) {
      return 'Passwords do not match';
    }
    return '';
  };

  const validateUsername = (username) => {
    if (!username) return 'Username is required';
    if (username.length < 3) return 'Username must be at least 3 characters';
    return '';
  };

  const validateAllFields = () => {
    const newErrors = {
      email: validateEmail(formData.email),
      password: validatePassword(formData.password),
      confirmPassword: validateConfirmPassword(),
      username: validateUsername(formData.username),
      name: formData.name ? '' : 'Full name is required',
      verificationCode: '',
      general: ''
    };

    setErrors(newErrors);
    return !Object.values(newErrors).some(error => error !== '');
  };

  // Show alert
  const showAlert = (message, type = 'info') => {
    setAlert({ message, type });
    setTimeout(() => {
      setAlert({ message: '', type: '' });
    }, 5000);
  };

  // Handle field blur
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
        error = validateConfirmPassword();
        break;
      case 'username':
        error = validateUsername(formData.username);
        break;
      case 'name':
        error = formData.name ? '' : 'Full name is required';
        break;
      default:
        break;
    }
    setErrors(prev => ({ ...prev, [field]: error }));
  };

  // Handle registration
  const handleRegister = async (e) => {
    e.preventDefault();
    setErrors({
      email: '', password: '', confirmPassword: '', username: '', name: '', 
      verificationCode: '', general: ''
    });
    setAlert({ message: '', type: '' });

    if (!validateAllFields()) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          deviceId: localStorage.getItem('deviceId')
        })
      });

      const data = await response.json();

      if (response.ok) {
        const responseData = data.data || data;
        
        // Save tokens for immediate use
        localStorage.setItem('access_token', responseData.access_token);
        localStorage.setItem('refresh_token', responseData.refresh_token);
        localStorage.setItem('user', JSON.stringify(responseData.user));

        // Save confirm token for later verification
        if (responseData.confirm_token) {
          localStorage.setItem('confirmToken', responseData.confirm_token);
          setConfirmToken(responseData.confirm_token);
        }

        const message = data.resultMessage?.en || 'Registration successful! Redirecting to dashboard...';
        showAlert(message, 'success');

        // Redirect to dashboard
        setTimeout(() => {
          navigate(`/user/${responseData.user.username}/guests`);
        }, 1500);

      } else {
        handleApiError(data);
      }

    } catch (error) {
      console.error('Registration error:', error);
      showAlert('An error occurred. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle API errors
  const handleApiError = (data) => {
    const errorCode = data.resultCode;
    const errorMessage = data.resultMessage?.en || 'An error occurred';

    const errorMap = {
      '00032': { field: 'email', message: 'This email is already registered' },
      '00067': { field: 'username', message: 'This username is already taken' },
      '00066': { field: 'password', message: 'Password must be 6-20 characters' },
      '00005': { field: 'email', message: 'Invalid email format' }
    };

    if (errorMap[errorCode]) {
      setErrors(prev => ({ ...prev, [errorMap[errorCode].field]: errorMap[errorCode].message }));
    } else {
      showAlert(errorMessage, 'error');
    }
  };

  // Handle verification
  const handleVerification = async (e) => {
    e.preventDefault();

    if (!verificationCode || verificationCode.length !== 6) {
      setErrors(prev => ({ ...prev, verificationCode: 'Please enter a valid 6-digit code' }));
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/verify-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          confirm_token: confirmToken,
          verification_code: verificationCode
        })
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        showAlert('Email verified successfully! Redirecting...', 'success');

        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);

      } else {
        if (data.resultCode === '00054') {
          setErrors(prev => ({ 
            ...prev, 
            verificationCode: 'Invalid verification code. Please try again.' 
          }));
        } else {
          setErrors(prev => ({ 
            ...prev, 
            verificationCode: data.resultMessage?.en || 'Verification failed' 
          }));
        }
      }

    } catch (error) {
      console.error('Verification error:', error);
      setErrors(prev => ({ 
        ...prev, 
        verificationCode: 'An error occurred. Please try again.' 
      }));
    } finally {
      setLoading(false);
    }
  };

  // Handle resend code
  const handleResendCode = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/send-verification-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: formData.email
        })
      });

      const data = await response.json();

      if (response.ok) {
        setConfirmToken(data.confirm_token);
        showAlert('New verification code sent to your email!', 'success');
        startResendTimer();
      } else {
        showAlert(data.resultMessage?.en || 'Failed to resend code', 'error');
      }

    } catch (error) {
      console.error('Resend error:', error);
      showAlert('An error occurred. Please try again.', 'error');
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

  // Handle back to register
  const handleBackToRegister = () => {
    setCurrentStep(1);
    setVerificationCode('');
    setErrors(prev => ({ ...prev, verificationCode: '' }));
    
    if (resendTimer) {
      clearInterval(resendTimer);
      setResendTimer(null);
    }
  };

  return (
    <div className="register-container">
      <div className="register-card">
        <div className="register-header">
          <h1>🌍 Travel Agent P</h1>
          <p>Create your account to get started</p>
        </div>

        <div className="register-body">
          {alert.message && (
            <div className={`alert alert-${alert.type}`}>
              {alert.message}
            </div>
          )}

          {/* Step 1: Registration Form */}
          {currentStep === 1 && (
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  onBlur={() => handleBlur('name')}
                  placeholder="Enter your full name"
                  required
                  className="form-input"
                />
                {errors.name && <span className="error-message">{errors.name}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  onBlur={() => handleBlur('email')}
                  placeholder="Enter your email"
                  required
                  className="form-input"
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  onBlur={() => handleBlur('username')}
                  placeholder="Choose a username"
                  required
                  className="form-input"
                />
                {errors.username && <span className="error-message">{errors.username}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  onBlur={() => handleBlur('password')}
                  placeholder="Create a password"
                  required
                  className="form-input"
                />
                {errors.password && <span className="error-message">{errors.password}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Confirm Password</label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  onBlur={() => handleBlur('confirmPassword')}
                  placeholder="Confirm your password"
                  required
                  className="form-input"
                />
                {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Language</label>
                  <select
                    name="language"
                    value={formData.language}
                    onChange={handleChange}
                    className="form-input"
                  >
                    <option value="en">English</option>
                    <option value="vi">Tiếng Việt</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Timezone</label>
                  <select
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleChange}
                    className="form-input"
                  >
                    <option value="UTC">UTC</option>
                    <option value="Asia/Ho_Chi_Minh">Asia/Ho Chi Minh</option>
                    <option value="America/New_York">America/New York</option>
                    <option value="Europe/London">Europe/London</option>
                  </select>
                </div>
              </div>

              <div className="info-note">
                <p>
                  ℹ️ <strong>Note:</strong> You can start using the app immediately after registration. 
                  Email verification is optional for enhanced security.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
              >
                <span className="btn-text">{loading ? 'Creating account...' : 'Create Account'}</span>
                {loading && <div className="spinner"></div>}
              </button>

              <div className="footer-text">
                Already have an account? <Link to="/">Login here</Link>
              </div>
            </form>
          )}

          {/* Step 2: Verification Form */}
          {currentStep === 2 && (
            <div className="verification-container">
              <div className="verification-icon">📧</div>
              <h2>Verify Your Email</h2>
              <p className="verification-message">
                We've sent a 6-digit verification code to<br />
                <strong>{formData.email}</strong>
              </p>

              <form onSubmit={handleVerification}>
                <div className="form-group">
                  <label className="form-label">Verification Code</label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').substring(0, 6);
                      setVerificationCode(value);
                      setErrors(prev => ({ ...prev, verificationCode: '' }));
                    }}
                    placeholder="Enter 6-digit code"
                    maxLength="6"
                    className="form-input code-input"
                  />
                  {errors.verificationCode && (
                    <span className="error-message">{errors.verificationCode}</span>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  <span className="btn-text">{loading ? 'Verifying...' : 'Verify Email'}</span>
                  {loading && <div className="spinner"></div>}
                </button>

                <div className="resend-container">
                  <p className="resend-text">Didn't receive the code?</p>
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={resendCountdown > 0}
                    className="btn-link"
                  >
                    Resend Code
                  </button>
                  {resendCountdown > 0 && (
                    <p className="timer-text">Resend available in {resendCountdown}s</p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleBackToRegister}
                  className="btn btn-secondary"
                >
                  Back to Registration
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
