# 📖 Hướng dẫn chạy Celery trên Local

## 🎯 Tổng quan

Celery là một distributed task queue được sử dụng để xử lý các tác vụ bất đồng bộ (asynchronous tasks). Trong project **Travel Agent P**, Celery được dùng để gửi email bất đồng bộ, giúp API response nhanh hơn và không bị block bởi việc gửi email.

### Kiến trúc Celery trong project:

```
Flask App (API)
    ↓ (trigger task)
Redis (Message Broker)
    ↓ (queue message)
Celery Worker
    ↓ (execute task)
Gmail SMTP (Send Email)
```

---

## 📋 Prerequisites (Yêu cầu)

### 1. Python Environment
- Python 3.8+ đã cài đặt
- Virtual environment đã được activate

### 2. Redis Server
- Redis phải được cài đặt và chạy trên local
- Default port: `6379`

### 3. Dependencies đã cài đặt
```bash
cd server
pip install -r requirements.txt
```

Key dependencies:
- `celery==5.5.2`
- `redis==6.4.0`
- `flask-mail==0.10.0`

---

## 🔧 Bước 1: Cài đặt Redis

### Windows:

#### Option 1: Download Redis (Recommended)
1. Download Redis từ: https://github.com/microsoftarchive/redis/releases
2. Download file: `Redis-x64-3.0.504.msi` (hoặc version mới hơn)
3. Chạy installer và cài đặt
4. Redis sẽ tự động chạy như Windows Service

#### Option 2: Using Memurai (Redis alternative for Windows)
1. Download Memurai từ: https://www.memurai.com/
2. Cài đặt và chạy như Windows Service

#### Kiểm tra Redis đang chạy:
```bash
# Check if Redis is running
redis-cli ping
# Expected output: PONG

# Check Redis process
tasklist | findstr redis
# Expected: redis-server.exe running
```

### macOS:

```bash
# Install Redis using Homebrew
brew install redis

# Start Redis service
brew services start redis

# Or start manually
redis-server

# Check if running
redis-cli ping
# Expected output: PONG
```

### Linux (Ubuntu/Debian):

```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server

# Test connection
redis-cli ping
# Expected output: PONG
```

---

## ⚙️ Bước 2: Cấu hình Environment Variables

### File: `server/.env`

Đảm bảo các biến sau đã được cấu hình:

```env
# Celery Broker (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0

# Email Configuration (Gmail)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com

# Optional: Mail Server (default sẵn trong config.py)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
```

### ⚠️ Quan trọng: Gmail App Password

**KHÔNG dùng password thật của Gmail!** Phải tạo App Password:

1. Đăng nhập Gmail → Google Account Settings
2. Security → 2-Step Verification (phải bật)
3. App passwords → Select app: "Mail" → Select device: "Other"
4. Nhập tên: "Travel Agent P"
5. Copy password 16 ký tự → Paste vào `.env` file

```env
MAIL_PASSWORD=abcd efgh ijkl mnop  # 16 characters, no spaces in actual value
```

---

## 🚀 Bước 3: Chạy Celery Worker

### Trên Windows:

```bash
# Navigate to server folder
cd p:\coddd\Travel_Agent_P\server

# Activate virtual environment (if using)
venv\Scripts\activate

# Start Celery worker với pool=solo (Windows compatible)
celery -A celery_worker.celery worker --loglevel=info --pool=solo
```

### Trên macOS/Linux:

```bash
# Navigate to server folder
cd /path/to/Travel_Agent_P/server

# Activate virtual environment (if using)
source venv/bin/activate

# Start Celery worker
celery -A celery_worker.celery worker --loglevel=info
```

### 📊 Output khi Celery chạy thành công:

```
 -------------- celery@DESKTOP-XXXXX v5.5.2 (opalescent)
--- ***** -----
-- ******* ---- Windows-10-10.0.19045-SP0 2025-10-23 10:30:00
- *** --- * ---
- ** ---------- [config]
- ** ---------- .> app:         __main__:0x1234567890ab
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     disabled://
- *** --- * --- .> concurrency: 4 (solo)
-- ******* ---- .> task events: OFF (enable -E to monitor)
--- ***** -----
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . app.email.send_async_email

[2025-10-23 10:30:00,123: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-10-23 10:30:00,456: INFO/MainProcess] mingle: searching for neighbors
[2025-10-23 10:30:01,789: INFO/MainProcess] mingle: all alone
[2025-10-23 10:30:02,012: INFO/MainProcess] celery@DESKTOP-XXXXX ready.
```

### ✅ Kiểm tra các điểm sau:
- ✅ **transport:** `redis://localhost:6379/0` - Redis connection OK
- ✅ **[tasks]** section hiển thị: `app.email.send_async_email` - Task registered
- ✅ **ready** message - Worker sẵn sàng nhận tasks

