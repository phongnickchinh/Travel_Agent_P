import { useState } from 'react';
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

  // Initialize device ID on mount
  getDeviceId();

  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear field-specific error
    setErrors(prev => ({ ...prev, [name]: '', general: '' }));
    setAlert({ message: '', type: '' });
  };

  // Show alert
  const showAlert = (message, type = 'info') => {
    setAlert({ message, type });
    setTimeout(() => {
      setAlert({ message: '', type: '' });
    }, 5000);
  };

  // Handle field blur - use validation functions from authApi
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

    // Validate using authApi function
    const { errors: validationErrors, isValid } = validateRegistrationForm(formData);
    if (!isValid) {
      setErrors({ ...validationErrors, verificationCode: '', general: '' });
      return;
    }

    setLoading(true);

    try {
      // Call registerApi from authApi service
      const data = await registerApi(formData);
      const responseData = data.data || data;
      
      // Save confirm token for email verification
      if (responseData.confirmToken || responseData.confirm_token) {
        const token = responseData.confirmToken || responseData.confirm_token;
        localStorage.setItem('confirmToken', token);
        setConfirmToken(token);
      }

      // Store user email for verification page
      localStorage.setItem('pendingVerificationEmail', formData.email);

      const message = data.resultMessage?.en || 'Registration successful! Please verify your email.';
      showAlert(message, 'success');

      // Switch to verification step
      setCurrentStep(2);

    } catch (error) {
      console.error('Registration error:', error);
      
      // Parse API error using authApi helper
      if (error.response?.data) {
        const { field, message, isFieldError } = parseApiError(error.response.data);
        if (isFieldError) {
          setErrors(prev => ({ ...prev, [field]: message }));
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

  // Handle verification
  const handleVerification = async (e) => {
    e.preventDefault();

    if (!verificationCode || verificationCode.length !== 6) {
      setErrors(prev => ({ ...prev, verificationCode: 'Please enter a valid 6-digit code' }));
      return;
    }

    setLoading(true);

    try {
      // Call verifyEmailApi from authApi service
      const data = await verifyEmailApi(confirmToken, verificationCode);

      // Clear pending verification data
      localStorage.removeItem('confirmToken');
      localStorage.removeItem('pendingVerificationEmail');

      showAlert('Email verified successfully! Please login to continue.', 'success');

      // Redirect to login page
      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (error) {
      console.error('Verification error:', error);
      
      // Parse API error using authApi helper
      if (error.response?.data) {
        const { message } = parseApiError(error.response.data);
        setErrors(prev => ({ ...prev, verificationCode: message }));
      } else {
        setErrors(prev => ({ ...prev, verificationCode: 'An error occurred. Please try again.' }));
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle resend code
  const handleResendCode = async () => {
    try {
      // Call sendVerificationCodeApi from authApi service
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
