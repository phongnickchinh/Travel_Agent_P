"""
Plan Controller - REST API for Travel Plans
============================================

Purpose:
- User endpoints for plan CRUD operations
- Trigger Celery tasks for LLM generation
- Paginated plan listing

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

import logging
from flask import request, jsonify

from . import plan_api
from ...service.planner_service import PlannerService
from ...middleware import JWT_required
from ...core.rate_limiter import rate_limit, get_identifier_from_auth_token
from config import Config
from ...utils.response_helpers import build_success_response, build_error_response
from ...core.di_container import DIContainer
from ...model.mongo.plan import PlanCreateRequest, PlanUpdateRequest, PlanPatchRequest, PlanStatusEnum
from ...utils.sanitization import sanitize_user_input, contains_mongo_operators

# Import Celery task (will create later)
from ...tasks.plan_tasks import generate_plan_task

logger = logging.getLogger(__name__)


class PlanController:
    """
    Controller for travel plan endpoints.
    
    Routes:
    - POST   /api/plan                           Create new plan
    - GET    /api/plan                           List user's plans
    - GET    /api/plan/<plan_id>                 Get plan details
    - PUT    /api/plan/<plan_id>                 Update/regenerate plan
    - DELETE /api/plan/<plan_id>                 Soft delete plan (move to trash)
    
    Trash Management:
    - GET    /api/plan/trash                     List deleted plans
    - POST   /api/plan/<plan_id>/restore         Restore plan from trash
    - DELETE /api/plan/<plan_id>/permanent-delete Permanently delete plan
    
    Plan Sharing:
    - POST   /api/plan/<plan_id>/share           Toggle public sharing
    - GET    /api/plan/shared/<share_token>      Get public plan (no auth)
    """
    
    def __init__(self, planner_service: PlannerService):
        self.planner_service = planner_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        plan_api.add_url_rule("/", "create_plan", self._wrap_jwt_required(self.create_plan), methods=["POST"])
        
        plan_api.add_url_rule("/", "list_plans", self._wrap_jwt_required(self.list_plans), methods=["GET"])
        
        plan_api.add_url_rule("/<plan_id>", "get_plan", self._wrap_jwt_required(self.get_plan), methods=["GET"])
        
        plan_api.add_url_rule("/<plan_id>","update_plan", self._wrap_jwt_required(self.update_plan), methods=["PUT"])
        
        plan_api.add_url_rule("/<plan_id>", "patch_plan", self._wrap_jwt_required(self.patch_plan), methods=["PATCH"])
        
        plan_api.add_url_rule("/<plan_id>", "delete_plan", self._wrap_jwt_required(self.delete_plan), methods=["DELETE"])
        
        # Trash management
        plan_api.add_url_rule("/trash", "list_trash", self._wrap_jwt_required(self.list_trash), methods=["GET"])
        
        plan_api.add_url_rule("/<plan_id>/restore", "restore_plan", self._wrap_jwt_required(self.restore_plan), methods=["POST"])
        
        plan_api.add_url_rule("/<plan_id>/permanent-delete", "permanent_delete_plan", self._wrap_jwt_required(self.permanent_delete_plan), methods=["DELETE"])
        
        # Plan sharing
        plan_api.add_url_rule("/<plan_id>/share", "toggle_sharing", self._wrap_jwt_required(self.toggle_sharing), methods=["POST"])
        
        # Public access (no auth required)
        plan_api.add_url_rule("/shared/<share_token>", "get_shared_plan", self.get_shared_plan, methods=["GET"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware."""
        @JWT_required
        def wrapper(user, *args, **kwargs):
            return f(user, *args, **kwargs)
        return wrapper
    
    @rate_limit(
        max_requests=10000,
        window_seconds=Config.RATE_LIMIT_PLAN_CREATION_WINDOW,
        identifier_func=get_identifier_from_auth_token,
        key_prefix='plan_creation'
    )
    def create_plan(self, user):
        """
        Create new travel plan.
        
        POST /plan
        Body:
        {
            "destination_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "destination_name": "Da Nang",
            "destination_types": ["locality", "political"],
            "num_days": 3,
            "start_date": "2025-06-01",
            "origin": {
                "location": {"lat": 16.0678, "lng": 108.2208},
                "address": "173 Hoang Hoa Tham, Ngoc Ha, Ha Noi",
                "transport_mode": "driving"
            },
            "preferences": {
                "interests": ["beach", "culture", "nightlife"],
                "budget": 5000000
            }
        }
        
        Response:
        {
            "plan_id": "plan_abc123",
            "status": "pending",
            "message": "Plan creation started. Processing in background."
        }
        """
        try:
            data = request.get_json() or {}

            # Sanitize input to avoid NoSQL injection and large payloads
            allowed_keys = [
                "title", 
                "destination_place_id", 
                "destination_name", 
                "destination_types",
                "destination",  # Legacy support
                "num_days", 
                "start_date", 
                "origin", 
                "preferences"
            ]
            sanitized_data = sanitize_user_input(data, allowed_keys)
            if contains_mongo_operators(sanitized_data):
                return build_error_response(
                    "Invalid request payload (forbidden operators).",
                    "Dữ liệu chứa ký tự MongoDB không hợp lệ.",
                    "40004",
                    400
                )
            
            # Validate request
            try:
                plan_request = PlanCreateRequest(**sanitized_data)
            except Exception as e:
                return build_error_response(
                    "Invalid request payload.",
                    f"Dữ liệu yêu cầu không hợp lệ: {str(e)}",
                    "40001",
                    400
                )
            
            # Create plan (PENDING status)
            plan = self.planner_service.create_plan(user.id, plan_request)
            
            # Trigger Celery task for LLM generation
            generate_plan_task.delay(plan['plan_id'])
            
            logger.info(f"[INFO] Plan {plan['plan_id']} created for user {user.id}")
            
            return build_success_response(
                "Plan creation started. Processing in background.",
                "Đã bắt đầu tạo kế hoạch. Đang xử lý trong nền.",
                "20001",
                {
                    "plan_id": plan['plan_id'],
                    "status": plan['status'],
                    "destination": plan['destination'],
                    "num_days": plan['num_days']
                },
                201
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to create plan: {e}")
            return build_error_response(
                "Failed to create plan.",
                f"Không thể tạo kế hoạch: {str(e)}",
                "50001",
                500
            )
    
    def list_plans(self, user):
        """
        List user's plans with pagination.
        
        GET /plan?page=1&limit=20&status=completed
        
        Response:
        {
            "plans": [...],
            "total": 15,
            "page": 1,
            "limit": 20
        }
        """
        try:
            # Get query params
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            status_str = request.args.get('status')
            
            # Parse status
            status = None
            if status_str:
                try:
                    status = PlanStatusEnum(status_str.lower())
                except ValueError:
                    pass
            
            # Calculate skip
            skip = (page - 1) * limit
            
            # Get plans
            plans = self.planner_service.get_user_plans(
                user_id=user.id,
                skip=skip,
                limit=limit,
                status=status
            )
            
            # Get total count
            total = self.planner_service.count_user_plans(user.id, status)
            
            return build_success_response(
                "Plans retrieved successfully.",
                "Đã lấy danh sách kế hoạch thành công.",
                "20002",
                {
                    "plans": plans,
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to list plans: {e}")
            return build_error_response(
                "Failed to retrieve plans.",
                f"Không thể lấy danh sách kế hoạch: {str(e)}",
                "50002",
                500
            )
    
    def get_plan(self, user, plan_id: str):
        """
        Get plan details by ID.
        
        GET /plan/<plan_id>
        
        Response:
        {
            "plan_id": "plan_abc123",
            "destination": "Da Nang",
            "num_days": 3,
            "status": "completed",
            "itinerary": [...]
        }
        """
        try:
            plan = self.planner_service.get_plan(plan_id)
            
            if not plan:
                return build_error_response(
                    "Plan not found.",
                    "Không tìm thấy kế hoạch.",
                    "40401",
                    404
                )
            
            # Verify ownership
            if plan['user_id'] != user.id:
                return build_error_response(
                    "Unauthorized access.",
                    "Không có quyền truy cập kế hoạch này.",
                    "40301",
                    403
                )
            
            return build_success_response(
                "Plan details retrieved successfully.",
                "Đã lấy chi tiết kế hoạch thành công.",
                "20003",
                {"plan": plan}
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get plan {plan_id}: {e}")
            return build_error_response(
                "Failed to retrieve plan.",
                f"Không thể lấy kế hoạch: {str(e)}",
                "50003",
                500
            )
    
    @rate_limit(
        max_requests=Config.RATE_LIMIT_PLAN_CREATION,
        window_seconds=Config.RATE_LIMIT_PLAN_CREATION_WINDOW,
        identifier_func=get_identifier_from_auth_token,
        key_prefix='plan_regeneration'
    )
    def update_plan(self, user, plan_id: str):
        """
        Update/regenerate plan with new preferences.
        
        PUT /plan/<plan_id>
        Body:
        {
            "preferences": {
                "interests": ["adventure", "nightlife"],
                "budget": "high"
            }
        }
        
        Response:
        {
            "message": "Plan regeneration started.",
            "plan_id": "plan_abc123",
            "status": "pending"
        }
        """
        try:
            data = request.get_json() or {}
            allowed_keys = ["title", "preferences", "start_date", "origin"]
            sanitized_data = sanitize_user_input(data, allowed_keys)
            if contains_mongo_operators(sanitized_data):
                return build_error_response(
                    "Invalid request payload (forbidden operators).",
                    "Dữ liệu chứa ký tự MongoDB không hợp lệ.",
                    "40005",
                    400
                )
            
            # Validate request
            try:
                update_request = PlanUpdateRequest(**sanitized_data)
            except Exception as e:
                return build_error_response(
                    "Invalid request payload.",
                    f"Dữ liệu yêu cầu không hợp lệ: {str(e)}",
                    "40002",
                    400
                )
            
            # Regenerate plan
            success = self.planner_service.regenerate_plan(plan_id, user.id, update_request)
            
            if not success:
                return build_error_response(
                    "Failed to regenerate plan.",
                    "Không thể tạo lại kế hoạch.",
                    "50004",
                    500
                )
            
            # Trigger Celery task
            generate_plan_task.delay(plan_id)
            
            return build_success_response(
                "Plan regeneration started.",
                "Đã bắt đầu tạo lại kế hoạch.",
                "20004",
                {
                    "plan_id": plan_id,
                    "status": "pending"
                }
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to update plan {plan_id}: {e}")
            return build_error_response(
                "Failed to update plan.",
                f"Không thể cập nhật kế hoạch: {str(e)}",
                "50005",
                500
            )
    
    def delete_plan(self, user, plan_id: str):
        """
        Soft delete plan (move to trash).
        
        DELETE /plan/<plan_id>
        
        Response:
        {
            "message": "Plan moved to trash successfully."
        }
        """
        try:
            success = self.planner_service.delete_plan(plan_id, user.id)
            
            if not success:
                return build_error_response(
                    "Plan not found or unauthorized.",
                    "Không tìm thấy kế hoạch hoặc không có quyền xóa.",
                    "40402",
                    404
                )
            
            return build_success_response(
                "Plan moved to trash successfully.",
                "Đã chuyển kế hoạch vào thùng rác thành công.",
                "20005"
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete plan {plan_id}: {e}")
            return build_error_response(
                "Failed to delete plan.",
                f"Không thể xóa kế hoạch: {str(e)}",
                "50006",
                500
            )

    def patch_plan(self, user, plan_id: str):
        """
        Partial update plan (non-core fields only).
        Does NOT trigger regeneration.
        
        PATCH /plan/<plan_id>
        Body:
        {
            "title": "My Updated Title",
            "start_date": "2026-02-01",
            "itinerary_updates": [
                {"day": 1, "notes": "Custom note for day 1"},
                {"day": 2, "activities": ["Morning yoga", "Beach visit"]}
            ]
        }
        
        Editable fields:
        - Plan level: title, thumbnail_url, start_date, estimated_total_cost
        - Day level: notes, activities, estimated_times, estimated_cost_vnd, 
                     accommodation_name, accommodation_address, check_in_time, check_out_time
        
        Response:
        {
            "plan": { ... updated plan ... }
        }
        """
        try:
            data = request.get_json() or {}
            
            # Allowed keys for PATCH (non-core fields)
            allowed_keys = [
                "title", 
                "thumbnail_url", 
                "start_date", 
                "estimated_total_cost",
                "itinerary_updates"
            ]
            sanitized_data = sanitize_user_input(data, allowed_keys)
            
            if contains_mongo_operators(sanitized_data):
                return build_error_response(
                    "Invalid request payload (forbidden operators).",
                    "Dữ liệu chứa ký tự MongoDB không hợp lệ.",
                    "40006",
                    400
                )
            
            # Validate with PlanPatchRequest
            try:
                patch_request = PlanPatchRequest(**sanitized_data)
            except Exception as e:
                return build_error_response(
                    "Invalid request payload.",
                    f"Dữ liệu yêu cầu không hợp lệ: {str(e)}",
                    "40007",
                    400
                )
            
            # Call service
            updated_plan = self.planner_service.patch_plan(
                plan_id, user.id, patch_request
            )
            
            if not updated_plan:
                return build_error_response(
                    "Plan not found or unauthorized.",
                    "Không tìm thấy kế hoạch hoặc không có quyền chỉnh sửa.",
                    "40407",
                    404
                )
            
            logger.info(f"[INFO] Plan {plan_id} patched by user {user.id}")
            
            return build_success_response(
                "Plan updated successfully.",
                "Đã cập nhật kế hoạch thành công.",
                "20012",
                {"plan": updated_plan}
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to patch plan {plan_id}: {e}")
            return build_error_response(
                "Failed to update plan.",
                f"Không thể cập nhật kế hoạch: {str(e)}",
                "50012",
                500
            )


    # ============================================
    # TRASH MANAGEMENT
    # ============================================
    
    def list_trash(self, user):
        """
        List user's deleted plans (trash) with pagination.
        
        GET /plan/trash?page=1&limit=20
        
        Response:
        {
            "plans": [...],
            "total": 5,
            "page": 1,
            "limit": 20
        }
        """
        try:
            # Get query params
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            
            # Get trash plans
            result = self.planner_service.get_trash_plans(user.id, page, limit)
            
            return build_success_response(
                "Trash plans retrieved successfully.",
                "Đã lấy danh sách thùng rác thành công.",
                "20007",
                result
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to list trash: {e}")
            return build_error_response(
                "Failed to retrieve trash plans.",
                f"Không thể lấy danh sách thùng rác: {str(e)}",
                "50007",
                500
            )
    
    def restore_plan(self, user, plan_id: str):
        """
        Restore plan from trash.
        
        POST /plan/<plan_id>/restore
        
        Response:
        {
            "message": "Plan restored successfully."
        }
        """
        try:
            success = self.planner_service.restore_plan(plan_id, user.id)
            
            if not success:
                return build_error_response(
                    "Plan not found in trash or unauthorized.",
                    "Không tìm thấy kế hoạch trong thùng rác hoặc không có quyền khôi phục.",
                    "40403",
                    404
                )
            
            return build_success_response(
                "Plan restored successfully.",
                "Đã khôi phục kế hoạch thành công.",
                "20008"
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to restore plan {plan_id}: {e}")
            return build_error_response(
                "Failed to restore plan.",
                f"Không thể khôi phục kế hoạch: {str(e)}",
                "50008",
                500
            )
    
    def permanent_delete_plan(self, user, plan_id: str):
        """
        Permanently delete plan from trash.
        
        DELETE /plan/<plan_id>/permanent-delete
        
        Response:
        {
            "message": "Plan permanently deleted."
        }
        """
        try:
            success = self.planner_service.permanent_delete_plan(plan_id, user.id)
            
            if not success:
                return build_error_response(
                    "Plan not found in trash or unauthorized.",
                    "Không tìm thấy kế hoạch trong thùng rác hoặc không có quyền xóa vĩnh viễn.",
                    "40404",
                    404
                )
            
            return build_success_response(
                "Plan permanently deleted.",
                "Đã xóa vĩnh viễn kế hoạch.",
                "20009"
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to permanently delete plan {plan_id}: {e}")
            return build_error_response(
                "Failed to permanently delete plan.",
                f"Không thể xóa vĩnh viễn kế hoạch: {str(e)}",
                "50009",
                500
            )
    
    # ============================================
    # PLAN SHARING
    # ============================================
    
    def toggle_sharing(self, user, plan_id: str):
        """
        Toggle plan public sharing.
        
        POST /plan/<plan_id>/share
        Body:
        {
            "is_public": true
        }
        
        Response:
        {
            "message": "Plan sharing updated.",
            "plan": {
                "plan_id": "plan_abc123",
                "is_public": true,
                "share_token": "xyz123...",
                "share_url": "http://localhost:5173/shared/xyz123..."
            }
        }
        """
        try:
            data = request.get_json() or {}
            is_public = data.get('is_public', False)
            
            if not isinstance(is_public, bool):
                return build_error_response(
                    "Invalid is_public value.",
                    "Giá trị is_public không hợp lệ.",
                    "40003",
                    400
                )
            
            # Toggle sharing
            updated_plan = self.planner_service.toggle_plan_sharing(plan_id, user.id, is_public)
            
            if not updated_plan:
                return build_error_response(
                    "Plan not found or unauthorized.",
                    "Không tìm thấy kế hoạch hoặc không có quyền chia sẻ.",
                    "40405",
                    404
                )
            
            # Build share URL if public
            share_url = None
            if is_public and updated_plan.get('share_token'):
                # You can configure this base URL from config
                share_url = f"http://localhost:5173/shared/{updated_plan['share_token']}"
            
            return build_success_response(
                "Plan sharing updated successfully.",
                "Đã cập nhật chia sẻ kế hoạch thành công.",
                "20010",
                {
                    "plan_id": updated_plan['plan_id'],
                    "is_public": updated_plan['is_public'],
                    "share_token": updated_plan.get('share_token'),
                    "share_url": share_url
                }
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to toggle sharing for plan {plan_id}: {e}")
            return build_error_response(
                "Failed to update plan sharing.",
                f"Không thể cập nhật chia sẻ kế hoạch: {str(e)}",
                "50010",
                500
            )
    
    def get_shared_plan(self, share_token: str):
        """
        Get public plan by share token (no authentication required).
        
        GET /plan/shared/<share_token>
        
        Response:
        {
            "plan": {
                "plan_id": "plan_abc123",
                "destination": "Da Nang",
                "num_days": 3,
                "itinerary": [...]
            }
        }
        """
        try:
            plan = self.planner_service.get_public_plan(share_token)
            
            if not plan:
                return build_error_response(
                    "Shared plan not found or no longer public.",
                    "Không tìm thấy kế hoạch chia sẻ hoặc đã không còn công khai.",
                    "40406",
                    404
                )
            
            # Remove sensitive fields, keep the full plan structure for frontend parity
            safe_plan = {
                k: v
                for k, v in plan.items()
                if k not in {"user_id", "is_deleted", "is_public"}
            }
            
            return build_success_response(
                "Shared plan retrieved successfully.",
                "Đã lấy kế hoạch chia sẻ thành công.",
                "20011",
                {"plan": safe_plan}
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get shared plan {share_token}: {e}")
            return build_error_response(
                "Failed to retrieve shared plan.",
                f"Không thể lấy kế hoạch chia sẻ: {str(e)}",
                "50011",
                500
            )


# Create the controller instance
def init_plan_controller():
    container = DIContainer.get_instance()
    planner_service = container.resolve(PlannerService.__name__)
    return PlanController(planner_service)