---

## 🚀 Bước 4: Chạy Flask Application

**Mở terminal/command prompt MỚI** (giữ Celery worker chạy ở terminal cũ):

```bash
# Navigate to server folder
cd p:\coddd\Travel_Agent_P\server

# Activate virtual environment
venv\Scripts\activate

# Run Flask app
python run.py
```

hoặc:

```bash
flask run
```

### Output khi Flask chạy:

```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
```

---

## 🧪 Bước 5: Test Email Sending

### Option 1: Test qua Registration

1. Mở browser: `http://localhost:3000/register` (React app)
2. Điền form đăng ký với email thật
3. Submit form
4. **Quan sát Celery worker terminal:**

```
[2025-10-23 10:35:12,345: INFO/MainProcess] Task app.email.send_async_email[abc-123-def] received
[2025-10-23 10:35:14,567: INFO/ForkPoolWorker-1] An email has been sent.
[2025-10-23 10:35:14,789: INFO/ForkPoolWorker-1] Task app.email.send_async_email[abc-123-def] succeeded in 2.4s
```

5. **Check email inbox** - Email verification sẽ đến trong vài giây

### Option 2: Test qua API trực tiếp

Sử dụng Postman hoặc curl:

```bash
# Test registration API
curl -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "username": "testuser",
    "name": "Test User",
    "language": "en",
    "timezone": "UTC",
    "deviceId": "device-123"
  }'
```

### Option 3: Test Reset Password

```bash
curl -X POST http://127.0.0.1:5000/request-reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'
```

---

## 🐛 Troubleshooting (Xử lý lỗi)

### ❌ Lỗi: "ConnectionError: Error 10061 connecting to localhost:6379"

**Nguyên nhân:** Redis chưa chạy

**Giải pháp:**
```bash
# Check if Redis is running
tasklist | findstr redis

# If not running, start Redis
redis-server

# Or on Windows with service installed:
net start redis
```

---

### ❌ Lỗi: "kombu.exceptions.OperationalError: Unable to connect"

**Nguyên nhân:** Redis đang chạy nhưng Celery không kết nối được

**Giải pháp:**
1. Kiểm tra `.env`:
```env
CELERY_BROKER_URL=redis://localhost:6379/0
```

2. Test Redis connection:
```bash
redis-cli ping
# Should return: PONG
```

3. Check Redis logs:
```bash
# Windows (check Event Viewer)
# macOS/Linux:
sudo journalctl -u redis
```

---

### ❌ Lỗi: "SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')"

**Nguyên nhân:** Gmail App Password sai hoặc chưa bật 2-Step Verification

**Giải pháp:**
1. Đảm bảo đã bật **2-Step Verification** trong Google Account
2. Tạo **App Password** mới (không phải password thường)
3. Copy chính xác 16 ký tự vào `.env`:
```env
MAIL_PASSWORD=abcdefghijklmnop  # NO SPACES!
```

4. Restart Celery worker sau khi update `.env`

---

### ❌ Lỗi: "Task never executes" (Task không bao giờ chạy)

**Nguyên nhân:** Celery worker không nhận được task

**Giải pháp:**
1. Check worker có đang chạy không:
```bash
# Look for "celery@..." ready message
```

2. Check task đã được register:
```
[tasks]
  . app.email.send_async_email  # ← Should appear here
```

3. Restart cả Flask app VÀ Celery worker:
```bash
# Terminal 1: Stop Flask (Ctrl+C) → python run.py
# Terminal 2: Stop Celery (Ctrl+C) → celery command again
```

---

### ❌ Lỗi: "ModuleNotFoundError: No module named 'celery_worker'"

**Nguyên nhân:** Chạy Celery command từ sai folder

**Giải pháp:**
```bash
# ĐÚNG: Phải chạy từ server folder
cd p:\coddd\Travel_Agent_P\server
celery -A celery_worker.celery worker --loglevel=info --pool=solo

# SAI: Chạy từ root folder
cd p:\coddd\Travel_Agent_P
celery -A celery_worker.celery worker  # ← Will fail
```

---

### ❌ Celery worker bị crash hoặc hang

**Giải pháp:**

1. **Restart worker:**
```bash
# Press Ctrl+C to stop
# Run command again
celery -A celery_worker.celery worker --loglevel=info --pool=solo
```

2. **Clear Redis queue** (nếu có tasks stuck):
```bash
redis-cli
> FLUSHALL
> exit
```

3. **Check logs** với verbose mode:
```bash
celery -A celery_worker.celery worker --loglevel=debug --pool=solo
```

---

### ❌ Emails gửi chậm hoặc không đến

**Nguyên nhân:** Gmail rate limiting hoặc spam filter

