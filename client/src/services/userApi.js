import api from './apiClient';

/**
 * User API Service
 * Handles user profile operations
 */

class UserAPI {
  /**
   * Update user profile (text fields only)
   * @param {Object} userData - User data to update (username, name, language, timezone)
   * @returns {Promise<Object>} { success: boolean, data: updatedUser, error?: string }
   */
  async updateProfile(userData) {
    try {
      const response = await api.put('/user/', userData);
      
      return {
        success: true,
        data: response.data.data?.user || response.data.user || response.data
      };
    } catch (error) {
      console.error('Error updating profile:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.response?.data?.message_vi || 'Failed to update profile',
        errorVi: error.response?.data?.message_vi || 'Cập nhật hồ sơ thất bại'
      };
    }
  }

  /**
   * Upload avatar image
   * @param {File} imageFile - Avatar image file
   * @returns {Promise<Object>} { success: boolean, data: updatedUser, error?: string }
   */
  async uploadAvatar(imageFile) {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await api.post('/user/avatar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return {
        success: true,
        data: response.data.data?.user || response.data.user || response.data
      };
    } catch (error) {
      console.error('Error uploading avatar:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.response?.data?.message_vi || 'Failed to upload avatar',
        errorVi: error.response?.data?.message_vi || 'Tải ảnh đại diện thất bại'
      };
    }
  }

  /**
   * Change user password
   * @param {string} oldPassword - Current password
   * @param {string} newPassword - New password
   * @returns {Promise<Object>} { success: boolean, message?: string, error?: string }
   */
  async changePassword(oldPassword, newPassword) {
    try {
      const response = await api.post('/user/change-password', {
        oldPassword,
        newPassword
      });
      
      return {
        success: true,
        message: response.data.message || response.data.resultMessage?.en || 'Password changed successfully'
      };
    } catch (error) {
      console.error('Error changing password:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.response?.data?.resultMessage?.en || 'Failed to change password'
      };
    }
  }

  /**
   * Get user profile
   * @returns {Promise<Object>} { success: boolean, data: user, error?: string }
   */
  async getProfile() {
    try {
      const response = await api.get('/user/');
      
      return {
        success: true,
        data: response.data.user || response.data
      };
    } catch (error) {
      console.error('Error getting profile:', error);
      return {
        success: false,
        error: error.response?.data?.message || 'Failed to get profile'
      };
    }
  }

  /**
   * Delete user account
   * @returns {Promise<Object>} { success: boolean, error?: string }
   */
  async deleteAccount() {
    try {
      await api.delete('/user/');
      
      return {
        success: true
      };
    } catch (error) {
      console.error('Error deleting account:', error);
      return {
        success: false,
        error: error.response?.data?.message || 'Failed to delete account'
      };
    }
  }
}

export default new UserAPI();
