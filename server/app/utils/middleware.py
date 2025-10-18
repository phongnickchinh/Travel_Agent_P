from functools import wraps
from flask import jsonify, request


from functools import wraps
from inspect import signature
import jwt

from flask import request, jsonify

from config import secret_key
from  ..repo.implements.user_repository import UserRepository


def JWT_required(f):
    """Decorator to require JSON Web Token for API access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "resultMessage": {
                    "en": "Access denied. No token provided.",
                    "vn": "Truy cập bị từ chối. Không có token được cung cấp."
                },
                "resultCode": "00006"
            }), 401
        
        auth_header_parts = auth_header.split(" ")
        if len(auth_header_parts) != 2 or not auth_header_parts[1]:
            return jsonify({
                "resultMessage": {
                    "en": "Access denied. No token provided.",
                    "vn": "Truy cập bị từ chối. Không có token được cung cấp."
                },
                "resultCode": "00006"
            }), 401
            
        token = auth_header_parts[1]
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 401
            
        user_id = payload.get("user_id")
        if not user_id:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 401
            
        user_repository = UserRepository()
        user = user_repository.get_user_by_id(user_id)
        if not user:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 401
            
        func_signature = signature(f)
        if "user_id" in func_signature.parameters:
            return f(user_id, *args, **kwargs)
        elif "user" in func_signature.parameters:
            return f(user, *args, **kwargs)
        
        return f(*args, **kwargs)

    return decorated_function


def validate_fields(allow_fields):
    """Decorator to validate fields in request JSON data."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Lấy dữ liệu từ request
            data = request.get_json() or {}

            # Kiểm tra các trường bắt buộc có giá trị hay không
            missing_fields = {field for field in allow_fields if not data.get(field)}
            if missing_fields:
                return jsonify({
                    "resultMessage": {
                        "en": "Please provide all required fields!",
                        "vn": "Vui lòng cung đầy đủ các trường bắt buộc!"
                    },
                    "resultCode": "00099"
                }), 400

            # Nếu tất cả hợp lệ, gọi hàm gốc
            return func(*args, **kwargs)
        return wrapper
    return decorator


# def check_item_ownership(f):
#     '''Decorator to check if the user has access to the fridge item'''
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         group_id = kwargs.get('group_id') or request.view_args.get('group_id')
#         try:
#             data = request.json
#         except:
#             data = {}
#         item_id = data.get("itemId") or kwargs.get('item_id') or request.view_args.get('item_id')

#         # Kiểm tra nếu thiếu thông tin cần thiết
#         if not item_id:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Missing itemId in the request.",
#                     "vn": "Thiếu itemId trong yêu cầu."
#                 },
#                 "resultCode": "00234"
#             }), 400

#         # Truy vấn để kiểm tra quyền sở hữu
#         fridge_item = db.session.query(FridgeItem).filter_by(id=item_id, owner_id=group_id).first()

#         if not fridge_item:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "You do not have access to this fridge item.",
#                     "vn": "Bạn không có quyền truy cập mục này trong tủ lạnh."
#                 },
#                 "resultCode": "00235"
#             }), 403

#         return f(*args, **kwargs)
#     return decorated_function


# from functools import wraps
# from flask import jsonify, request

# def check_list_ownership(f):
#     ''''Decorator to check if user has access to the shopping list'''
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         group_id = kwargs.get('group_id') or request.view_args.get('group_id')
#         print(request)
#         try:
#             data = request.json
#             list_id = data.get("list_id")
#         except:
#             list_id = kwargs.get('list_id') or request.args.get("list_id")

#         # Kiểm tra nếu thiếu list_id trong yêu cầu
#         if not list_id:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Missing list_id in the request.",
#                     "vn": "Thiếu list_id trong yêu cầu."
#                 },
#                 "resultCode": "00247"
#             }), 400

#         # Truy vấn để kiểm tra quyền sở hữu
#         shopping_list = db.session.query(ShoppingList).filter_by(id=list_id, group_id=group_id).first()

