import api from './apiClient';

/**
 * Generate a unique device ID
 */
export function generateDeviceId() {
  return 'device-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

/**
 * Get or create device ID from localStorage
 */
export function getDeviceId() {
  let deviceId = localStorage.getItem('deviceId');
  if (!deviceId) {
    deviceId = generateDeviceId();
    localStorage.setItem('deviceId', deviceId);
  }
  return deviceId;
}

/**
 * Login with email and password
 */
export async function loginApi(credentials) {
  const res = await api.post('/login', credentials);
  // res.data = { user: {...}, access_token, refresh_token }
  return res.data;
}

/**
 * Login with Google OAuth token
 */
export async function googleLoginApi(idToken) {
  const deviceId = getDeviceId();
  
  const res = await api.post('/google', {
    token: idToken,
    deviceId: deviceId
  }, {
    headers: {
      'Authorization': `Bearer ${idToken}`
    }
  });
  return res.data;
}

/**
 * Get authentication configuration (Google Client ID, etc.)
 */
export async function getAuthConfigApi() {
  const res = await api.get('/config');
  return res.data.google_client_id ? { success: true, data: { google_client_id: res.data.google_client_id } } : { success: false };
}

/**
 * Register new user account
 */
export async function registerApi(userData) {
  const deviceId = getDeviceId();
  
  const res = await api.post('/register', {
    ...userData,
    deviceId: deviceId
  });
  
  // Response: { user, access_token, refresh_token, confirm_token }
  return res.data;
}

/**
 * Verify email with confirmation code
 */
export async function verifyEmailApi(confirmToken, verificationCode) {
  const res = await api.post('/verify-email', {
    confirm_token: confirmToken,
    verification_code: verificationCode
  });
  
  // Response: { access_token, refresh_token, message }
  return res.data;
}

/**
 * Send verification code to email
 */
export async function sendVerificationCodeApi(email) {
  const res = await api.post('/send-verification-code', {
    email: email
  });
  
  // Response: { confirm_token, message }
  return res.data;
}

/**
 * Request password reset (send reset code to email)
 */
export async function requestPasswordResetApi(email) {
  const res = await api.post('/request-reset-password', {
    email: email
  });
  
  // Response: { reset_token, message }
  return res.data;
}

/**
 * Validate reset code
 */
export async function validateResetCodeApi(resetToken, resetCode) {
  const res = await api.post('/validate-reset-code', {
    resetToken: resetToken,
    resetCode: resetCode
  });
  
  // Response: { temp_access_token, message }
  return res.data;
}

/**
 * Reset password with temp access token
 */
export async function resetPasswordApi(tempAccessToken, newPassword) {
  const res = await api.post('/reset-password', {
    tempAccessToken: tempAccessToken,
    newPassword: newPassword
  });
  
  // Response: { message }
  return res.data;
}

/**
 * Resend reset code
 */
export async function resendResetCodeApi(email) {
  const res = await api.post('/request-reset-code', {
    email: email
  });
  
  // Response: { reset_token, message }
  return res.data;
}

export async function logoutApi() {
  // Gửi logout, có thể k cần token vì token có thể hết hạn rồi
  try {
    await api.post('/logout');
  } catch (_) {}
}

export async function getProfileApi() {
  try {
    const res = await api.get('/user/');
    if (!res.data) {
      throw new Error('User data is empty');
    }
    // Backend returns: { resultCode, resultMessage, user }
    // Extract user object from response
    return res.data.user || res.data; // Return user object
  } catch (error) {
    console.error('Error getting profile:', error);
    throw error;
  }
}

export async function refreshTokenApi(refreshToken) {
  const res = await api.post('/refresh-token', { refresh_token: refreshToken });
  return res.data; // { access_token, refresh_token }
}

// ============================================
// VALIDATION UTILITIES
// ============================================

/**
 * Validate email format
 */
export function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email) return 'Email is required';
  if (!emailRegex.test(email)) return 'Please enter a valid email address';
  return '';
}

/**
 * Validate password
 */
export function validatePassword(password) {
  if (!password) return 'Password is required';
  if (password.length < 6 || password.length > 20) {
    return 'Password must be 6-20 characters long';
  }
  return '';
}

/**
 * Validate confirm password matches password
 */
export function validateConfirmPassword(password, confirmPassword) {
  if (!confirmPassword) return 'Please confirm your password';
  if (password !== confirmPassword) {
    return 'Passwords do not match';
  }
  return '';
}

/**
 * Validate username
 */
export function validateUsername(username) {
  if (!username) return 'Username is required';
  if (username.length < 3) return 'Username must be at least 3 characters';
  return '';
}

/**
 * Validate full name
 */
export function validateName(name) {
  if (!name) return 'Full name is required';
  if (name.trim().length < 2) return 'Name must be at least 2 characters';
  return '';
}

/**
 * Validate all registration fields
 */
export function validateRegistrationForm(formData) {
  const errors = {
    email: validateEmail(formData.email),
    password: validatePassword(formData.password),
    confirmPassword: validateConfirmPassword(formData.password, formData.confirmPassword),
    username: validateUsername(formData.username),
    name: validateName(formData.name)
  };

  const hasErrors = Object.values(errors).some(error => error !== '');
  return { errors, isValid: !hasErrors };
}

/**
 * Parse API error response and map to field-specific errors
 */
export function parseApiError(data) {
  const errorCode = data.resultCode;
  const errorMessage = data.resultMessage?.en || 'An error occurred';

  const errorMap = {
    '00032': { field: 'email', message: 'This email is already registered' },
    '00067': { field: 'username', message: 'This username is already taken' },
    '00066': { field: 'password', message: 'Password must be 6-20 characters' },
    '00005': { field: 'email', message: 'Invalid email format' },
    '00054': { field: 'verificationCode', message: 'Invalid verification code. Please try again.' }
  };

  if (errorMap[errorCode]) {
    return {
      field: errorMap[errorCode].field,
      message: errorMap[errorCode].message,
      isFieldError: true
    };
  }

  return {
    field: 'general',
    message: errorMessage,
    isFieldError: false
  };
}
