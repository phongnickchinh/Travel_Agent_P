# Email Verification API Guide

## Overview
Hệ thống xác thực email sử dụng mã verification 6 chữ số được gửi qua email. Quy trình gồm 2 bước:
1. **Send Verification Code** - Gửi mã xác thực đến email
2. **Verify Email** - Xác nhận mã và kích hoạt tài khoản

## API Endpoints

### 1. Send Verification Code

Gửi mã xác thực 6 chữ số đến email của người dùng.

#### Endpoint
```
POST /api/auth/send-verification-code
```

#### Request Headers
```
Content-Type: application/json
```

#### Request Body
```json
{
  "email": "user@example.com"
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | Email của người dùng cần xác thực |

#### Success Response (200 OK)
```json
{
  "resultMessage": {
    "en": "Code has been sent to your email successfully.",
    "vn": "Mã đã được gửi đến email của bạn thành công."
  },
  "resultCode": "00048",
  "confirmToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| resultMessage | object | Thông báo kết quả bằng 2 ngôn ngữ (en, vn) |
| resultCode | string | Mã kết quả duy nhất |
| confirmToken | string | JWT token để xác nhận (expires sau 30 phút) |

#### Error Responses

**400 Bad Request - Invalid JSON**
```json
{
  "resultMessage": {
    "en": "Invalid JSON data.",
    "vn": "Dữ liệu JSON không hợp lệ."
  },
  "resultCode": "00004"
}
```

**400 Bad Request - Missing Email**
```json
{
  "resultMessage": {
    "en": "Please provide all required fields!",
    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
  },
  "resultCode": "00025"
}
```

**400 Bad Request - Invalid Email Format**
```json
{
  "resultMessage": {
    "en": "Please provide a valid email address.",
    "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ."
  },
  "resultCode": "00005"
}
```

**400 Bad Request - Email Not Registered**
```json
{
  "resultMessage": {
    "en": "Your email has not been activated, please register first.",
    "vn": "Email của bạn chưa được kích hoạt, vui lòng đăng ký trước."
  },
  "resultCode": "00043"
}
```

**400 Bad Request - Email Already Verified**
```json
{
  "resultMessage": {
    "en": "Your email has already been verified.",
    "vn": "Email của bạn đã được xác minh."
  },
  "resultCode": "00046"
}
```

#### Email Template
Email được gửi với:
- **Subject**: "Your Verification Code from Travel Agent P"
- **Template**: `confirm.html` / `confirm.txt`
- **Content**: Mã verification 6 chữ số (ví dụ: `123456`)

#### Example Usage

**cURL**
```bash
curl -X POST http://localhost:5000/api/auth/send-verification-code \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**JavaScript (Fetch API)**
```javascript
const response = await fetch('http://localhost:5000/api/auth/send-verification-code', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com'
  })
});

const data = await response.json();
console.log('Confirm Token:', data.confirmToken);
```

**Python (Requests)**
```python
import requests

response = requests.post(
    'http://localhost:5000/api/auth/send-verification-code',
    json={'email': 'user@example.com'}
)

data = response.json()
print(f"Confirm Token: {data['confirmToken']}")
```

---

### 2. Verify Email

Xác nhận mã verification và kích hoạt tài khoản người dùng.

#### Endpoint
```
POST /api/auth/verify-email
```

#### Request Headers
```
Content-Type: application/json
```

#### Request Body
```json
{
  "confirm_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "verification_code": "123456"
}
```

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| confirm_token | string | Yes | Token nhận được từ endpoint send-verification-code |
| verification_code | string | Yes | Mã 6 chữ số nhận qua email |

#### Success Response (200 OK)
```json
{
  "resultMessage": {
    "en": "Your email address has been verified successfully.",
    "vn": "Địa chỉ email của bạn đã được xác minh thành công."
  },
  "resultCode": "00058",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| resultMessage | object | Thông báo kết quả bằng 2 ngôn ngữ (en, vn) |
| resultCode | string | Mã kết quả duy nhất |
| access_token | string | JWT access token (expires sau 3600s) |
| refresh_token | string | JWT refresh token (expires sau 604800s) |

#### Error Responses

**400 Bad Request - Invalid JSON**
```json
{
  "resultMessage": {
    "en": "Invalid JSON data.",
    "vn": "Dữ liệu JSON không hợp lệ."
  },
  "resultCode": "00004"
}
```

**400 Bad Request - Missing Fields**
```json
{
  "resultMessage": {
    "en": "Please provide all required fields!",
    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
  },
  "resultCode": "00025"
}
```

**400 Bad Request - Invalid Code or Expired Token**
```json
{
  "resultMessage": {
    "en": "The code you entered does not match the code we sent to your email. Please check again.",
    "vn": "Mã bạn nhập không khớp với mã chúng tôi đã gửi đến email của bạn. Vui lòng kiểm tra lại."
  },
  "resultCode": "00054"
}
```

#### Example Usage

**cURL**
```bash
curl -X POST http://localhost:5000/api/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{
    "confirm_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "verification_code": "123456"
  }'
```

**JavaScript (Fetch API)**
```javascript
const response = await fetch('http://localhost:5000/api/auth/verify-email', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    confirm_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    verification_code: '123456'
  })
});

const data = await response.json();
console.log('Access Token:', data.access_token);
console.log('Refresh Token:', data.refresh_token);

// Lưu tokens để sử dụng cho các API calls sau
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

**Python (Requests)**
```python
import requests

response = requests.post(
    'http://localhost:5000/api/auth/verify-email',
    json={
        'confirm_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'verification_code': '123456'
    }
)

data = response.json()
print(f"Access Token: {data['access_token']}")
print(f"Refresh Token: {data['refresh_token']}")
```

---

## Complete Flow Example

### Scenario: Người dùng vừa đăng ký và cần xác thực email

#### Step 1: Register (Đăng ký)
```javascript
// 1. Đăng ký tài khoản mới
const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'newuser@example.com',
    password: 'SecurePass123',
    username: 'newuser',
    name: 'New User',
    language: 'en',
    timezone: 'Asia/Ho_Chi_Minh',
    deviceId: 'device-001'
  })
});