#         # Nếu shopping_list không tồn tại hoặc không thuộc group
#         if not shopping_list:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Shopping list does not belong to this group.",
#                     "vn": "Danh sách mua sắm không thuộc nhóm này."
#                 },
#                 "resultCode": "00248"
#             }), 403

#         return f(*args, **kwargs)
#     return decorated_function


# def check_task_ownership(f):
#     '''Decorator to check if the task belongs to the group'''
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         group_id = kwargs.get('group_id')  # Lấy group_id từ URL
#         data = request.json
#         task_id = data.get("task_id")  

#         # Kiểm tra nếu thiếu task_id trong yêu cầu
#         if not task_id:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Missing task_id in the request.",
#                     "vn": "Thiếu task_id trong yêu cầu."
#                 },
#                 "resultCode": "00292"
#             }), 400

#         # Truy vấn để kiểm tra quyền sở hữu
#         task = db.session.query(ShoppingTask).join(ShoppingList).filter(
#             ShoppingTask.id == task_id,
#             ShoppingList.group_id == group_id
#         ).first()

#         # Nếu task không tồn tại hoặc không thuộc nhóm
#         if not task:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Task does not belong to this group.",
#                     "vn": "Nhiệm vụ không thuộc nhóm này."
#                 },
#                 "resultCode": "00293"
#             }), 403

#         return f(*args, **kwargs)
#     return decorated_function


# def check_recipe_ownership(f):
#     '''Decorator to check if the recipe belongs to the group'''
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         group_id = kwargs.get('group_id') or request.view_args.get('group_id')
#         try:
#             data = request.json
#         except:
#             data = {}
#         try:
#             form_data = request.form
#         except:
#             form_data = {}
#         recipe_id = kwargs.get('recipe_id') or request.view_args.get('recipe_id') or data.get('recipe_id') or form_data.get('recipe_id')

#         # Kiểm tra nếu thiếu recipe_id trong yêu cầu
#         if not recipe_id:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Missing recipe_id in the request.",
#                     "vn": "Thiếu recipe_id trong yêu cầu."
#                 },
#                 "resultCode": "00298"
#             }), 400

#         # Truy vấn để kiểm tra quyền sở hữu
#         recipe = db.session.query(Recipe).filter_by(id=recipe_id, group_id=group_id).first()

#         # Nếu recipe không tồn tại hoặc không thuộc nhóm
#         if not recipe:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Recipe does not belong to this group.",
#                     "vn": "Công thức không thuộc nhóm này."
#                 },
#                 "resultCode": "00299"
#             }), 403

#         return f(*args, **kwargs)
#     return decorated_function


# def check_meal_plan_ownership(f):
#     '''Decorator to check if the meal plan belongs to the group'''
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         group_id = kwargs.get('group_id') or request.view_args.get('group_id')
#         try:
#             data = request.json
#         except:
#             data = {}
#         meal_id = data.get("meal_id") or kwargs.get('meal_id') or request.view_args.get('meal_id')

#         # Kiểm tra nếu thiếu meal_plan_id trong yêu cầu
#         if not meal_id:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "Missing meal_id in the request.",
#                     "vn": "Thiếu ID kế hoạch bữa ăn trong yêu cầu."
#                 },
#                 "resultCode": "00300"
#             }), 400

#         # Truy vấn để kiểm tra quyền sở hữu
#         meal_plan = db.session.query(MealPlan).filter_by(id=meal_id, group_id=group_id, is_deleted=False).first()

#         # Nếu meal_plan không tồn tại hoặc không thuộc nhóm
#         if not meal_plan:
#             return jsonify({
#                 "resultMessage": {
#                     "en": "You do not have access to this meal plan.",
#                     "vn": "Bạn không có quyền truy cập kế hoạch ăn này."
#                 },
#                 "resultCode": "00301"
#             }), 403

#         return f(*args, **kwargs)
#     return decorated_function