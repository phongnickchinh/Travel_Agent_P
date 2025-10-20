# One Email = One Account Policy

## Tổng quan

Hệ thống đảm bảo **1 email chỉ tương ứng với 1 tài khoản duy nhất**.

Một tài khoản có thể có nhiều phương thức đăng nhập:
- `'local'`: Chỉ có password
- `'google'`: Chỉ có Google OAuth  
- `'both'`: Có cả password và Google OAuth

## Cách hoạt động

### Scenario 1: User register bằng email/password, sau đó login Google

```
Trước:
- email: user@example.com
- password_hash: ✓
- google_id: null
- auth_provider: 'local'

User login Google với cùng email → Tự động link

Sau:
- email: user@example.com
- password_hash: ✓ (giữ nguyên)
- google_id: "123456..."
- auth_provider: 'both'

→ User có thể login bằng cả password VÀ Google
```

### Scenario 2: User login Google lần đầu, sau đó set password

```
Trước:
- email: user@example.com  
- password_hash: null
- google_id: "123456..."
- auth_provider: 'google'

User set password → Tự động update

Sau:
- email: user@example.com
- password_hash: ✓ (mới set)
- google_id: "123456..."
- auth_provider: 'both'

→ User có thể login bằng cả Google VÀ password
```

### Scenario 3: Google-only user cố login bằng password

```
User:
- auth_provider: 'google'
- password_hash: null

POST /auth/login với password
→ REJECTED (401)
→ Lý do: user.has_local_auth() = False
```

## API Behavior

### POST /auth/login (Email + Password)
- Chỉ accept nếu `auth_provider` in ['local', 'both']
- Reject nếu `auth_provider = 'google'` (Google-only)

### POST /auth/google (Google OAuth)
- Tự động link nếu email đã tồn tại
- Update `auth_provider` dựa vào password:
  - Có password → 'both'
  - Không có password → 'google'

### POST /auth/link-google (Link Google thủ công)
- Update `auth_provider` dựa vào password:
  - Có password → 'both'
  - Không có password → 'google'

### POST /auth/reset-password (Set password)
- Nếu có `google_id` → Update auth_provider thành 'both'

## Helper Methods

```python
user.has_local_auth()   # True nếu có password và auth_provider in ['local', 'both']
user.has_google_auth()  # True nếu có google_id và auth_provider in ['google', 'both']
user.check_password()   # Return False nếu password_hash is None
```

## Database Migration

```bash
cd server
flask db migrate -m "Support both auth methods"
flask db upgrade
```

Migration sẽ update existing users:
```sql
UPDATE users 
SET auth_provider = CASE
    WHEN password_hash IS NOT NULL AND google_id IS NOT NULL THEN 'both'
    WHEN password_hash IS NOT NULL AND google_id IS NULL THEN 'local'
    WHEN password_hash IS NULL AND google_id IS NOT NULL THEN 'google'
    ELSE 'local'
END;
```

## Testing

```bash
# Test 1: Register → Google login (auto-link)
POST /auth/register → auth_provider='local'
POST /auth/google (same email) → auth_provider='both'

# Test 2: Google login → Set password  
POST /auth/google → auth_provider='google'
POST /auth/reset-password → auth_provider='both'

# Test 3: Google-only user login with password (should fail)
Given: auth_provider='google', password_hash=null
POST /auth/login → 401 Unauthorized
```

## Files Changed

1. `server/app/model/user.py`
   - auth_provider comment: 'local', 'google', or 'both'
   - Added: has_local_auth(), has_google_auth()
   - Updated: check_password() to handle null

2. `server/app/service/auth_service.py`
   - validate_login(): Check has_local_auth()
   - authenticate_google_user(): Auto-update auth_provider
   - link_google_account(): Auto-update auth_provider
   - set_password(): Auto-update auth_provider to 'both'