const registerData = await registerResponse.json();
// registerData.confirmToken - Token để verify
// registerData.verificationCode - Mã (chỉ dùng trong development)
console.log('Confirm Token:', registerData.confirmToken);
```

#### Step 2: Check Email
```
Người dùng kiểm tra email và lấy mã verification 6 chữ số.
Ví dụ: 123456
```

#### Step 3: Verify Email
```javascript
// 2. Xác thực email với mã nhận được
const verifyResponse = await fetch('http://localhost:5000/api/auth/verify-email', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    confirm_token: registerData.confirmToken,
    verification_code: '123456'  // Mã từ email
  })
});

const verifyData = await verifyResponse.json();

if (verifyResponse.ok) {
  // Lưu tokens
  localStorage.setItem('access_token', verifyData.access_token);
  localStorage.setItem('refresh_token', verifyData.refresh_token);
  
  console.log('Email verified successfully!');
  // Redirect to dashboard
  window.location.href = '/dashboard';
}
```

---

### Scenario: Người dùng đã đăng ký nhưng chưa verify và muốn gửi lại mã

#### Step 1: Resend Verification Code
```javascript
// 1. Gửi lại mã xác thực
const resendResponse = await fetch('http://localhost:5000/api/auth/send-verification-code', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'existing@example.com'
  })
});

const resendData = await resendResponse.json();
console.log('New Confirm Token:', resendData.confirmToken);

// Show message to user
alert('A new verification code has been sent to your email.');
```

#### Step 2: Enter Code from Email
```html
<input type="text" id="code" placeholder="Enter 6-digit code" maxlength="6" />
<button onclick="verifyEmail()">Verify</button>
```

#### Step 3: Verify
```javascript
async function verifyEmail() {
  const code = document.getElementById('code').value;
  
  if (code.length !== 6) {
    alert('Please enter a 6-digit code');
    return;
  }
  
  const verifyResponse = await fetch('http://localhost:5000/api/auth/verify-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirm_token: resendData.confirmToken,
      verification_code: code
    })
  });
  
  const verifyData = await verifyResponse.json();
  
  if (verifyResponse.ok) {
    localStorage.setItem('access_token', verifyData.access_token);
    localStorage.setItem('refresh_token', verifyData.refresh_token);
    window.location.href = '/dashboard';
  } else {
    alert(verifyData.resultMessage.en);
  }
}
```

---

## Flow Diagram

```
┌─────────────────┐
│   User Signup   │
│   (Register)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ System generates verification   │
│ code and sends email            │
│ Returns: confirmToken           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ User checks email and gets      │
│ 6-digit verification code       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ User enters code in app         │
│ POST /verify-email              │
│ Body: {confirm_token, code}     │
└────────┬────────────────────────┘
         │
         ▼
    ┌────┴────┐
    │ Valid?  │
    └────┬────┘
         │
    ┌────┼────┐
    │Yes │No  │
    ▼    │    ▼
┌───────┐│ ┌──────────────┐
│Verify ││ │Return error: │
│Email  ││ │Invalid code  │
│Success││ └──────────────┘
└───┬───┘│
    │    │
    ▼    │
