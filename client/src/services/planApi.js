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
      
      // Backend returns data directly in response.data (not nested in data.data)
      return {
        success: true,
        data: response.data,  // Changed from response.data.data
        message: response.data.resultMessage
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
      // Backend returns plans directly in response.data (not nested in data.data)
      // Format: { resultMessage, resultCode, plans, total, page, limit }
      return {
        success: true,
        data: {
          plans: response.data.plans || [],
          total: response.data.total || 0,
          page: response.data.page || 1,
          limit: response.data.limit || 20
        }
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
  async getPlanById(planId) {
    try {
      const response = await api.get(`/plan/${planId}`);
      return {
        success: true,
        data: response.data.plan || response.data.data?.plan || response.data
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
   * Get plan details by ID (legacy alias)
   * 
   * @param {string} planId - Plan ID
   * @returns {Promise<Object>} - Plan details
   */
  async getPlan(planId) {
    return this.getPlanById(planId);
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

  // ========================================
  // TRASH OPERATIONS
  // ========================================

  /**
   * Get list of deleted plans (trash) with pagination
   * Returns BASIC INFO ONLY (no full itinerary)
   * 
   * @param {Object} params - Query parameters
   * @param {number} params.page - Page number (default: 1)
   * @param {number} params.limit - Items per page (default: 20)
   * @returns {Promise<Object>} - Trash plans list with pagination
   */
  async getTrashPlans(params = {}) {
    try {
      const response = await api.get('/plan/trash', { params });
      return {
        success: true,
        data: {
          plans: response.data.plans || [],
          total: response.data.total || 0,
          page: response.data.page || 1,
          limit: response.data.limit || 20
        }
      };
    } catch (error) {
      console.error('[ERROR] Get trash plans failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Restore plan from trash
   * 
   * @param {string} planId - Plan ID
   * @returns {Promise<Object>} - Restore result
   */
  async restorePlan(planId) {
    try {
      const response = await api.post(`/plan/${planId}/restore`);
      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      console.error('[ERROR] Restore plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message
      };
    }
  }

  /**
   * Permanently delete plan from trash
   * 
   * @param {string} planId - Plan ID
   * @returns {Promise<Object>} - Permanent delete result
   */
  async permanentDeletePlan(planId) {
    try {
      const response = await api.delete(`/plan/${planId}/permanent-delete`);
      return {
        success: true,
        message: response.data.message
      };
    } catch (error) {
      console.error('[ERROR] Permanent delete plan failed:', error);
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

  // ========================================
  // SHARING
  // ========================================

  /**
   * Toggle plan sharing (public/private)
   * @param {string} planId
   * @param {boolean} isPublic
   */
  async toggleShare(planId, isPublic) {
    try {
      const response = await api.post(`/plan/${planId}/share`, { is_public: isPublic });
      const payload = response.data?.data || response.data;
      return {
        success: true,
        data: {
          plan_id: payload?.plan_id,
          is_public: payload?.is_public,
          share_token: payload?.share_token,
          share_url: payload?.share_url,
        },
        message: response.data?.resultMessage || response.data?.message,
      };
    } catch (error) {
      console.error('[ERROR] Toggle share failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message,
        errorVi: error.response?.data?.message_vi,
      };
    }
  }

  /**
   * Get public plan by share token (no auth required)
   * @param {string} shareToken
   */
  async getSharedPlan(shareToken) {
    try {
      const response = await api.get(`/plan/shared/${shareToken}`);
      return {
        success: true,
        data: response.data?.plan || response.data?.data?.plan || response.data,
      };
    } catch (error) {
      console.error('[ERROR] Get shared plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.message || error.message,
        errorVi: error.response?.data?.message_vi,
      };
    }
  }

  // ========================================
  // PATCH (NON-CORE UPDATES)
  // ========================================

  /**
   * Partial update plan (non-core fields only)
   * Does NOT trigger AI regeneration
   * 
   * @param {string} planId - Plan ID
   * @param {Object} patchData - Partial update data
   * @param {string} patchData.title - New title
   * @param {string} patchData.thumbnail_url - New thumbnail
   * @param {string} patchData.start_date - New start date (YYYY-MM-DD)
   * @param {number} patchData.estimated_total_cost - User-adjusted cost
   * @param {Array} patchData.itinerary_updates - Day-level updates
   * @returns {Promise<Object>} - Updated plan
   * 
   * @example
   * // Update title and day 1 notes
   * await planAPI.patchPlan('plan_123', {
   *   title: 'My Updated Trip',
   *   itinerary_updates: [
   *     { day: 1, notes: 'Remember sunscreen!' }
   *   ]
   * });
   */
  async patchPlan(planId, patchData) {
    try {
      const response = await api.patch(`/plan/${planId}`, patchData);
      return {
        success: true,
        data: response.data?.data?.plan || response.data?.plan || response.data,
        message: response.data?.resultMessage
      };
    } catch (error) {
      console.error('[ERROR] Patch plan failed:', error);
      return {
        success: false,
        error: error.response?.data?.resultMessage?.en || error.response?.data?.message || error.message,
        errorVi: error.response?.data?.resultMessage?.vn || error.response?.data?.message_vi
      };
    }
  }

  /**
   * Update plan title (convenience method)
   * @param {string} planId
   * @param {string} title
   */
  async updateTitle(planId, title) {
    return this.patchPlan(planId, { title });
  }

  /**
   * Update plan start date (convenience method)
   * @param {string} planId
   * @param {string} startDate - Format: YYYY-MM-DD
   */
  async updateStartDate(planId, startDate) {
    return this.patchPlan(planId, { start_date: startDate });
  }

  /**
   * Update day notes (convenience method)
   * @param {string} planId
   * @param {number} dayNumber - 1-based day number
   * @param {string} notes
   */
  async updateDayNotes(planId, dayNumber, notes) {
    return this.patchPlan(planId, {
      itinerary_updates: [{ day: dayNumber, notes }]
    });
  }

  /**
   * Update day activities (convenience method)
   * @param {string} planId
   * @param {number} dayNumber - 1-based day number
   * @param {Array<string>} activities
   */
  async updateDayActivities(planId, dayNumber, activities) {
    return this.patchPlan(planId, {
      itinerary_updates: [{ day: dayNumber, activities }]
    });
  }

  /**
   * Update day activities and time slots.
   * @param {string} planId
   * @param {number} dayNumber
   * @param {Array} activities
   * @param {Array<string>} estimatedTimes - Format: "HH:MM-HH:MM"
   * @param {Array<string>} poiIds - Optional: List of POI IDs corresponding to activities
   */
  async updateDayActivitiesWithTimes(planId, dayNumber, activities, estimatedTimes, poiIds = null) {
    const update = { day: dayNumber, activities };
    if (typeof estimatedTimes !== 'undefined') {
      update.estimated_times = estimatedTimes;
    }
    if (poiIds) {
      update.poi_ids = poiIds;
    }
    return this.patchPlan(planId, {
      itinerary_updates: [update]
    });
  }

  /**
   * Update day accommodation (convenience method)
   * @param {string} planId
   * @param {number} dayNumber - 1-based day number
   * @param {Object} accommodation
   * @param {string} accommodation.name
   * @param {string} accommodation.address
   * @param {string} accommodation.checkIn - Format: HH:MM
   * @param {string} accommodation.checkOut - Format: HH:MM
   */
  async updateDayAccommodation(planId, dayNumber, accommodation) {
    return this.patchPlan(planId, {
      itinerary_updates: [{
        day: dayNumber,
        accommodation_name: accommodation.name,
        accommodation_address: accommodation.address,
        check_in_time: accommodation.checkIn,
        check_out_time: accommodation.checkOut
      }]
    });
  }
}

// Export singleton instance
const planAPI = new PlanAPI();
export default planAPI;
