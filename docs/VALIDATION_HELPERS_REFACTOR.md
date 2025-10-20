# Validation Helpers Refactoring

## Problem
The `get_json_or_error()` function in `server/app/utils/validation_helpers.py` was importing and using Flask's `request` object directly from the global context. This caused a `NameError: name 'request' is not defined` in certain runtime scenarios where the Flask request context was not available.

## Solution
Refactored `get_json_or_error()` to accept the `request` object as an explicit parameter instead of relying on Flask's context-dependent import.

## Changes Made

### 1. validation_helpers.py
**Before:**
```python
from flask import request, jsonify

def get_json_or_error():
    if not request.is_json:
        return None, build_error_response(...)
    return request.get_json(), None
```

**After:**
```python
from flask import jsonify

def get_json_or_error(request):
    if not request.is_json:
        return None, build_error_response(...)
    return request.get_json(), None
```

### 2. auth_controller.py
Updated **10 methods** to pass the `request` parameter:

1. ✅ `login()` - Line 47
2. ✅ `google_login()` - Line 84
3. ✅ `link_google()` - Line 124
4. ✅ `refresh_token()` - Line 156
5. ✅ `register()` - Line 205
6. ✅ `send_verification_code()` - Line 261
7. ✅ `verify_email()` - Line 306
8. ✅ `request_reset_password()` - Line 335
9. ✅ `validate_reset_code()` - Line 373
10. ✅ `reset_password()` - Line 398

**Pattern Applied:**
```python
# Before
data, error = get_json_or_error()

# After
data, error = get_json_or_error(request)
```

## Verification
- ✅ No remaining calls to `get_json_or_error()` without parameter
- ✅ No syntax errors detected
- ✅ All controller methods updated consistently

## Benefits
1. **Explicit Dependencies**: The `request` dependency is now explicit rather than implicit
2. **Better Testability**: Easier to test by passing mock request objects
3. **No Context Issues**: Eliminates Flask request context availability problems
4. **Cleaner Code**: Follows explicit-is-better-than-implicit principle

## Testing Checklist
- [ ] Test all authentication endpoints still work correctly
- [ ] Verify error messages are returned properly
- [ ] Confirm bilingual error messages work
- [ ] Test with invalid JSON payloads
- [ ] Test with missing required fields

## Related Files
- `server/app/utils/validation_helpers.py` - Helper function definition
- `server/app/controller/auth/auth_controller.py` - All method calls updated

## Date
Created: December 2024
