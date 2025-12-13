/**
 * Plan API Service
 * 
 * Purpose:
 * - CRUD operations for travel plans
 * - Trigger plan generation via Celery
 * - Poll plan status
 * 
 * Author: Travel Agent P Team
 */

import api from './apiClient';

class PlanAPI {
  /**
   * Create a new travel plan
   * @param {Object} planData - Plan creation data
   * @returns {Promise<Object>} - Created plan with plan_id and status
   */
  async createPlan(planData) {
    try {
      const response = await api.post('/plan/', planData);
      return {
        success: true,
        data: response.data.data,
        message: response.data.message
      };
    } catch (error) {
      console.error('[ERROR] Create plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message,
        errorVi: error.response?.data?.message_vi || 'Không thể tạo kế hoạch'
      };
    }
  }

  /**
   * Get list of user's plans with pagination
   * 
   * @param {Object} params - Query parameters
   * @param {number} params.page - Page number (default: 1)
   * @param {number} params.limit - Items per page (default: 20)
   * @param {string} params.status - Filter by status
   * @returns {Promise<Object>} - Plans list with pagination
   */
  async getPlans(params = {}) {
    try {
      const response = await api.get('/plan/', { params });
      return {
        success: true,
        data: response.data.data
      };
    } catch (error) {
      console.error('[ERROR] Get plans failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Get plan details by ID
   * 
   * @param {string} planId - Plan ID
   * @returns {Promise<Object>} - Plan details
   */
  async getPlan(planId) {
    try {
      const response = await api.get(`/plan/${planId}`);
      return {
        success: true,
        data: response.data.data.plan
      };
    } catch (error) {
      console.error('[ERROR] Get plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Update/regenerate plan
   * 
   * @param {string} planId - Plan ID
   * @param {Object} updateData - Update data (preferences, start_date, etc.)
   * @returns {Promise<Object>} - Update result
   */
  async updatePlan(planId, updateData) {
    try {
      const response = await api.put(`/plan/${planId}`, updateData);
      return {
        success: true,
        data: response.data.data,
        message: response.data.message
      };
    } catch (error) {
      console.error('[ERROR] Update plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Delete plan
   * 
   * @param {string} planId - Plan ID
   * @returns {Promise<Object>} - Delete result
   */
  async deletePlan(planId) {
    try {
      const response = await api.delete(`/plan/${planId}`);
      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      console.error('[ERROR] Delete plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Poll plan status until completed or failed
   * 
   * @param {string} planId - Plan ID
   * @param {Object} options - Polling options
   * @param {number} options.interval - Polling interval in ms (default: 2000)
   * @param {number} options.maxAttempts - Max polling attempts (default: 60)
   * @param {function} options.onProgress - Progress callback
   * @returns {Promise<Object>} - Final plan data
   */
  async pollPlanStatus(planId, options = {}) {
    const { 
      interval = 2000, 
      maxAttempts = 60,
      onProgress = null 
    } = options;

    let attempts = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        attempts++;
        
        try {
          const result = await this.getPlan(planId);
          
          if (!result.success) {
            reject(new Error(result.error));
            return;
          }

          const plan = result.data;
          
          if (onProgress) {
            onProgress({
              status: plan.status,
              attempts,
              maxAttempts
            });
          }

          if (plan.status === 'completed') {
            resolve({ success: true, data: plan });
            return;
          }

          if (plan.status === 'failed') {
            reject(new Error(plan.error_message || 'Plan generation failed'));
            return;
          }

          if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout: Plan is still processing'));
            return;
          }

          // Continue polling
          setTimeout(poll, interval);
          
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
}

// Export singleton instance
const planAPI = new PlanAPI();
export default planAPI;
