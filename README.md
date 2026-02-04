<p align="center">
  <img src="docs/images/dino.svg" alt="Travel Agent P Logo" width="30"/>
</p>
<h1 align="center"><span style="color: #2E571C; font-weight: bold;">Travel Agent P</span></h1>

<p align="center">
  <strong>AI-Powered Travel Planning Platform</strong>
  <br>
  <em>Nền tảng lập kế hoạch du lịch thông minh với sự hỗ trợ của Trí tuệ Nhân tạo</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.1.1-green?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/MongoDB-6.0-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB"/>
  <img src="https://img.shields.io/badge/LangChain-AI-FF6B6B?style=for-the-badge" alt="LangChain"/>
</p>

<p align="center">
  <a href="#-tính-năng">Tính năng</a> •
  <a href="#-công-nghệ">Công nghệ</a> •
  <a href="#-cài-đặt">Cài đặt</a> •
  <a href="#-kiến-trúc">Kiến trúc</a> •
  <a href="#-api">API</a> •
  <a href="#-tác-giả">Tác giả</a>
</p>

---

## 📖 Giới thiệu

**Travel Agent P** là một nền tảng lập kế hoạch du lịch thông minh, sử dụng công nghệ Trí tuệ Nhân tạo để tự động tạo lịch trình du lịch cá nhân hóa. Hệ thống kết hợp dữ liệu từ Google Places API với các mô hình ngôn ngữ lớn (LLM) để đề xuất địa điểm phù hợp, tối ưu hóa lộ trình và tạo ra trải nghiệm du lịch hoàn hảo cho người dùng.

### 🎯 Mục tiêu

- **Tự động hóa** quy trình lập kế hoạch du lịch phức tạp
- **Cá nhân hóa** lịch trình dựa trên sở thích, ngân sách và thời gian
- **Tối ưu hóa** lộ trình sử dụng thuật toán phân cụm thông minh
- **Tích hợp AI** để đề xuất địa điểm và tạo mô tả chi tiết

---

## 🖼️ Demo

<!-- TODO: Thêm screenshots của ứng dụng -->

### Trang chủ
![Homepage](docs/images/welcome.png)

### Tạo lịch trình với AI
![Create Plan](docs/images/create_plan.png)

### Chi tiết lịch trình
![Plan Detail](docs/images/plan_detail.png)

### Dashboard người dùng
![Dashboard](docs/images/dashboard.png)

---

## ✨ Tính năng

### 🔐 Xác thực & Bảo mật
- Đăng ký/Đăng nhập với email và mật khẩu
- Xác thực OAuth 2.0 với Google
- JWT Token với cơ chế Refresh Token
- Rate Limiting bảo vệ API
- Redis Blacklist cho logout an toàn

### 🤖 AI Lập kế hoạch Du lịch (là tôi 😁)
- Tạo lịch trình tự động với LLM (Groq/HuggingFace)
- Phân cụm POI thông minh (DBSCAN + Nearest Neighbor)
- Tối ưu hóa thời gian di chuyển giữa các điểm
- Đề xuất địa điểm dựa trên sở thích người dùng

### 🗺️ Quản lý Địa điểm (POI)
- Tích hợp Google Places API
- Elasticsearch cho tìm kiếm full-text
- Hybrid Autocomplete (ES + Google)
- Deduplication thông minh với Geohash

### 📋 Quản lý Lịch trình
- Xem danh sách lịch trình đã tạo
- Chi tiết từng ngày với timeline
- Chia sẻ lịch trình công khai
- Lưu trữ tạm (Trash) và khôi phục

### 👤 Hồ sơ Người dùng
- Cập nhật thông tin cá nhân
- Upload avatar lên Firebase Storage
- Xem lịch sử lịch trình

---

## 🛠️ Công nghệ

### Frontend
| Công nghệ | Phiên bản | Mô tả |
|-----------|-----------|-------|
| React | 18+ | UI Library |
| Vite | 5.x | Build Tool |
| Tailwind CSS | 3.x | Styling Framework |
| Framer Motion | 11.x | Animation Library |
| React Router | 6.x | Routing |
| Axios | 1.x | HTTP Client |
| Lucide React | - | Icon Library |

### Backend
| Công nghệ | Phiên bản | Mô tả |
|-----------|-----------|-------|
| Python | 3.10+ | Programming Language |
| Flask | 3.1.1 | Web Framework |
| SQLAlchemy | 2.0 | ORM |
| Celery | 5.5.2 | Task Queue |
| LangChain | 0.1+ | AI Orchestration |

