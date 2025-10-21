# Registration Page Guide

## 📝 Overview
Simple and elegant registration page with email verification flow for Travel Agent P.

## ✨ Features

### Step 1: Registration Form
- Email and password input
- Username and full name
- Language selection (English/Vietnamese)
- Timezone selection
- Real-time validation
- Password confirmation
- Responsive design

### Step 2: Email Verification
- Automatic verification code sent after registration
- 6-digit code input
- Resend code functionality with 60-second cooldown
- Back to registration option
- Auto-redirect to dashboard after successful verification

## 🚀 How to Use

### 1. Setup
Place files in your client directory:
```
client/
├── register.html
├── css/
│   └── register.css
└── js/
    └── register.js
```

### 2. Configuration
Update API_BASE_URL in `register.js` if needed:
```javascript
const API_BASE_URL = 'http://localhost:5000/api/auth';
```

### 3. Open in Browser
```
http://localhost:5000/register.html
```

## 📋 Registration Flow

```
┌─────────────────┐
│ 1. Fill Form    │
│   - Email       │
│   - Password    │
│   - Username    │
│   - Full Name   │
│   - Language    │
│   - Timezone    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. Submit Registration  │
│   POST /auth/register   │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ 3. Verification Code Sent    │
│   - Code sent to email       │
│   - confirmToken received    │
│   - Show verification step   │
└────────┬─────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. Enter 6-Digit Code   │
│   - Input code          │
│   - Option to resend    │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│ 5. Verify Email          │
│   POST /auth/verify-email│
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ 6. Success!              │
│   - Tokens saved         │
│   - Redirect to dashboard│
└──────────────────────────┘
```

## 🎨 UI Components

### Registration Form
- Email input with validation
- Password input (6-20 characters)
- Password confirmation
- Username input
- Full name input
- Language dropdown
- Timezone dropdown
- Submit button with loading state

### Verification Form
- 6-digit code input
- Verify button with loading state
- Resend code button (60s cooldown)
- Timer display
- Back to registration button

### Alerts
- Success alerts (green)
- Error alerts (red)
- Info alerts (blue)

## 🔧 Validation Rules

### Email
- Required
- Valid email format (regex: `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`)

### Password
- Required
- 6-20 characters long
- Must match confirmation

### Username
- Required
- Minimum 3 characters

### Full Name
- Required

### Verification Code
- Required
- Exactly 6 digits
- Numeric only

## 🎯 API Endpoints Used

### 1. Register
```
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "username": "username",
  "name": "Full Name",
  "language": "en",
  "timezone": "Asia/Ho_Chi_Minh",
  "deviceId": "device-xxx"
}

Response:
{
  "resultCode": "00035",
  "confirmToken": "eyJhbGci...",
  "verificationCode": "123456",
  "user": {...}
}
```

### 2. Verify Email
```
POST /api/auth/verify-email
Content-Type: application/json

{
  "confirm_token": "eyJhbGci...",
  "verification_code": "123456"
}

Response:
{
  "resultCode": "00058",
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci..."
}
```

### 3. Resend Verification Code
```
POST /api/auth/send-verification-code
Content-Type: application/json

{
  "email": "user@example.com"
}

Response:
{
  "resultCode": "00048",
  "confirmToken": "eyJhbGci..."
}
```

## 💾 Local Storage

The page stores:
- `deviceId`: Unique device identifier (auto-generated)
- `access_token`: JWT access token (after verification)
- `refresh_token`: JWT refresh token (after verification)

## 🎨 Styling

### Color Scheme
- Primary: `#4F46E5` (Indigo)
- Success: `#10B981` (Green)
- Error: `#EF4444` (Red)
- Background: Linear gradient (Purple)

### Responsive Breakpoints
- Mobile: `max-width: 576px`

## ⚠️ Error Handling

### Common Errors

| Error Code | Message | Field |
|------------|---------|-------|
| 00032 | Email already exists | email |
| 00067 | Username already taken | username |
| 00066 | Invalid password length | password |
| 00005 | Invalid email format | email |
| 00054 | Invalid verification code | verificationCode |

### Error Display
- Field-specific errors appear below inputs in red
- General errors appear as alert banners at top
- Auto-dismiss after 5 seconds

## 🔐 Security Features

1. **Password Validation**: 6-20 characters
2. **Email Validation**: Regex validation
3. **Device ID**: Unique per device
4. **Token Storage**: Secure local storage
5. **HTTPS**: Use in production
6. **Resend Cooldown**: Prevents spam (60s)

## 📱 Features

### Auto-Format
- Verification code: Numbers only, max 6 digits
- Email: Trimmed whitespace

### Loading States
- Button spinners during API calls
- Disabled state while processing
- Loading overlay for critical operations

### User Feedback
- Real-time validation
- Clear error messages (English/Vietnamese)
- Success animations
- Countdown timer for resend

### Accessibility
- Proper labels for all inputs
- Focus management
- Keyboard navigation
- ARIA attributes

## 🧪 Testing

### Test Cases

1. **Valid Registration**
   - Fill all fields correctly
   - Submit form
   - Check email for code
   - Enter code
   - Verify redirect to dashboard

2. **Invalid Email**
   - Enter invalid email format
   - Check error message appears

3. **Password Mismatch**
   - Enter different passwords
   - Check confirmation error

4. **Duplicate Email**
   - Try to register with existing email
   - Check error message

5. **Invalid Code**
   - Enter wrong verification code
   - Check error message

6. **Resend Code**
   - Wait for timer
   - Click resend
   - Check new code sent

## 🚀 Production Checklist

- [ ] Update API_BASE_URL to production URL
- [ ] Enable HTTPS
- [ ] Add CORS configuration
- [ ] Set up email service
- [ ] Configure rate limiting
- [ ] Add analytics tracking
- [ ] Test on multiple browsers
- [ ] Test on mobile devices
- [ ] Add password strength indicator
- [ ] Implement CAPTCHA (optional)

## 📞 Support

For issues or questions, refer to:
- [Email Verification Guide](../docs/EMAIL_VERIFICATION_GUIDE.md)
- [API Documentation](../docs/README.md)

## 🔄 Future Enhancements

- [ ] Social login integration (Google, Facebook)
- [ ] Password strength meter
- [ ] Terms of service checkbox
- [ ] Privacy policy link
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Remember me functionality
- [ ] Two-factor authentication option

---

**Created**: December 2024  
**Version**: 1.0.0
