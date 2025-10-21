# Email Verification - Quick Reference

## 📧 Two-Step Process

### Step 1️⃣: Send Verification Code
```http
POST /api/auth/send-verification-code
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "confirmToken": "eyJhbGci...",
  "resultCode": "00048"
}
```

### Step 2️⃣: Verify Email with Code
```http
POST /api/auth/verify-email
Content-Type: application/json

{
  "confirm_token": "eyJhbGci...",
  "verification_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "resultCode": "00058"
}
```

---

## 🎯 Common Use Cases

### Use Case 1: New User Registration Flow
```
Register → Get confirmToken → Check Email → Enter Code → Verify → Login
```

### Use Case 2: Resend Verification Code
```
Send-Verification-Code → Get NEW confirmToken → Check Email → Enter Code → Verify
```

---

## 📱 Frontend Integration Example

### React/Vue/Angular
```javascript
// 1. Send code
const sendCode = async (email) => {
  const res = await fetch('/api/auth/send-verification-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  const data = await res.json();
  return data.confirmToken;
};

// 2. Verify code
const verifyCode = async (confirmToken, code) => {
  const res = await fetch('/api/auth/verify-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirm_token: confirmToken,
      verification_code: code
    })
  });
  const data = await res.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
};
```

---

## ⚡ Quick Test with cURL

```bash
# Step 1: Send code
curl -X POST http://localhost:5000/api/auth/send-verification-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Step 2: Verify (replace TOKEN and CODE)
curl -X POST http://localhost:5000/api/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"confirm_token": "TOKEN_HERE", "verification_code": "123456"}'
```

---

## ❌ Common Errors

| Code | Message | Solution |
|------|---------|----------|
| 00043 | Email not registered | Register first |
| 00046 | Email already verified | Just login |
| 00054 | Invalid/expired code | Request new code |
| 00025 | Missing fields | Check request body |
| 00005 | Invalid email format | Fix email format |

---

## ⏱️ Timeouts

- **Confirm Token**: 30 minutes
- **Verification Code**: 30 minutes
- **Access Token**: 1 hour
- **Refresh Token**: 7 days

---

## 🔐 Security Notes

✅ Verification code is 6 random digits (000000-999999)  
✅ Codes expire after 30 minutes  
✅ One email = one account policy enforced  
✅ Tokens are JWT-based and secure  
✅ Use HTTPS in production  

---

## 📚 Full Documentation

See [EMAIL_VERIFICATION_GUIDE.md](./EMAIL_VERIFICATION_GUIDE.md) for complete details.