┌───────────────────┐
│ Return tokens:    │
│ - access_token    │
│ - refresh_token   │
│ User can now      │
│ access protected  │
│ endpoints         │
└───────────────────┘
```

---

## Token Expiration & Security

### Confirm Token
- **Lifetime**: 30 minutes (1800 seconds)
- **Purpose**: Xác nhận quyền sở hữu email
- **One-time use**: Không (có thể resend để lấy token mới)

### Verification Code
- **Lifetime**: 30 minutes (theo confirm_token)
- **Format**: 6 chữ số (000000 - 999999)
- **Security**: Random generation, stored in database

### Access Token (sau khi verify)
- **Lifetime**: 1 hour (3600 seconds)
- **Purpose**: Truy cập protected endpoints
- **Header**: `Authorization: Bearer <access_token>`

### Refresh Token (sau khi verify)
- **Lifetime**: 7 days (604800 seconds)
- **Purpose**: Lấy access_token mới khi hết hạn
- **Endpoint**: POST /api/auth/refresh-token

---

## Error Handling Best Practices

### Frontend Implementation

```javascript
async function sendVerificationCode(email) {
  try {
    const response = await fetch('/api/auth/send-verification-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Handle specific error codes
      switch (data.resultCode) {
        case '00043':
          throw new Error('Email not registered. Please sign up first.');
        case '00046':
          throw new Error('Email already verified. Please login.');
        case '00005':
          throw new Error('Invalid email format.');
        default:
          throw new Error(data.resultMessage.en);
      }
    }
    
    return data.confirmToken;
    
  } catch (error) {
    console.error('Error sending verification code:', error);
    throw error;
  }
}

async function verifyEmail(confirmToken, code) {
  try {
    const response = await fetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        confirm_token: confirmToken,
        verification_code: code
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Handle specific error codes
      switch (data.resultCode) {
        case '00054':
          throw new Error('Invalid or expired verification code.');
        case '00025':
          throw new Error('Please provide all required fields.');
        default:
          throw new Error(data.resultMessage.en);
      }
    }
    
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token
    };
    
  } catch (error) {
    console.error('Error verifying email:', error);
    throw error;
  }
}
```

---

## Testing

### Manual Testing with Postman

#### Test 1: Send Verification Code
1. Open Postman
2. Create new POST request: `http://localhost:5000/api/auth/send-verification-code`
3. Headers: `Content-Type: application/json`
4. Body (raw JSON):
```json
{
  "email": "test@example.com"
}
```
5. Send request
6. Check email for verification code
7. Save `confirmToken` from response

#### Test 2: Verify Email
1. Create new POST request: `http://localhost:5000/api/auth/verify-email`
2. Headers: `Content-Type: application/json`
3. Body (raw JSON):
```json
{
  "confirm_token": "<confirmToken_from_previous_request>",
  "verification_code": "123456"
}
```
4. Send request
5. Save `access_token` and `refresh_token` from response

---

## Troubleshooting

### Problem: Email not received
**Solutions:**
- Check spam/junk folder
- Verify email service configuration in `.env`
- Check server logs for email sending errors
- Wait a few minutes (email delivery delay)

### Problem: "Invalid or expired verification code"
**Solutions:**
- Check if code matches exactly (no spaces)
- Verify confirmToken hasn't expired (30 min limit)
- Request new code via send-verification-code endpoint
- Check server time is synchronized

### Problem: "Email already verified"
**Solutions:**
- User can login directly with POST /api/auth/login
- No need to verify again

### Problem: "Email has not been activated"
**Solutions:**
- User needs to register first with POST /api/auth/register
- Check if email exists in database

---

## Security Considerations

1. **Rate Limiting**: Implement rate limiting to prevent abuse
   - Max 3 requests per email per hour for send-verification-code
   - Max 5 verification attempts per confirm_token

2. **Code Expiration**: Verification codes expire after 30 minutes

3. **One Email = One Account**: System enforces unique email constraint

4. **Secure Token Storage**: 
   - Never expose tokens in URLs
   - Store tokens in httpOnly cookies or secure storage
   - Use HTTPS in production

5. **Email Validation**: Backend validates email format before sending

---

## Related Documentation

- [Authentication Guide](./AUTHENTICATION_GUIDE.md)
- [Google OAuth Guide](./GOOGLE_OAUTH_GUIDE.md)
- [Password Reset Guide](./PASSWORD_RESET_GUIDE.md)
- [API Error Codes Reference](./ERROR_CODES.md)

---

## Date
Created: December 2024
Last Updated: December 2024