### Databases
| Công nghệ | Mục đích |
|-----------|----------|
| PostgreSQL | Users, Auth, Tokens (ACID) |
| MongoDB | POI, Plans, Reviews (Flexible Schema) |
| Redis | Cache, Rate Limiting, Celery Broker |
| Elasticsearch | Full-text Search, Autocomplete |

### AI/ML
| Công nghệ | Mục đích |
|-----------|----------|
| Groq API | LLM Inference (Primary) |
| HuggingFace | Embeddings, Fallback LLM |
| DBSCAN | POI Clustering |
| Nearest Neighbor | Route Optimization |

### Infrastructure
| Công nghệ | Mục đích |
|-----------|----------|
| Docker | Containerization |
| Firebase Storage | Image Storage |
| Google Places API | POI Data Source |

---

## 🏗️ Kiến trúc

### Kiến trúc Tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│   React Web App (Vite + Tailwind + Framer Motion)               │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTPS/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Flask)                         │
│   ┌─────────────┐ ┌──────────────┐ ┌─────────────┐              │
│   │  Auth (JWT) │ │ Rate Limiter │ │    CORS     │              │
│   └─────────────┘ └──────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Controller Layer│ │ Service Layer   │ │ Repository Layer│
│  (Blueprints)   │ │ (Business Logic)│ │ (Data Access)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │PostgreSQL│ │ MongoDB  │ │  Redis   │ │  Elasticsearch   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     ASYNC PROCESSING                            │
│   ┌──────────────────────────────────────────────────────┐      │
│   │              Celery Workers                          │      │
│   │  ┌────────────┐ ┌────────────┐ ┌────────────┐        │      │
│   │  │Email Tasks │ │ AI Tasks   │ │ Sync Tasks │        │      │
│   │  └────────────┘ └────────────┘ └────────────┘        │      │
│   └──────────────────────────────────────────────────────┘      │
│                              │                                  │
│   ┌──────────────────────────────────────────────────────┐      │
│   │              AI/ML Layer (LangChain)                 │      │
│   │  ┌────────────┐ ┌────────────┐ ┌────────────┐        │      │
│   │  │ Groq LLM   │ │ Clustering │ │ Embeddings │        │      │
│   │  └────────────┘ └────────────┘ └────────────┘        │      │
│   └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Design Pattern: 4-Layer Architecture

```
Controller (Flask Blueprints)
      │
      ▼
Service (Business Logic)
      │
      ▼
Repository (Data Access)
      │
      ▼
Data Layer (DB/External APIs)
```

> 📚 Xem chi tiết: [Architecture Diagram](docs/ARCHITECTURE_DIAGRAM.md)

---

## 📦 Cài đặt

### Yêu cầu hệ thống

- **Python** 3.10+
- **Node.js** 18+
- **PostgreSQL** 12+
- **MongoDB** 6.0+
- **Redis** 5.0+
- **Elasticsearch** 8.x (Optional)

### 1️. Clone Repository

```bash
git clone https://github.com/phongnickchinh/Travel_Agent_P.git
cd Travel_Agent_P
```

### 2️. Cài đặt Backend

```bash
# Di chuyển vào thư mục server
cd server

# Tạo virtual environment
python -m venv venv

# Kích hoạt virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 3️. Cấu hình Environment Variables

Tạo file `.env` trong thư mục `server/`:

```bash
# Application
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/travel_agent_p

# MongoDB
MONGODB_URI=mongodb://localhost:27017/travel_agent_p

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Google Places API
GOOGLE_PLACES_API_KEY=your_google_places_api_key

# AI (Chọn 1 trong 2)
GROQ_API_KEY=your_groq_api_key
# hoặc
HUGGINGFACE_API_KEY=your_huggingface_api_key

# Firebase Storage
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
FIREBASE_STORAGE_BUCKET=your-bucket.appspot.com

# Email (Gmail SMTP)
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### 4️. Khởi tạo Database

```bash
# Chạy migrations
flask db upgrade
```

### 5️. Chạy Backend Server

```bash
# Terminal 1: Flask Server
python run.py

# Terminal 2: Celery Worker
celery -A celery_worker.celery worker --loglevel=info --pool=solo
```

### 6️. Cài đặt Frontend

```bash
# Di chuyển vào thư mục client
cd ../client

# Cài đặt dependencies
npm install

# Chạy development server
npm run dev
```

### 7️. Truy cập ứng dụng

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5000

---

## 📚 API Documentation

