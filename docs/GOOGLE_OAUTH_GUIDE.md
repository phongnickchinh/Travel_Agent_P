# Google OAuth Integration Guide

## Tổng quan

Hệ thống đã được tích hợp Google OAuth để cho phép người dùng đăng nhập bằng tài khoản Google của họ.

## Các thay đổi đã thực hiện

### 1. Model Layer (User Model)
- ✅ Thêm trường `google_id` (String, unique, nullable, indexed) - ID duy nhất từ Google
- ✅ Thêm trường `auth_provider` (String, default='local') - Loại xác thực: 'local' hoặc 'google'
- ✅ Thêm trường `profile_picture` (String, nullable) - URL ảnh đại diện từ Google
- ✅ Cập nhật `password_hash` thành nullable để cho phép người dùng OAuth không có password
- ✅ Cập nhật `__init__` method để hỗ trợ tạo user từ Google OAuth

### 2. Repository Layer
**User Repository Interface (`user_interface.py`)**
- ✅ `get_user_by_google_id(google_id)` - Tìm user theo Google ID
- ✅ `create_google_user(email, name, google_id, profile_picture, language)` - Tạo user mới từ Google
- ✅ `update_google_profile(user, name, profile_picture)` - Cập nhật thông tin Google profile

**User Repository Implementation (`user_repository.py`)**
- ✅ Implement tất cả các method trên
- ✅ Tự động generate username từ email
- ✅ Tự động generate device_id cho OAuth users
- ✅ Tự động set `is_verified=True` cho Google users

### 3. Service Layer (Auth Service)
- ✅ `authenticate_google_user(google_token)` - Xác thực user với Google token
  - Verify Google token
  - Tạo user mới nếu chưa tồn tại
  - Link với local account nếu email đã tồn tại
  - Generate access & refresh tokens
- ✅ `link_google_account(user_id, google_token)` - Liên kết Google account với tài khoản hiện tại

### 4. Utility Layer
**Google OAuth Helper (`google_oauth_helper.py`)**
- ✅ `verify_google_token(token)` - Verify Google ID token và trả về user info
- ✅ `get_google_user_info(token)` - Lấy thông tin user từ Google access token (alternative method)
- ✅ `generate_username_from_email(email)` - Tạo username từ email
- ✅ `generate_device_id_for_oauth()` - Tạo device ID cho OAuth users

### 5. Controller Layer (Auth Controller)
- ✅ POST `/auth/google` - Đăng nhập bằng Google
- ✅ POST `/auth/link-google` - Liên kết tài khoản Google (requires JWT)

### 6. Configuration
**Config (`config.py`)**
- ✅ Thêm `GOOGLE_CLIENT_ID` từ environment variable
- ✅ Thêm `GOOGLE_CLIENT_SECRET` từ environment variable

## Cấu hình Environment Variables

Thêm vào file `.env`:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Hướng dẫn lấy Google OAuth Credentials

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới hoặc chọn project hiện có
3. Vào "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Chọn "Web application"
6. Thêm authorized redirect URIs (nếu cần)
7. Copy `Client ID` và `Client Secret` vào file `.env`

## API Endpoints

### 1. Đăng nhập bằng Google
```http
POST /auth/google
Content-Type: application/json

{
  "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

**Success Response (200):**
```json
{
  "result_code": "00091",
  "message_en": "You have successfully logged in with Google.",
  "message_vi": "Bạn đã đăng nhập thành công bằng Google.",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@gmail.com",
      "name": "User Name",
      "username": "user_1234",
      "google_id": "108765432109876543210",
      "auth_provider": "google",
      "profile_picture": "https://lh3.googleusercontent.com/...",
      "is_verified": true,
      "language": "en",
      "created_at": "2025-10-19T10:00:00Z"
    },
    "role": "user",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
  }
}
```

**Error Response (400):**
```json
{
  "result_code": "00090",
  "message_en": "Google authentication failed. Please try again.",
  "message_vi": "Xác thực Google thất bại. Vui lòng thử lại."
}
```

### 2. Liên kết tài khoản Google
```http
POST /auth/link-google
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

