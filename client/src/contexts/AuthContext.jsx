import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { getProfileApi, googleLoginApi, loginApi, logoutApi, refreshTokenApi } from '../services/authApi';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const isRefreshing = useRef(false);
  const refreshRetryCount = useRef(0);
  const MAX_REFRESH_RETRIES = 3;

  useEffect(() => {
    const checkUserAuthentication = async () => {
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      // Fast path: No tokens at all
      if (!accessToken && !refreshToken) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        // Case 1: Have access token -> try to get profile
        if (accessToken) {
          try {
            const userInfo = await getProfileApi();
            setUser(userInfo);
            setLoading(false);
            return;
          } catch (error) {
            // Access token invalid or expired, fall through to refresh token logic
          }
        }

        // Case 2: No access token or it failed, but have refresh token
        if (refreshToken) {
          try {
            const res = await refreshTokenApi(refreshToken);
            // Handle response structure: { data: { access_token, ... } } or { access_token, ... }
            const data = res.data || res;
            const newAccessToken = data.access_token;
            const newRefreshToken = data.refresh_token;

            if (newAccessToken) {
              localStorage.setItem('access_token', newAccessToken);
              if (newRefreshToken) {
                localStorage.setItem('refresh_token', newRefreshToken);
              }
              
              // Retry get profile with new token
              const userInfo = await getProfileApi();
              setUser(userInfo);
            } else {
              throw new Error('No access token in refresh response');
            }
          } catch (refreshError) {
            console.error('Refresh token failed:', refreshError);
            // Both tokens invalid
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setUser(null);
          }
        } else {
          // No tokens at all (should be caught by fast path, but safe fallback)
          setUser(null);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkUserAuthentication();
  }, []);

  // Đăng nhập
  const login = async (credentials) => {
    const response = await loginApi(credentials);
    const data = response.data || response;
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setUser(data.user);
    return data.user;
  };

  // Đăng ký (optional - Register component handles this directly)
  const register = async (userData) => {
    // This is a placeholder if needed in the future
    // Currently Register.jsx handles registration directly
    throw new Error('Use Register component directly');
  };

  // Đăng nhập bằng Google
  const googleLogin = async (idToken) => {
    const response = await googleLoginApi(idToken);
    // Backend returns: { data: { user, access_token, refresh_token } } or { user, access_token, refresh_token }
    const data = response.data || response;
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setUser(data.user);
    return data.user;
  };

  // Refresh user data (for profile updates)
  const refreshUser = async () => {
    try {
      const userInfo = await getProfileApi();
      setUser(userInfo);
      return { success: true, user: userInfo };
    } catch (error) {
      console.error('Failed to refresh user:', error);
      return { success: false, error: error.message };
    }
  };

  // Logout function
  const logout = async () => {
    // Optimistic logout: Clear state immediately
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    
    try {
      await logoutApi();
    } catch (error) {
      console.error('Logout API failed:', error);
    }
  };

  // Silent token refresh with retry logic (prevents aggressive logout on network hiccups)
  useEffect(() => {
    // Don't start interval until initial auth check completes
    if (loading) return;
    // Don't refresh if no user is logged in
    if (!user) return;

    const interval = setInterval(async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) return;
      
      // Prevent concurrent refresh requests
      if (isRefreshing.current) return;
      isRefreshing.current = true;

      try {
        const res = await refreshTokenApi(refreshToken);
        const data = res.data || res;
        
        if (data.access_token) {
          localStorage.setItem('access_token', data.access_token);
          if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
          }
          // Reset retry count on success
          refreshRetryCount.current = 0;
        }
      } catch (error) {
        console.warn('Token refresh failed:', error);
        refreshRetryCount.current += 1;
        
        // Only logout after multiple consecutive failures
        if (refreshRetryCount.current >= MAX_REFRESH_RETRIES) {
          console.error('Token refresh failed after max retries, logging out');
          logout();
        }
      } finally {
        isRefreshing.current = false;
      }
    }, 55 * 1000); // Refresh every 55 seconds

    return () => clearInterval(interval);
  }, [loading, user]);

  return (
    <AuthContext.Provider value={{ user, login, register, googleLogin, logout, refreshUser, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