### Authentication

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/auth/register` | Đăng ký tài khoản |
| POST | `/api/auth/login` | Đăng nhập |
| POST | `/api/auth/logout` | Đăng xuất |
| POST | `/api/auth/refresh` | Làm mới token |
| POST | `/api/auth/google` | Đăng nhập Google |
| POST | `/api/auth/verify-email` | Xác thực email |

### User

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/user/profile` | Lấy thông tin user |
| PUT | `/api/user/profile` | Cập nhật profile |
| POST | `/api/user/avatar` | Upload avatar |

### Plans

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/plan/create` | Tạo lịch trình mới |
| GET | `/api/plan/{id}` | Lấy chi tiết lịch trình |
| GET | `/api/plan/my-plans` | Danh sách lịch trình |
| DELETE | `/api/plan/{id}` | Xóa lịch trình |
| POST | `/api/plan/{id}/share` | Chia sẻ lịch trình |

### Search

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/search/autocomplete` | Gợi ý tìm kiếm |
| GET | `/api/places/search` | Tìm kiếm địa điểm |

> 📚 Xem chi tiết: [API Documentation](docs/API_PAYLOAD_EXAMPLES.md)

---

## 📁 Cấu trúc Thư mục

```
Travel_Agent_P/
├── client/                     # Frontend React
│   ├── src/
│   │   ├── components/         # UI Components
│   │   ├── contexts/           # React Contexts
│   │   ├── pages/              # Page Components
│   │   ├── services/           # API Services
│   │   └── utils/              # Utilities
│   └── package.json
│
├── server/                     # Backend Flask
│   ├── app/
│   │   ├── ai/                 # AI/ML Logic
│   │   ├── controller/         # API Controllers
│   │   ├── core/               # Core Utilities
│   │   ├── middleware/         # Middlewares
│   │   ├── model/              # Data Models
│   │   ├── providers/          # External APIs
│   │   ├── repo/               # Repositories
│   │   ├── service/            # Business Logic
│   │   └── tasks/              # Celery Tasks
│   ├── migrations/             # Database Migrations
│   └── requirements.txt
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE_DIAGRAM.md
│   ├── API_PAYLOAD_EXAMPLES.md
│   ├── ELASTICSEARCH_SETUP.md
│   └── ...
│
└── README.md
```

---

## 🧪 Testing

### Backend Tests

```bash
cd server
pytest tests/ -v
```

### Frontend Tests

```bash
cd client
npm run test
```

---

## 🚀 Deployment

### Docker Compose

```bash
# Build và chạy tất cả services
docker-compose up -d

# Xem logs
docker-compose logs -f
```

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Configure HTTPS/SSL
- [ ] Set up Nginx reverse proxy
- [ ] Configure proper CORS origins
- [ ] Enable Redis persistence
- [ ] Set up database backups
- [ ] Configure monitoring (Sentry)

---

## 📊 Performance

### Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| API Response Time (p95) | < 500ms | ✅ ~200ms |
| AI Generation Time | < 60s | ✅ ~30-45s |
| Redis Cache Hit Rate | > 70% | ✅ ~85% |
| Concurrent Users | 100+ | ✅ Tested |

---

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

---

## 📄 License

Dự án được phân phối dưới giấy phép MIT. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

## 👨‍💻 Tác giả

<p align="center">
  <img src="docs/images/author.jpg" alt="Author" width="150" style="border-radius: 50%;"/>
</p>

<p align="center">
  <strong>Phạm Văn Phong</strong>
  <br>
  MSSV: 20215448
  <br>
  Trường Công nghệ thông tin và Truyền thông, Đại học Bách khoa Hà Nội
</p>

<p align="center">
  <strong>Giáo viên hướng dẫn:</strong> TS. Đỗ Quốc Huy
</p>

<p align="center">
  <a href="https://github.com/phongnickchinh">
    <img src="https://img.shields.io/badge/GitHub-phongnickchinh-181717?style=for-the-badge&logo=github" alt="GitHub"/>
  </a>
</p>

---

## 🙏 Lời cảm ơn

- **TS. Đỗ Quốc Huy** - Giáo viên hướng dẫn
- **Trường Công nghệ thông tin và Truyền thông, ĐHBKHN** - Đơn vị đào tạo
- **Cộng đồng Open Source** - Các thư viện và công cụ được sử dụng

---

<p align="center">
  Made with ❤️ by Phạm Văn Phong
  <br>
  © 2026 Travel Agent P. All rights reserved.
</p>
