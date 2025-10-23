import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './ResetPassword.css';

export default function ResetPassword() {
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

  // Validate email
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) return 'Email is required';
    if (!emailRegex.test(email)) return 'Please enter a valid email';
    return '';
  };

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
      const response = await fetch('http://127.0.0.1:5000/request-reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: email.trim() })
      });

      const data = await response.json();

      if (response.ok) {
        const responseData = data.data || data;
        setResetToken(responseData.resetToken);
        setCurrentStep(2);
        startResendTimer();
        showAlert('Verification code sent to your email!', 'success');
      } else {
        const errorMessage = data.resultMessage?.en || data.message || 'Failed to send code';
        showAlert(errorMessage, 'error');
      }

    } catch (error) {
      console.error('Send code error:', error);
      showAlert('An error occurred. Please try again.', 'error');
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
      const response = await fetch('http://127.0.0.1:5000/validate-reset-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resetToken: resetToken,
          resetCode: resetCode
        })
      });

      const data = await response.json();

      if (response.ok) {
        setTempAccessToken(data.tempAccessToken);
        setCurrentStep(3);
        showAlert('Code verified successfully!', 'success');
      } else {
        const errorMessage = data.resultMessage?.en || data.message || 'Invalid verification code';
        setErrors(prev => ({ ...prev, resetCode: errorMessage }));
      }

    } catch (error) {
      console.error('Verify code error:', error);
      setErrors(prev => ({ ...prev, resetCode: 'An error occurred. Please try again.' }));
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Reset password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    clearErrors();

    // Validate password
    if (!newPassword) {
      setErrors(prev => ({ ...prev, newPassword: 'Password is required' }));
      return;
    }

    if (newPassword.length < 6 || newPassword.length > 20) {
      setErrors(prev => ({ ...prev, newPassword: 'Password must be 6-20 characters long' }));
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrors(prev => ({ ...prev, confirmPassword: 'Passwords do not match' }));
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tempAccessToken: tempAccessToken,
          newPassword: newPassword
        })
      });

      const data = await response.json();

      if (response.ok) {
        setCurrentStep(4);
      } else {
        const errorMessage = data.resultMessage?.en || data.message || 'Failed to reset password';
        showAlert(errorMessage, 'error');
      }

    } catch (error) {
      console.error('Reset password error:', error);
      showAlert('An error occurred. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Resend code
  const handleResendCode = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/request-reset-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: email })
      });

      const data = await response.json();

      if (response.ok) {
        const responseData = data.data || data;
        setResetToken(responseData.resetToken);
        showAlert('New verification code sent!', 'success');
        startResendTimer();
      } else {
        showAlert('Failed to resend code', 'error');
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

  return (
    <div className="reset-password-container">
      <div className="reset-card">
        <div className="reset-header">
          <div className="icon">🔐</div>
          <h1>Reset Password</h1>
          <p>Recover your account securely</p>
        </div>

        <div className="reset-body">
          {alert.message && (
            <div className={`alert alert-${alert.type}`}>
              {alert.message}
            </div>
          )}

          {/* Step 1: Enter Email */}
          {currentStep === 1 && (
            <div>
              <p className="info-text">
                Enter your email address and we'll send you a verification code to reset your password.
              </p>

              <form onSubmit={handleSendCode}>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setErrors(prev => ({ ...prev, email: '' }));
                    }}
                    placeholder="Enter your email"
                    required
                    className="form-input"
                  />
                  {errors.email && <span className="error-message">{errors.email}</span>}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  <span className="btn-text">{loading ? 'Sending...' : 'Send Verification Code'}</span>
                  {loading && <div className="spinner"></div>}
                </button>

                <Link to="/" className="btn btn-secondary">
                  Back to Login
                </Link>
              </form>
            </div>
          )}

          {/* Step 2: Verify Code */}
          {currentStep === 2 && (
            <div>
              <p className="info-text">
                We've sent a 6-digit verification code to<br />
                <strong>{email}</strong>
              </p>

              <form onSubmit={handleVerifyCode}>
                <div className="form-group">
                  <label className="form-label">Verification Code</label>
                  <input
                    type="text"
                    value={resetCode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').substring(0, 6);
                      setResetCode(value);
                      setErrors(prev => ({ ...prev, resetCode: '' }));
                    }}
                    placeholder="6-digit code"
                    maxLength="6"
                    className="form-input code-input"
                  />
                  {errors.resetCode && <span className="error-message">{errors.resetCode}</span>}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  <span className="btn-text">{loading ? 'Verifying...' : 'Verify Code'}</span>
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
                  onClick={handleBackToStep1}
                  className="btn btn-secondary"
                >
                  Change Email
                </button>
              </form>
            </div>
          )}

          {/* Step 3: New Password */}
          {currentStep === 3 && (
            <div>
              <p className="info-text">
                Create a new password for your account.
              </p>

              <form onSubmit={handleResetPassword}>
                <div className="form-group">
                  <label className="form-label">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      setErrors(prev => ({ ...prev, newPassword: '' }));
                    }}
                    placeholder="Enter new password"
                    required
                    className="form-input"
                  />
                  {errors.newPassword && <span className="error-message">{errors.newPassword}</span>}
                  <div className="password-requirements">
                    <strong>Password requirements:</strong>
                    <ul>
                      <li>Must be 6-20 characters long</li>
                      <li>Should include letters and numbers</li>
                    </ul>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Confirm Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      setErrors(prev => ({ ...prev, confirmPassword: '' }));
                    }}
                    placeholder="Confirm new password"
                    required
                    className="form-input"
                  />
                  {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  <span className="btn-text">{loading ? 'Resetting...' : 'Reset Password'}</span>
                  {loading && <div className="spinner"></div>}
                </button>
              </form>
            </div>
          )}

          {/* Step 4: Success */}
          {currentStep === 4 && (
            <div className="success-container">
              <div className="success-icon">✅</div>
              <h2>Password Reset Successful!</h2>
              <p className="info-text">
                Your password has been successfully reset. You can now login with your new password.
              </p>
              <button
                onClick={() => navigate('/')}
                className="btn btn-primary"
              >
                Go to Login
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
