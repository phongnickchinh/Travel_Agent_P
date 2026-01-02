import { createContext, useContext, useEffect, useState } from 'react';
import { getProfileApi, googleLoginApi, loginApi, logoutApi, refreshTokenApi } from '../services/authApi';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

useEffect(() => {
  // Sử dụng một hàm async bên trong useEffect
  const checkUserAuthentication = async () => {
    const accessToken = localStorage.getItem('access_token');

    if (accessToken) {
      try {
        const userInfo = await getProfileApi();
        setUser(userInfo);
      } catch (error) {
        console.error('Failed to get user profile:', error);
        localStorage.removeItem('access_token');
        // localStorage.removeItem('refresh_token');
        setUser(null);
      } finally {
        // Luôn set loading thành false sau khi đã xử lý xong
        setLoading(false);
      }
    } else {
      // Nếu không có token, không cần loading nữa
      setLoading(false);
    }
  };

  checkUserAuthentication();
}, []);

  // Đăng nhập
  const login = async (credentials) => {
    const response = await loginApi(credentials);
    // Backend returns: { data: { user, access_token, refresh_token } } or { user, access_token, refresh_token }
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

  // Đăng xuất
  const logout = async () => {
    await logoutApi();
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  // Tự động refresh token định kỳ
  useEffect(() => {
    const interval = setInterval(() => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) return;

      refreshTokenApi(refreshToken)
        .then((res) => {
          localStorage.setItem('access_token', res.access_token);
          // localStorage.setItem('refresh_token', res.refresh_token);
        })
        .catch(() => {
          logout();
        });
    }, 55 * 1000); // Gọi sau mỗi 55 giây

    return () => clearInterval(interval);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, googleLogin, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
