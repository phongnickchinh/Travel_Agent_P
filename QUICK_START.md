# Registration Page - Quick Start

## 🎯 Mở trang ngay lập tức

### Option 1: Mở trực tiếp file HTML
```
Nhấp đúp vào: client/register.html
```

### Option 2: Dùng Live Server (VS Code)
```
1. Cài extension "Live Server" trong VS Code
2. Right-click vào register.html
3. Chọn "Open with Live Server"
```

### Option 3: Python HTTP Server
```bash
cd client
python -m http.server 8000
# Mở browser: http://localhost:8000/register.html
```

---

## ⚡ Flow Đăng Ký

### Bước 1: Điền Form
```
✅ Email: test@example.com
✅ Password: password123 (6-20 ký tự)
✅ Confirm Password: password123 (phải giống)
✅ Username: testuser (tối thiểu 3 ký tự)
✅ Full Name: Test User
✅ Language: English hoặc Tiếng Việt
✅ Timezone: Asia/Ho Chi Minh
```

Click **"Register"** → Tự động gửi verification code qua email

### Bước 2: Verify Email
```
1. Màn hình chuyển sang bước Verification
2. Hiện thông báo: "We've sent a 6-digit verification code to test@example.com"
3. Kiểm tra email nhận mã (ví dụ: 123456)
4. Nhập 6 số vào ô input
5. Click "Verify Email"
```

**Nếu không nhận được mã:**
- Click nút **"Resend Code"**
- Đợi 60 giây để resend lại

### Bước 3: Thành Công
```
✓ Email verified successfully!
✓ Access token và Refresh token được lưu vào localStorage
✓ Tự động redirect đến dashboard sau 2 giây
```

---

## 🎨 Giao Diện

### Màu Sắc
- **Primary**: Indigo (#4F46E5) - Nút chính
- **Success**: Green (#10B981) - Thông báo thành công
- **Error**: Red (#EF4444) - Thông báo lỗi
- **Background**: Purple gradient - Nền trang

### Animations
- ✨ Fade in khi chuyển step
- ⏳ Loading spinner khi đang xử lý
- ✓ Success popup với scale animation
- 🕐 Countdown timer cho resend

---

## 🧪 Test Nhanh

### Test 1: Registration thành công
```javascript
// Mở console (F12) và chạy:
localStorage.clear();  // Xóa data cũ
// Sau đó điền form và submit
```

### Test 2: Xem data sau khi verify
```javascript
// Mở console và chạy:
console.log({
  deviceId: localStorage.getItem('deviceId'),
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token')
});
```

### Test 3: Simulate resend
```javascript
// Chờ 60s hoặc modify code để test ngay
// Trong register.js, line 347: resendCountdown = 60;
// Đổi thành: resendCountdown = 3;  // Chỉ đợi 3 giây
```

---

## ⚠️ Lỗi Thường Gặp

### Lỗi 1: "Email already exists"
```
Nguyên nhân: Email đã được đăng ký
Giải pháp: Dùng email khác hoặc đăng nhập
```

### Lỗi 2: "Invalid verification code"
```
Nguyên nhân: Mã không đúng hoặc đã hết hạn (30 phút)
Giải pháp: Click "Resend Code" để lấy mã mới
```

### Lỗi 3: "Password must be 6-20 characters"
```
Nguyên nhân: Mật khẩu quá ngắn hoặc quá dài
Giải pháp: Nhập mật khẩu từ 6-20 ký tự
```

### Lỗi 4: "Passwords do not match"
```
Nguyên nhân: Password và Confirm Password không giống nhau
Giải pháp: Nhập lại cho khớp
```

### Lỗi 5: CORS Error
```
Nguyên nhân: Server chưa bật CORS hoặc sai domain
Giải pháp: 
1. Kiểm tra server đang chạy
2. Kiểm tra API_BASE_URL trong register.js
3. Thêm CORS headers ở server
```

---

## 📱 Responsive Design

### Desktop (>576px)
- Card width: 500px
- Padding: 40px
- Font size: Standard

### Mobile (≤576px)
- Card width: 100%
- Padding: 24px
- Font size: Slightly smaller
- Touch-friendly buttons

---

## 🔑 API Endpoints

Đảm bảo server đang chạy và các endpoints này hoạt động:

```
✓ POST /api/auth/register
✓ POST /api/auth/verify-email
✓ POST /api/auth/send-verification-code
```

Test endpoints với curl:
```bash
# Test register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "username": "testuser",
    "name": "Test User",
    "language": "en",
    "timezone": "Asia/Ho_Chi_Minh",
    "deviceId": "device-123"
  }'
```

---

## 💡 Tips

1. **Development Mode**: Verification code hiện trong response register (đừng dùng production!)
2. **Timer**: 60s cooldown cho resend để tránh spam
3. **Auto-redirect**: 2s sau khi verify thành công
4. **Device ID**: Tự động generate và lưu vào localStorage
5. **Back Button**: Có thể quay lại form đăng ký nếu cần

---

## 🚀 Next Steps

Sau khi register thành công:
1. User được redirect đến `dashboard.html`
2. Access token được lưu trong localStorage
3. Dùng token này cho các API calls tiếp theo:

```javascript
fetch('/api/some-endpoint', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
```

---

## 📞 Need Help?

- 📖 [Full Documentation](./REGISTER_PAGE_GUIDE.md)
- 📧 [Email Verification API Guide](../docs/EMAIL_VERIFICATION_GUIDE.md)
- 🔍 [API Documentation](../docs/README.md)

---

**Happy Registering! 🎉**
