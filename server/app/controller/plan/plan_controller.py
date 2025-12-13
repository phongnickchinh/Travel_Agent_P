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
from ...model.mongo.plan import PlanCreateRequest, PlanUpdateRequest, PlanStatusEnum
from ...utils.sanitization import sanitize_user_input, contains_mongo_operators

# Import Celery task (will create later)
from ...tasks.plan_tasks import generate_plan_task

logger = logging.getLogger(__name__)


class PlanController:
    """
    Controller for travel plan endpoints.
    
    Routes:
    - POST   /api/plan              Create new plan
    - GET    /api/plan              List user's plans
    - GET    /api/plan/<plan_id>    Get plan details
    - PUT    /api/plan/<plan_id>    Update/regenerate plan
    - DELETE /api/plan/<plan_id>    Delete plan
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
        
        plan_api.add_url_rule("/<plan_id>", "delete_plan", self._wrap_jwt_required(self.delete_plan), methods=["DELETE"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware."""
        @JWT_required
        def wrapper(user, *args, **kwargs):
            return f(user, *args, **kwargs)
        return wrapper
    
    @rate_limit(
        max_requests=Config.RATE_LIMIT_PLAN_CREATION,
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
            "destination": "Da Nang",
            "num_days": 3,
            "start_date": "2025-06-01",
            "origin": {
                "location": {"lat":, "lng": },
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
            allowed_keys = ["title", "destination", "num_days", "start_date", "origin", "preferences"]
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
        Delete plan.
        
        DELETE /plan/<plan_id>
        
        Response:
        {
            "message": "Plan deleted successfully."
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
                "Plan deleted successfully.",
                "Đã xóa kế hoạch thành công.",
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


# Create the controller instance
def init_plan_controller():
    container = DIContainer.get_instance()
    planner_service = container.resolve(PlannerService.__name__)
    return PlanController(planner_service)
