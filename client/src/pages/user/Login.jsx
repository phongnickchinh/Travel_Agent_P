import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Login.css';

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

export default function Login() {
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // Initialize Google Sign-In
  useEffect(() => {
    loadGoogleScript().then(() => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: '691313143015-dl1ao5k5nj9is2rs2v8c2u2ulnj4i6ge.apps.googleusercontent.com',
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
  }, []);

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
    console.log("Google ID Token:", id_token);

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

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>🌍 Travel Agent P</h1>
          <p>Welcome back! Please login to continue</p>
        </div>

        <div className="login-body">
          {success && <div className="alert alert-success">{success}</div>}
          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="Enter your email"
                required
                className="form-input"
              />
              {emailError && <span className="error-message">{emailError}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Enter your password"
                required
                className="form-input"
              />
              {passwordError && <span className="error-message">{passwordError}</span>}
            </div>

            <div className="forgot-password">
              <Link to="/reset-password">Forgot password?</Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
            >
              <span className="btn-text">{loading ? 'Logging in...' : 'Login'}</span>
              {loading && <div className="spinner"></div>}
            </button>
          </form>

          <div className="divider">
            <span>OR</span>
          </div>

          <div className="google-btn-wrapper">
            <div id="googleSignInButton"></div>
          </div>

          <div className="register-link">
            Don't have an account? <Link to="/register">Register here</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
