# 🛡️ Bảo mật MongoDB trong kiến trúc lai PostgreSQL + MongoDB

## 🎯 Mục tiêu
MongoDB trong hệ thống lai chỉ lưu dữ liệu phi cấu trúc như lịch trình, review, kế hoạch AI, không chứa thông tin người dùng hoặc mật khẩu.  
Do đó, bảo mật tập trung vào việc **ngăn truy cập trái phép**, **chống NoSQL injection**, **quản lý dung lượng**, và **bảo vệ API nội bộ**.

---

## 🔐 1. Xác thực & Phân quyền
- Bật xác thực trong `mongod.conf`:
  ```yaml
  security:
    authorization: enabled
  ```
- Tạo user riêng cho ứng dụng Flask:
  ```bash
  use travelplanner_db
  db.createUser({
    user: "planner_rw",
    pwd: "StrongPassword123!",
    roles: [{role: "readWrite", db: "travelplanner_db"}]
  })
  ```
- Flask kết nối bằng tài khoản riêng, không dùng `root`.

---

## 🌐 2. Giới hạn truy cập mạng
- Trong `mongod.conf`, chỉ cho phép kết nối nội bộ:
  ```yaml
  net:
    bindIp: 127.0.0.1
  ```
- Nếu deploy bằng Docker, chỉ expose trong localhost:
  ```yaml
  ports:
    - "127.0.0.1:27017:27017"
  ```
- Nếu dùng cloud (Render, AWS, Vercel), để MongoDB trong private subnet.

---

## ⚙️ 3. Chống NoSQL Injection
- Không truyền trực tiếp dữ liệu người dùng vào truy vấn Mongo.
- Dùng ORM an toàn như **MongoEngine** hoặc thư viện validate (Pydantic, Marshmallow).
- Không cho phép ký tự `$`, `.`, `{}`, `}` trong đầu vào.
- Ví dụ validate input:
  ```python
  from marshmallow import Schema, fields, validate

  class PlanInput(Schema):
      destination = fields.Str(required=True, validate=validate.Length(max=255))
      budget = fields.Float(required=True)
  ```

---

## 🚦 4. Chống spam ghi dữ liệu
- Áp dụng **rate limiting** cho các endpoint như `/save-plan`, `/review`.
- Dùng **Celery** hoặc **Redis queue** để kiểm soát tốc độ ghi.

---

## ⏳ 5. TTL và dung lượng dữ liệu
- Dùng TTL Index để Mongo tự xóa dữ liệu tạm (cache hoặc AI plan):
  ```python
  mongo.db.ai_plans.create_index("created_at", expireAfterSeconds=604800)
  ```

---

## 🔒 6. Bảo vệ API key & dữ liệu nội bộ
- Không lưu API key gốc trong MongoDB (dùng alias hoặc mã hóa AES).
- Nếu cần lưu log, mã hóa nội dung bằng `Fernet` hoặc AES.

---

## 📋 7. Giám sát và sao lưu
- Bật log truy cập:
  ```yaml
  systemLog:
    destination: file
    path: /var/log/mongodb/mongod.log
    logAppend: true
  ```
- Sao lưu định kỳ (24h/lần):
  ```bash
  mongodump --db travelplanner_db --out /backups/mongo_$(date +%F)
  ```

---

## 🧠 8. Phân tách quyền giữa PostgreSQL và MongoDB
| Thành phần | Vai trò | Quyền |
|-------------|----------|-------|
| Flask API Auth | PostgreSQL | `readWrite` |
| Flask AI Planner | MongoDB | `readWrite` |
| AI Worker (chỉ đọc dữ liệu review) | MongoDB | `read` |
| DB Admin | Cả hai DB | `admin`, không thông qua ứng dụng |

---

## ✅ 9. Checklist nhanh
| Mục tiêu | Giải pháp |
|-----------|------------|
| ✅ Không truy cập trái phép | `authorization: enabled`, user riêng |
| ✅ Không public Mongo | `bindIp: 127.0.0.1` |
| ✅ Chống spam dữ liệu | Rate limit + TTL index |
| ✅ Tránh NoSQL injection | Validate input / ORM an toàn |
| ✅ Không lộ API key | Hash / alias trước khi lưu |
| ✅ Backup định kỳ | `mongodump` hoặc Atlas Backup |
| ✅ Theo dõi truy cập | Bật `systemLog` |
