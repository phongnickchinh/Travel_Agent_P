import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL;

// Log API URL để debugging
console.log('API Base URL:', API_BASE);

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false, // Tránh gửi cookies tự động
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    // Thêm header để giúp CORS
    'Access-Control-Allow-Origin': '*',
  },
});

// trạng thái refresh token
let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

// Thêm access token vào header request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Xử lý response lỗi 401 để tự refresh token
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/login') &&
      !originalRequest.url.includes('/refresh-token')
    ) {
      if (isRefreshing) {
        // Đang refresh token, chờ token mới rồi retry
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = 'Bearer ' + token;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      
      // Kiểm tra nếu refreshToken không tồn tại, đăng xuất và từ chối promise
      if (!refreshToken) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(new Error('No refresh token available'));
      }

      return new Promise((resolve, reject) => {
        console.log('Attempting to refresh token with:', API_BASE);
        
        axios
          .post(`${API_BASE}/refresh-token`, { refresh_token: refreshToken }, {
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'Access-Control-Allow-Origin': '*',
            }
          })
          .then(({ data }) => {
            console.log('Token refresh successful');
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            api.defaults.headers.Authorization = 'Bearer ' + data.access_token;
            originalRequest.headers.Authorization = 'Bearer ' + data.access_token;
            onRefreshed(data.access_token);
            resolve(api(originalRequest));
          })
          .catch((err) => {
            console.error('Token refresh failed:', err);
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login'; // hoặc gọi logout trong context
            reject(err);
          })
          .finally(() => {
            isRefreshing = false;
          });
      });
    }

    return Promise.reject(error);
  }
);

export default api;