**Success Response (200):**
```json
{
  "result_code": "00093",
  "message_en": "Google account linked successfully.",
  "message_vi": "Liên kết tài khoản Google thành công.",
  "data": {
    "message": "Google account linked successfully"
  }
}
```

**Error Response (400):**
```json
{
  "result_code": "00094",
  "message_en": "This Google account is already linked to another account",
  "message_vi": "Liên kết tài khoản Google thất bại."
}
```

## Database Migration

Chạy lệnh sau để tạo và áp dụng migration:

```bash
# Tạo migration file
cd server
python -m flask db migrate -m "Add Google OAuth fields to User model"

# Áp dụng migration
python -m flask db upgrade
```

## Testing với Postman/Thunder Client

### Test Flow 1: Đăng nhập lần đầu với Google

1. Lấy Google ID token từ frontend (sau khi user đăng nhập Google)
2. Gửi POST request đến `/auth/google` với `google_token`
3. Hệ thống sẽ:
   - Verify token với Google
   - Tạo user mới với thông tin từ Google
   - Assign role "user" mặc định
   - Trả về access_token và refresh_token

### Test Flow 2: Liên kết Google với tài khoản hiện tại

1. Đăng nhập bằng local account (email + password)
2. Lấy access_token
3. Gửi POST request đến `/auth/link-google` với:
   - Header: `Authorization: Bearer <access_token>`
   - Body: `{"google_token": "..."}`
4. Hệ thống sẽ liên kết Google ID với tài khoản hiện tại

### Test Flow 3: Đăng nhập với Google khi đã có tài khoản

1. User đã có tài khoản với email từ Google
2. Gửi POST request đến `/auth/google`
3. Hệ thống tự động link Google account với local account
4. Trả về tokens

## Security Notes

- ✅ Google tokens được verify với Google servers trước khi sử dụng
- ✅ Email phải được verified bởi Google (`email_verified: true`)
- ✅ Google ID được index để tăng performance
- ✅ Không cho phép link một Google account với nhiều tài khoản
- ✅ OAuth users được tự động verified (`is_verified: true`)
- ✅ Password là optional cho OAuth users

## Error Codes

| Code | Description |
|------|-------------|
| 00090 | Google authentication failed |
| 00091 | Google login successful |
| 00092 | Error during Google authentication |
| 00093 | Google account linked successfully |
| 00094 | Google account linking failed |
| 00095 | Error while linking Google account |

## Frontend Integration Example

```javascript
// 1. User clicks "Login with Google" button
// 2. Use Google Sign-In library to get ID token

// Google Sign-In initialization
google.accounts.id.initialize({
  client_id: 'YOUR_GOOGLE_CLIENT_ID',
  callback: handleCredentialResponse
});

// Handle Google response
function handleCredentialResponse(response) {
  const googleToken = response.credential; // This is the ID token
  
  // Send to backend
  fetch('http://your-api.com/auth/google', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      google_token: googleToken
    })
  })
  .then(res => res.json())
  .then(data => {
    // Save tokens to localStorage/sessionStorage
    localStorage.setItem('access_token', data.data.access_token);
    localStorage.setItem('refresh_token', data.data.refresh_token);
    
    // Redirect to dashboard
    window.location.href = '/dashboard';
  })
  .catch(error => {
    console.error('Login failed:', error);
  });
}
```

## Troubleshooting

### Issue: "Invalid Google token"
- **Solution**: Đảm bảo GOOGLE_CLIENT_ID trong `.env` khớp với client ID trong Google Console
- **Solution**: Token có thể đã hết hạn, yêu cầu user đăng nhập lại

### Issue: "This Google account is already linked to another account"
- **Solution**: Google ID đã được sử dụng bởi tài khoản khác
- **Workaround**: User cần đăng nhập bằng tài khoản đã link hoặc unlink account cũ

### Issue: Migration fails with "column already exists"
- **Solution**: Drop column thủ công hoặc tạo migration mới để alter table

## Next Steps

- [ ] Implement unlink Google account feature
- [ ] Add Google Calendar/Drive API integration (optional)
- [ ] Add unit tests for Google OAuth flow
- [ ] Add rate limiting for OAuth endpoints
- [ ] Add audit log for OAuth logins
