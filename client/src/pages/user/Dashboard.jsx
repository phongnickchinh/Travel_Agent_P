import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Dashboard.css';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [tokenInfo, setTokenInfo] = useState({
    deviceId: '',
    accessToken: '',
    refreshToken: ''
  });

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    // Check if user is logged in
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      navigate('/login');
      return;
    }

    // Load token info
    setTokenInfo({
      deviceId: localStorage.getItem('deviceId') || 'N/A',
      accessToken: accessToken ? accessToken.substring(0, 30) + '...' : 'N/A',
      refreshToken: localStorage.getItem('refresh_token')?.substring(0, 30) + '...' || 'N/A'
    });
  }, [navigate]);

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const handleLogoutConfirm = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Still redirect even if API call fails
      navigate('/login');
    } finally {
      setIsLoggingOut(false);
      setShowLogoutModal(false);
    }
  };

  const handleLogoutCancel = () => {
    setShowLogoutModal(false);
  };

  const handleGoHome = () => {
    if (user && user.username) {
      navigate(`/dashboard/${user.username}`);
    } else {
      navigate('/');
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-card">
        <div className="welcome-header">
          <div className="success-icon">✓</div>
          <h1>Welcome to Travel Agent P! 🎉</h1>
          <p>Your account has been successfully verified</p>
        </div>

        <div className="info-card">
          <h3>📋 Account Information</h3>
          {user && (
            <>
              <div className="info-item">
                <span className="info-label">Username:</span>
                <span className="info-value">{user.username || 'N/A'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Email:</span>
                <span className="info-value">{user.email || 'N/A'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Name:</span>
                <span className="info-value">{user.name || 'N/A'}</span>
              </div>
            </>
          )}
          <div className="info-item">
            <span className="info-label">Device ID:</span>
            <span className="info-value">{tokenInfo.deviceId}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Access Token:</span>
            <span className="info-value token-value">{tokenInfo.accessToken}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Refresh Token:</span>
            <span className="info-value token-value">{tokenInfo.refreshToken}</span>
          </div>
          <div className="info-item">
            <span className="info-label">User Info:</span>
            <span className="info-value token-value">{JSON.stringify(user)}</span>
          </div>
        </div>

        <div className="info-card">
          <h3>✅ What's Next?</h3>
          <ul className="next-steps-list">
            <li>Your account is ready to use</li>
            <li>Access token is stored securely</li>
            <li>You can now make authenticated API calls</li>
            <li>Token will auto-refresh when needed</li>
          </ul>
        </div>

        {/* Quick Actions */}
        <div className="info-card quick-actions-card">
          <h3>🚀 Bắt đầu ngay</h3>
          <div className="quick-actions-grid">
            <button 
              className="quick-action-btn primary"
              onClick={() => navigate('/create-plan')}
            >
              <span className="qa-icon">✨</span>
              <span className="qa-text">Tạo Kế Hoạch Du Lịch</span>
              <span className="qa-desc">Để AI lên lịch trình cho bạn</span>
            </button>
            <button 
              className="quick-action-btn secondary"
              onClick={() => navigate('/search-demo')}
            >
              <span className="qa-icon">🔍</span>
              <span className="qa-text">Tìm Địa Điểm</span>
              <span className="qa-desc">Khám phá POI xung quanh</span>
            </button>
          </div>
        </div>

        <div className="actions">
          <button className="btn btn-primary" onClick={handleGoHome}>
            Go to Home
          </button>
          <button className="btn btn-danger" onClick={handleLogoutClick}>
            Logout
          </button>
        </div>
      </div>

      {/* Logout Confirmation Modal */}
      {showLogoutModal && (
        <div className="modal-overlay" onClick={handleLogoutCancel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-icon">⚠️</div>
              <h2>Confirm Logout</h2>
            </div>
            
            <div className="modal-body">
              <p>Are you sure you want to logout?</p>
              <p className="modal-subtitle">
                You'll need to login again to access your account.
              </p>
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn btn-secondary-modal" 
                onClick={handleLogoutCancel}
                disabled={isLoggingOut}
              >
                Cancel
              </button>
              <button 
                className="btn btn-danger-modal" 
                onClick={handleLogoutConfirm}
                disabled={isLoggingOut}
              >
                {isLoggingOut ? (
                  <>
                    <span className="spinner-small"></span>
                    Logging out...
                  </>
                ) : (
                  'Yes, Logout'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
