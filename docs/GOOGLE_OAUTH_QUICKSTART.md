# 🚀 Quick Start: Google OAuth Login

## Bước 1: Cấu hình Google OAuth Credentials

1. Truy cập https://console.cloud.google.com/
2. Tạo project mới hoặc chọn project hiện có
3. Vào **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Chọn **Web application**
6. Thêm **Authorized JavaScript origins**: `http://localhost:3000` (URL frontend của bạn)
7. Thêm **Authorized redirect URIs**: `http://localhost:3000/auth/callback` (nếu cần)
8. Copy **Client ID** và **Client Secret**

## Bước 2: Cấu hình Environment Variables

Thêm vào file `server/.env`:

```env
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456ghi789
```

## Bước 3: Chạy Migration

```bash
cd server
python -m flask db migrate -m "Add Google OAuth fields to User model"
python -m flask db upgrade
```

## Bước 4: Test API với Postman

### 4.1. Lấy Google ID Token

**Cách 1: Sử dụng Google OAuth Playground**
1. Truy cập https://developers.google.com/oauthplayground/
2. Chọn "Google OAuth2 API v2" > "userinfo.email" và "userinfo.profile"
3. Click "Authorize APIs"
4. Login với Google account
5. Click "Exchange authorization code for tokens"
6. Copy **id_token** (đây là google_token bạn cần)

**Cách 2: Sử dụng Frontend (khuyên dùng cho production)**
```html
<!-- Thêm vào HTML -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="g_id_onload"
     data-client_id="YOUR_GOOGLE_CLIENT_ID"
     data-callback="handleCredentialResponse">
</div>
<div class="g_id_signin" data-type="standard"></div>

<script>
function handleCredentialResponse(response) {
  const googleToken = response.credential; // This is the ID token
  console.log('Google Token:', googleToken);
  // Use this token to call /auth/google
}
</script>
```

### 4.2. Test Login Endpoint

```http
POST http://localhost:5000/auth/google
Content-Type: application/json

{
  "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE4MmU0MjMyYzc..."
}
```

**Expected Response:**
```json
{
  "result_code": "00091",
  "message_en": "You have successfully logged in with Google.",
  "message_vi": "Bạn đã đăng nhập thành công bằng Google.",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@gmail.com",
      "name": "John Doe",
      "username": "user_1234",
      "google_id": "108765432109876543210",
      "auth_provider": "google",
      "profile_picture": "https://lh3.googleusercontent.com/a/...",
      "is_verified": true
    },
    "role": "user",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### 4.3. Test Link Google Account (Optional)

**Yêu cầu:** User đã có tài khoản local và đã đăng nhập

```http
POST http://localhost:5000/auth/link-google
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE4MmU0MjMyYzc..."
}
```

**Expected Response:**
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

## Bước 5: Verify Database

Kiểm tra trong database:

```sql
-- Check if user was created correctly
SELECT id, email, name, google_id, auth_provider, is_verified, profile_picture
FROM users
WHERE google_id IS NOT NULL;

-- Expected result:
-- google_id: '108765432109876543210'
-- auth_provider: 'google'
-- is_verified: true
-- password_hash: NULL (for pure OAuth users)
-- profile_picture: 'https://lh3.googleusercontent.com/...'
```

## ✅ Checklist

- [ ] Đã tạo Google OAuth credentials
- [ ] Đã cấu hình GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET trong .env
- [ ] Đã chạy migration thành công
- [ ] Đã test endpoint /auth/google thành công
- [ ] User được tạo trong database với google_id
- [ ] Access token và refresh token được trả về
- [ ] User tự động verified (is_verified=true)
- [ ] Profile picture được lưu đúng

## 🐛 Common Issues

### Issue: "Invalid Google token"
**Nguyên nhân:** 
- GOOGLE_CLIENT_ID không đúng
- Token đã hết hạn (ID tokens thường expire sau 1 giờ)

**Giải pháp:**
- Verify GOOGLE_CLIENT_ID trong .env khớp với Google Console
- Get new token từ OAuth Playground hoặc frontend

### Issue: "Google email not verified"
**Nguyên nhân:** Email trong Google account chưa được verify

**Giải pháp:** User cần verify email trong Google account settings

### Issue: "This Google account is already linked to another account"
**Nguyên nhân:** Google ID đã được link với tài khoản khác

**Giải pháp:** 
- User login vào account đã link
- Hoặc implement unlink feature

## 📚 Tài liệu đầy đủ

Xem file `docs/GOOGLE_OAUTH_GUIDE.md` để có hướng dẫn chi tiết hơn về:
- Frontend integration
- Security best practices
- Error handling
- Advanced features

## 🎉 Done!

Bây giờ user có thể đăng nhập bằng Google account! 🚀