**Giải pháp:**
1. **Check spam folder** trong inbox
2. **Verify sender email** trong Gmail settings
3. **Check Celery logs** xem có error không:
```
[ERROR] SMTPException: ...
```

4. **Test with different email provider:**
```env
# Try with different SMTP (e.g., Outlook, SendGrid)
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
```

---

## 📁 File Structure

```
server/
├── celery_worker.py          # Celery worker entry point
├── config.py                  # Configuration (CELERY_BROKER_URL)
├── .env                       # Environment variables
├── app/
│   ├── __init__.py           # Celery instance initialization
│   ├── email.py              # Email tasks (@celery.task)
│   ├── templates/
│   │   ├── confirm.html      # Email verification template
│   │   ├── confirm.txt
│   │   ├── reset-password.html  # Password reset template
│   │   └── reset-password.txt
│   └── ...
└── run.py                     # Flask app entry point
```

---

## 🔍 Monitoring Celery

### Option 1: Command line (trong worker terminal)

Quan sát logs real-time:
```
[2025-10-23 10:35:12,345: INFO/MainProcess] Task received
[2025-10-23 10:35:14,567: INFO/Worker] Task succeeded
```

### Option 2: Flower (Web-based monitoring)

Cài đặt Flower:
```bash
pip install flower
```

Chạy Flower:
```bash
celery -A celery_worker.celery flower --port=5555
```

Mở browser: `http://localhost:5555`

Dashboard sẽ hiển thị:
- Active workers
- Tasks (pending, success, failed)
- Task execution time
- Broker connection status

---

## ⚡ Production Tips

### 1. Chạy Celery như background service

**Windows (using NSSM):**
```bash
# Download NSSM: https://nssm.cc/download
nssm install CeleryWorker "C:\path\to\venv\Scripts\celery.exe" "-A celery_worker.celery worker --pool=solo"
nssm start CeleryWorker
```

**Linux (using systemd):**
```bash
# Create service file: /etc/systemd/system/celery.service
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/server
ExecStart=/path/to/venv/bin/celery -A celery_worker.celery worker --detach
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Production Redis

Thay `localhost` bằng cloud Redis:
- **Redis Cloud** (free tier): https://redis.com/cloud/
- **AWS ElastiCache**
- **Azure Cache for Redis**
- **Heroku Redis**

```env
CELERY_BROKER_URL=redis://username:password@host:port/0
```

### 3. Alternative: Không dùng Celery

Nếu không muốn setup Celery, có thể dùng **SendGrid API** hoặc **AWS SES** để gửi email đồng bộ:

```python
# app/email.py (without Celery)
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email(to, subject, template, **kwargs):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    message = Mail(
        from_email='noreply@travelagentp.com',
        to_emails=to,
        subject=subject,
        html_content=render_template(f"{template}.html", **kwargs)
    )
    response = sg.send(message)
    return response
```

---

## 📝 Quick Reference Commands

```bash
# Start Redis (Windows)
redis-server

# Start Redis (macOS)
brew services start redis

# Start Redis (Linux)
sudo systemctl start redis-server

# Test Redis
redis-cli ping

# Start Celery Worker (Windows)
celery -A celery_worker.celery worker --loglevel=info --pool=solo

# Start Celery Worker (macOS/Linux)
celery -A celery_worker.celery worker --loglevel=info

# Start Flask App
python run.py

# Monitor with Flower
celery -A celery_worker.celery flower --port=5555

# Clear Redis queue
redis-cli FLUSHALL
```

---

## ✅ Checklist trước khi chạy

- [ ] Redis đã cài đặt và chạy (`redis-cli ping` → PONG)
- [ ] `.env` đã cấu hình đầy đủ (CELERY_BROKER_URL, MAIL_*)
- [ ] Gmail App Password đã tạo (không phải password thường)
- [ ] Virtual environment đã activate
- [ ] Dependencies đã cài đặt (`pip install -r requirements.txt`)
- [ ] Celery worker đang chạy (terminal riêng)
- [ ] Flask app đang chạy (terminal riêng)
- [ ] Test gửi email thành công

---

## 🎓 Summary

**3 bước chính để chạy Celery:**

1. **Start Redis:**
   ```bash
   redis-server
   ```

2. **Start Celery Worker (terminal 1):**
   ```bash
   cd server
   celery -A celery_worker.celery worker --loglevel=info --pool=solo
   ```

3. **Start Flask App (terminal 2):**
   ```bash
   cd server
   python run.py
   ```

**Quan sát logs trong Celery terminal để xem tasks được execute!** 🎉

---

## 📞 Support

Nếu gặp vấn đề, check:
1. Redis logs
2. Celery worker logs (terminal output)
3. Flask app logs
4. Gmail account security settings

Good luck! 🚀
