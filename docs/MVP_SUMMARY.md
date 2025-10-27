# Travel Agent P - MVP Planning & Architecture Summary

> **Document Version:** 1.0  
> **Created:** October 27, 2025  
> **Status:** ✅ Planning Phase Complete - Ready for Implementation

---

## 📋 Executive Summary

Đã hoàn thành giai đoạn thiết kế kiến trúc MVP cho dự án **Travel Agent P** - một nền tảng AI-powered travel planning. Tài liệu này tổng hợp toàn bộ quyết định thiết kế, schemas, acceptance criteria, và deliverables đã tạo.

### 🎯 MVP Scope
- ✅ **AC-001:** User Authentication (Register, Verify Email, Login, OAuth, Logout) - **HOÀN THÀNH**
- 🔄 **AC-002:** POI Management (Search, Details, Deduplication, Categories)
- 🔄 **AC-003:** AI Itinerary Planning (Generate, History, Edit, Share)
- 🔄 **AC-004:** Elasticsearch Search (Optional - Fuzzy, Multi-language)

### 📊 Success Metrics
- **API Response Time:** < 500ms (p95)
- **AI Generation Time:** < 30s per itinerary
- **Redis Cache Hit Rate:** > 70%
- **POI Deduplication Accuracy:** > 95%

---

## 🏗️ Tech Stack Architecture

### Backend Services
```
┌─────────────────────────────────────────────────┐
│              Client Layer                       │
│  React Web │ Mobile App │ Admin Dashboard       │
└─────────────────┬───────────────────────────────┘
                  │ HTTPS/REST
┌─────────────────▼───────────────────────────────┐
│           API Gateway (Flask)                   │
│  Middleware: Auth │ Rate Limit │ CORS │ Logging │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Service Layer                      │
│  Auth │ POI │ Itinerary │ User │ Search         │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│           Repository Layer                      │
│  PG Repo │ Mongo Repo │ Redis Repo │ ES Repo    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              Data Layer                         │
│  PostgreSQL │ MongoDB │ Redis │ Elasticsearch   │
│  Users/Auth │ POI/Itin│ Cache │ Full-text       │
└──────────────────────────────────────────────────┘
```

### Database Strategy

| Database | Purpose | Data Types | Why? |
|----------|---------|------------|------|
| **PostgreSQL** | Relational data | Users, roles, tokens, bookings | ACID compliance, strong relationships |
| **MongoDB** | Document store | POI, itineraries, reviews | Flexible schema, GeoJSON support |
| **Redis** | Multi-purpose | Blacklist, rate limit, cache, queue | Speed (O(1) ops), TTL auto-cleanup |
| **Elasticsearch** | Full-text search | POI index (optional) | Fuzzy matching, Vietnamese analyzer |

### Tech Stack Details

#### Core Framework
- **Flask 3.1.1** - REST API server
- **Python 3.10+** - Programming language
- **Gunicorn** - WSGI production server

#### Databases & Storage
- **PostgreSQL 12+** - Relational data
- **MongoDB 6.0+** - Document store
- **Redis 5.0+** - Cache + Queue
- **Firebase Storage** - Images/avatars
- **Elasticsearch 8.x** - Optional full-text search

#### AI/ML Stack
- **LangChain 0.1.0+** - AI orchestration
- **HuggingFace Transformers** - Embeddings
- **sentence-transformers/all-MiniLM-L6-v2** - 384-dim embeddings
- **OpenAI GPT-4 Turbo** - LLM for itinerary generation

#### Async Processing
- **Celery 5.5.2** - Task queue
- **Redis** - Message broker + result backend
- **Celery Beat** - Scheduled tasks

#### Supporting Libraries
```python
# Database
psycopg2-binary==2.9.9    # PostgreSQL adapter
pymongo==4.6.0            # MongoDB driver
redis==5.0.1              # Redis client
SQLAlchemy==2.0.25        # ORM

# AI/ML
langchain==0.1.0
sentence-transformers==2.3.1
openai==1.10.0
transformers==4.36.0

# Deduplication
unidecode==1.3.8          # Unicode normalization
pygeohash==1.2.1          # Geohash encoding
python-Levenshtein==0.25.0 # Fuzzy matching
geopy==2.4.1              # Distance calculation

# Async
celery[redis]==5.5.2
kombu==5.3.5

# Auth & Security
Flask-JWT-Extended==4.6.0
bcrypt==4.1.2

# API & Validation
marshmallow==3.20.1
jsonschema==4.20.0

# Utilities
python-dotenv==1.0.0
```

---

## 📐 Data Models & Schemas

### 1. JSON Schema: AI Itinerary Output
**File:** `docs/schemas/plan_v1.json` (225 lines)

**Purpose:** Enforce structure for LLM-generated itineraries

**Key Structure:**
```json
{
  "plan_id": "itin_xyz789",
  "destination": {
    "city": "Da Nang",
    "country": "Vietnam"
  },
  "duration": {"days": 3, "nights": 2},
  "budget": {
    "total": 5000000,
    "currency": "VND",
    "breakdown": {...}
  },
  "days": [
    {
      "day_number": 1,
      "date": "2025-11-01",
      "theme": "Beach Relaxation",
      "activities": [
        {
          "time_slot": "morning",
          "start_time": "09:00",
          "duration_minutes": 120,
          "activity_type": "visit_poi",
          "poi": {
            "poi_id": "poi_mykhebeach",
            "name": "Mỹ Khê Beach",
            "location": {"lat": 16.0544, "lng": 108.2428},
            "estimated_cost": {"amount": 0, "currency": "VND"}
          },
          "description": "...",
          "tips": [...]
        }
      ]
    }
  ]
}
```

**Validation Rules:**
- Required fields: `plan_id`, `destination`, `duration`, `budget`, `days[]`
- Enums: `time_slot` (morning/afternoon/evening), `activity_type` (visit_poi/meal/transport/other)
- Min/Max: `duration.days` (1-30), `budget.total` (> 0)
- Patterns: `plan_id` matches `^itin_[a-z0-9]+$`

### 2. POI Unified Model
**File:** `docs/schemas/poi_unified.json` (292 lines)

**Purpose:** Single source of truth for POI from multiple data sources

**Key Features:**
- **Deduplication Key:** `dedupe_key = normalize(name) + geohash(lat,lng,7)` (~150m precision)
- **GeoJSON Location:** MongoDB 2dsphere index for geo queries
- **Multi-source Tracking:** `sources[]` array tracks Google Places, TripAdvisor, etc.
- **Embeddings:** 384-dim vector for semantic search
- **Rich Metadata:** Ratings, pricing, hours, amenities

**Schema Structure:**
```json
{
  "poi_id": "poi_mykhebeach",
  "dedupe_key": "mykhebeach_wecq6uk",  // UNIQUE INDEX
  "name": "Mỹ Khê Beach",
  "name_unaccented": "my khe beach",
  "location": {  // 2dsphere INDEX
    "type": "Point",
    "coordinates": [108.2428, 16.0544]  // [lng, lat]
  },
  "address": {...},
  "categories": ["beach", "nature"],  // INDEX
  "ratings": {
    "average": 4.7,
    "count": 15234,
    "breakdown": {...}
  },
  "pricing": {
    "level": "free",  // free, cheap, moderate, expensive
    "entrance_fee": {...}
  },
  "opening_hours": {...},
  "images": [...],
  "embeddings": {
    "model": "all-MiniLM-L6-v2",
    "vector": [0.123, -0.456, ...],  // 384 dims
    "generated_at": "2025-10-27T10:00:00Z"
  },
  "sources": [
    {
      "provider": "google_places",
      "external_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
      "confidence": 0.95,
      "fetched_at": "2025-10-27T10:00:00Z"
    }
  ],
  "metadata": {
    "created_at": "2025-10-27T10:00:00Z",
    "updated_at": "2025-10-27T10:30:00Z",
    "verified": true,
    "popularity_score": 87.5,
    "view_count": 5001
  }
}
```

**MongoDB Indexes:**
```javascript
// Unique deduplication key
db.poi.createIndex({"dedupe_key": 1}, {unique: true})

// GeoJSON 2dsphere for location queries
db.poi.createIndex({"location": "2dsphere"})

// Category filter
db.poi.createIndex({"categories": 1})

// Text search (fallback if no Elasticsearch)
db.poi.createIndex({
  "name": "text",
  "name_unaccented": "text",
  "description.short": "text"
})

// Popularity & sorting
db.poi.createIndex({"metadata.popularity_score": -1})
db.poi.createIndex({"ratings.average": -1})
```

### 3. POI Deduplication Algorithm
**File:** `server/app/utils/poi_dedupe.py` (165 lines)

**Purpose:** Prevent duplicate POI entries from multiple data sources

**Core Functions:**
```python
def generate_dedupe_key(name: str, lat: float, lng: float, precision: int = 7) -> str:
    """
    Generate unique deduplication key.
    
    Algorithm:
    1. Normalize name: lowercase + remove accents + clean special chars
    2. Encode location: geohash(lat, lng, precision=7) → ~150m precision
    3. Combine: "{normalized_name}_{geohash}"
    
    Example:
    Input: "Mỹ Khê Beach", 16.0544, 108.2428
    Output: "mykhebeach_wecq6uk"
    """
    normalized = normalize_poi_name(name)
    geohash = pygeohash.encode(latitude=lat, longitude=lng, precision=precision)
    return f"{normalized}_{geohash}"

def normalize_poi_name(name: str) -> str:
    """
    Normalize POI name for comparison.
    
    Steps:
    1. Remove accents: "Mỹ Khê" → "My Khe"
    2. Lowercase: "My Khe" → "my khe"
    3. Remove special chars: "my-khe beach!" → "mykhe beach"
    4. Strip whitespace & deduplicate spaces
    5. Slug-ify: "mykhe beach" → "mykhebeach"
    """
    # Remove accents using unidecode
    unaccented = unidecode.unidecode(name)
    # Lowercase
    lower = unaccented.lower()
    # Remove non-alphanumeric (keep spaces)
    cleaned = re.sub(r'[^a-z0-9\s]', '', lower)
    # Remove extra spaces
    spaced = re.sub(r'\s+', '', cleaned)
    return spaced

def are_pois_duplicate(poi1: dict, poi2: dict, 
                       name_threshold: float = 0.85, 
                       distance_threshold_m: float = 150) -> bool:
    """
    Fuzzy check if two POIs are duplicates.
    
    Criteria (both must match):
    1. Name similarity > 85% (Levenshtein ratio)
    2. Distance < 150 meters (geodesic)
    
    Returns: True if duplicate, False otherwise
    """
    # Name similarity using Levenshtein
    name1 = normalize_poi_name(poi1['name'])
    name2 = normalize_poi_name(poi2['name'])
    name_ratio = Levenshtein.ratio(name1, name2)
    
    # Distance using geopy
    loc1 = (poi1['location']['coordinates'][1], poi1['location']['coordinates'][0])
    loc2 = (poi2['location']['coordinates'][1], poi2['location']['coordinates'][0])
    distance_m = geodesic(loc1, loc2).meters
    
    return name_ratio >= name_threshold and distance_m <= distance_threshold_m
```

**Why Geohash Precision 7?**
- Precision 6: ~1.2 km (too loose, many false positives)
- **Precision 7: ~150 m (OPTIMAL for tourist POI)**
- Precision 8: ~38 m (too strict, misses same building)

**Deduplication Strategy:**
1. **Strict (Primary):** Insert with unique `dedupe_key` → MongoDB rejects duplicates
2. **Fuzzy (Fallback):** Before insert, check `are_pois_duplicate()` against nearby POI
3. **Merge:** If duplicate found, merge ratings/sources from new provider

---

## 📝 Acceptance Criteria

**File:** `docs/MVP_ACCEPTANCE_CRITERIA.md` (450 lines)

### AC-001: User Authentication ✅ **COMPLETE**

| Feature | Endpoint | Status |
|---------|----------|--------|
| Register | POST `/api/auth/register` | ✅ Done |
| Verify Email | POST `/api/auth/verify-email` | ✅ Done |
| Login | POST `/api/auth/login` | ✅ Done |
| Refresh Token | POST `/api/auth/refresh` | ✅ Done |
| Logout | POST `/api/auth/logout` | ✅ Done |
| Google OAuth | POST `/api/auth/google` | ✅ Done |

**Test Cases:**
- [x] Register with valid email → 201 + verification email sent
- [x] Register with duplicate email → 409 Conflict
- [x] Verify with correct code → 200 + `is_verified=true`
- [x] Login unverified user → 403 Forbidden
- [x] Login with wrong password (5x) → 429 Rate Limited (300s)
- [x] Access protected endpoint → 401 if no token
- [x] Logout → Token added to Redis blacklist
- [x] Reuse blacklisted token → 401 Unauthorized

### AC-002: POI Management 🔄 **IN PROGRESS**

| Feature | Endpoint | Status |
|---------|----------|--------|
| Search POI | GET `/api/poi/search` | 🔄 To Do |
| POI Details | GET `/api/poi/{poi_id}` | 🔄 To Do |
| Add POI (Admin) | POST `/api/admin/poi` | 🔄 To Do |
| Update POI | PATCH `/api/admin/poi/{poi_id}` | 🔄 To Do |

**Test Cases:**
- [ ] Search by text → Returns relevant POI sorted by relevance
- [ ] Search by location (lat/lng/radius) → Returns nearby POI within radius
- [ ] Search with filters (categories, price_level) → Filtered results
- [ ] Get POI details → Full POI object with images, ratings, hours
- [ ] Add POI with duplicate dedupe_key → 409 Conflict
- [ ] Add POI from different provider (same place) → Merge sources
- [ ] Fuzzy duplicate detection → Nearby POI with similar name merged

### AC-003: AI Itinerary Planning 🔄 **IN PROGRESS**

| Feature | Endpoint | Status |
|---------|----------|--------|
| Generate Itinerary | POST `/api/itinerary/generate` | 🔄 To Do |
| Get Generation Status | GET `/api/itinerary/status/{job_id}` | 🔄 To Do |
| Get Itinerary | GET `/api/itinerary/{plan_id}` | 🔄 To Do |
| List My Itineraries | GET `/api/itinerary/my-itineraries` | 🔄 To Do |
| Share Itinerary | GET `/share/{plan_id}` | 🔄 To Do |

**Test Cases:**
- [ ] Generate itinerary → 202 Accepted + `job_id`
- [ ] Poll status → Shows progress (selecting POI, generating plan...)
- [ ] Generation completes < 30s → 200 + `itinerary_id`
- [ ] Generated plan matches JSON Schema → Validation passes
- [ ] Plan respects budget constraint → Total cost <= budget
- [ ] POI selected match interests → Categories align with preferences
- [ ] Get itinerary → Full plan with days[], activities[], tips[]
- [ ] Share itinerary → Public link (no auth required)

### AC-004: Elasticsearch Search 🔄 **OPTIONAL**

| Feature | Status |
|---------|--------|
| Vietnamese text analyzer | 🔄 Optional |
| Fuzzy matching | 🔄 Optional |
| Typo tolerance | 🔄 Optional |

**Test Cases:**
- [ ] Search "bai bien" → Matches "Bãi biển" (accent insensitive)
- [ ] Search "my keh" → Matches "Mỹ Khê" (typo tolerance)
- [ ] Search "beach danang" → Multi-language mixed query works

---

## 📊 Deliverables Summary

### 1. ✅ Architecture Diagram
**File:** `docs/ARCHITECTURE_DIAGRAM.md` (180 lines)

**Components:**
- Client Layer (React Web, Mobile, Admin)
- API Gateway (Flask + Middleware)
- Service Layer (Auth, POI, Itinerary, User, Search)
- Repository Layer (PG/Mongo/Redis/ES Repos)
- Data Layer (PostgreSQL, MongoDB, Redis, Elasticsearch)
- Async Processing (Celery Workers)
- AI/ML Layer (LangChain + HuggingFace)

**Data Flow Examples:**
- Registration Flow (Flask → PG → Celery → Email)
- Login Flow (Flask → PG → Redis blacklist check → JWT)
- POI Search Flow (Flask → Mongo 2dsphere → Redis cache)
- AI Generation Flow (Flask → Celery → LangChain → OpenAI → Mongo)
- Logout Flow (Flask → Redis blacklist → 204 No Content)

### 2. ✅ ERD & Database Schemas
**File:** `docs/ERD_DATABASE_SCHEMA.md` (350 lines)

**PostgreSQL Tables:**
```sql
-- Users & Authentication
users (id, email, username, password_hash, is_verified, auth_provider, created_at)
roles (id, name, description)
user_roles (user_id, role_id)
tokens (id, user_id, token_type, token_hash, expires_at, is_revoked)
login_attempts (id, email, ip_address, attempted_at, success)

-- Future: Bookings
bookings (id, user_id, itinerary_id, status, created_at)
```

**MongoDB Collections:**
```javascript
// POI
{
  poi_id: "poi_mykhebeach",
  dedupe_key: "mykhebeach_wecq6uk",  // UNIQUE
  name: "Mỹ Khê Beach",
  location: {type: "Point", coordinates: [108.2428, 16.0544]},  // 2dsphere
  categories: ["beach"],
  ratings: {...},
  embeddings: {vector: [...], model: "all-MiniLM-L6-v2"}
}

// Itineraries
{
  plan_id: "itin_xyz789",
  user_id: "user_123",
  destination: {...},
  days: [{activities: [...]}],
  metadata: {is_public: false, share_token: null}
}

// Reviews (Future)
{
  review_id: "rev_abc",
  user_id: "user_123",
  poi_id: "poi_mykhebeach",
  rating: 5,
  comment: "Beautiful beach!"
}
```

**Redis Key Patterns:**
```
# JWT Blacklist
blacklist:{jti} → {user_id} (TTL: token expiry)

# Rate Limiting
rate_limit:login:{ip} → sorted_set (TTL: window)
rate_limit:register:{email} → sorted_set

# Cache
cache:poi:{poi_id} → JSON (TTL: 3600s)
cache:search:{hash} → JSON (TTL: 600s)
cache:user:{user_id}:profile → JSON (TTL: 300s)

# Session
session:{user_id} → JSON (TTL: 86400s)

# Celery (internal)
celery-task-meta-{task_id} → JSON
```

**Elasticsearch Index:**
```json
{
  "mappings": {
    "properties": {
      "poi_id": {"type": "keyword"},
      "name": {
        "type": "text",
        "analyzer": "vietnamese",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "name_unaccented": {"type": "text", "analyzer": "standard"},
      "location": {"type": "geo_point"},
      "categories": {"type": "keyword"},
      "ratings_average": {"type": "float"},
      "popularity_score": {"type": "float"}
    }
  }
}
```

### 3. ✅ API Payload Examples
**File:** `docs/API_PAYLOAD_EXAMPLES.md` (500+ lines)

**Includes:**
- Request/response for 11 API endpoints
- Success responses (200, 201, 202, 204)
- Error responses (401, 409, 429)
- Rate limit headers
- Pagination examples
- Async job polling examples

### 4. ✅ Environment Variables
**File:** `server/.env.example` (400+ lines)

**Sections:**
- Application settings (Flask, debug, timezone)
- PostgreSQL (connection, pool settings)
- MongoDB (URI, collections, indexes)
- Redis (connection, TTL, prefixes)
- Cache configuration
- Rate limiting rules
- JWT settings
- Celery (broker, backend, concurrency)
- Email (SMTP, templates)
- Firebase (storage buckets)
- HuggingFace (API key, models)
- LangChain (LLM provider, OpenAI)
- Elasticsearch (optional)
- External APIs (Google Places/Maps, Weather, Exchange Rate)
- OAuth (Google, Facebook)
- CORS, Logging, Security
- Monitoring (Sentry, GA, App Insights)
- Performance tuning
- Feature flags
- Development tools (Swagger, debug toolbar)

### 5. ✅ JSON Schemas
**Files:**
- `docs/schemas/plan_v1.json` (225 lines) - Itinerary output
- `docs/schemas/poi_unified.json` (292 lines) - POI model

### 6. ✅ Deduplication Algorithm
**File:** `server/app/utils/poi_dedupe.py` (165 lines)

---

## 🚀 Implementation Roadmap

### Week 1-2: POI Foundation (CURRENT SPRINT)
**Priority: HIGH**

1. **MongoDB Setup**
   - [x] Install `pymongo`, `motor` (async)
   - [ ] Create `server/app/core/mongodb_client.py` (Singleton pattern)
   - [ ] Create `server/app/repo/poi_repository.py` (CRUD operations)
   - [ ] Create MongoDB indexes (dedupe_key, location 2dsphere, categories)

2. **POI Model Implementation**
   - [ ] Create `server/app/model/poi.py` (Pydantic model)
   - [ ] Implement `POIService` with deduplication logic
   - [ ] Create `server/app/controller/poi_controller.py`
   - [ ] Unit tests for deduplication algorithm

3. **POI Search Endpoints**
   - [ ] `GET /api/poi/search` (text + geo + filters)
   - [ ] `GET /api/poi/{poi_id}` (details)
   - [ ] `POST /api/admin/poi` (add POI with dedupe check)
   - [ ] `PATCH /api/admin/poi/{poi_id}` (update)

4. **POI Data Seeding**
   - [ ] Create `scripts/seed_vietnam_poi.py`
   - [ ] Top 100 Vietnam attractions (Ha Noi, Da Nang, Ho Chi Minh, etc.)
   - [ ] Generate embeddings with HuggingFace

**Deliverables:**
- POI CRUD APIs functional
- 100+ Vietnam POI seeded
- Deduplication tested (< 1% false positives)

### Week 3-4: AI Itinerary Generation
**Priority: HIGH**

1. **LangChain Setup**
   - [ ] Install `langchain`, `openai`, `sentence-transformers`
   - [ ] Create `server/app/ai/langchain_client.py`
   - [ ] Create prompt templates for itinerary generation
   - [ ] Test JSON Schema enforcement

2. **Itinerary Service**
   - [ ] Create `server/app/model/itinerary.py` (Pydantic)
   - [ ] Create `server/app/repo/itinerary_repository.py` (Mongo)
   - [ ] Create `server/app/service/itinerary_service.py`
   - [ ] Implement Celery task: `generate_itinerary_task()`

3. **Itinerary Endpoints**
   - [ ] `POST /api/itinerary/generate` (submit job)
   - [ ] `GET /api/itinerary/status/{job_id}` (poll status)
   - [ ] `GET /api/itinerary/{plan_id}` (get details)
   - [ ] `GET /api/itinerary/my-itineraries` (list user's plans)
   - [ ] `GET /share/{plan_id}` (public share link)

4. **AI Testing**
   - [ ] Test prompt engineering (clear, detailed plans)
   - [ ] Validate JSON Schema compliance (100% valid outputs)
   - [ ] Test budget constraints (cost <= budget)
   - [ ] Test interest matching (POI categories align)

**Deliverables:**
- AI generates 3-day itinerary in < 30s
- Plans validate against JSON Schema
- User can view history and share plans

### Week 5-6: Search & Performance
**Priority: MEDIUM**

1. **Elasticsearch Setup (Optional)**
   - [ ] Install Elasticsearch 8.x
   - [ ] Create index with Vietnamese analyzer
   - [ ] Sync POI data from MongoDB
   - [ ] Create `server/app/repo/es_repository.py`

2. **Advanced Search**
   - [ ] Fuzzy matching (typo tolerance)
   - [ ] Multi-language support (Vietnamese + English)
   - [ ] Weighted scoring (popularity, ratings, distance)
   - [ ] Search suggestions / autocomplete

3. **Caching Strategy**
   - [ ] Cache POI details (TTL: 1h)
   - [ ] Cache search results (TTL: 10min)
   - [ ] Cache user profile (TTL: 5min)
   - [ ] Invalidation on updates

4. **Performance Optimization**
   - [ ] Load testing (100 concurrent users)
   - [ ] Query optimization (explain plans)
   - [ ] Connection pooling tuning
   - [ ] CDN for Firebase images

**Deliverables:**
- Search handles typos ("my keh" → "Mỹ Khê")
- API p95 < 500ms
- Redis cache hit rate > 70%

### Week 7-8: Polish & Launch Prep
**Priority: MEDIUM**

1. **Admin Panel**
   - [ ] POI management (CRUD, approve/reject)
   - [ ] User management (ban, roles)
   - [ ] Analytics dashboard (API usage, top POI, etc.)

2. **Testing & QA**
   - [ ] Integration tests (full user flows)
   - [ ] Load tests (JMeter / Locust)
   - [ ] Security audit (OWASP Top 10)
   - [ ] Penetration testing

3. **Documentation**
   - [ ] API documentation (Swagger/OpenAPI)
   - [ ] Developer onboarding guide
   - [ ] Deployment guide (Docker Compose)
   - [ ] User guide (screenshots)

4. **DevOps**
   - [ ] CI/CD pipeline (GitHub Actions)
   - [ ] Docker Compose for local dev
   - [ ] Production deployment (AWS/Azure/GCP)
   - [ ] Monitoring (Sentry, logs, metrics)

**Deliverables:**
- MVP ready for alpha testing
- All tests passing (unit + integration)
- Production deployment successful

---

## 🔐 Security Considerations

### Authentication & Authorization
- ✅ **Bcrypt** password hashing (12 rounds)
- ✅ **JWT** with short expiry (1h access, 30d refresh)
- ✅ **Redis blacklist** for logged-out tokens
- ✅ **Rate limiting** on auth endpoints (5 login attempts / 5min)
- ✅ **CORS** configured for allowed origins only

### Data Protection
- 🔒 **HTTPS** only in production (TLS 1.3)
- 🔒 **Environment variables** for secrets (never hardcode)
- 🔒 **Firebase rules** for storage (authenticated uploads only)
- 🔒 **Input validation** with Marshmallow/Pydantic
- 🔒 **SQL injection prevention** (SQLAlchemy ORM)

### API Security
- 🔒 **Rate limiting** per endpoint (prevent abuse)
- 🔒 **Request size limits** (16MB max)
- 🔒 **Token expiry** auto-cleanup (Redis TTL)
- 🔒 **CSRF protection** (for web forms)
- 🔒 **Content Security Policy** (CSP headers)

### Monitoring
- 📊 **Sentry** for error tracking
- 📊 **Structured logging** (JSON format)
- 📊 **API metrics** (response time, error rate)
- 📊 **Security logs** (failed login attempts, suspicious activity)

---

## 📈 Performance Targets

### API Response Time
| Endpoint | Target (p95) | Current | Status |
|----------|--------------|---------|--------|
| GET `/api/poi/search` | < 200ms | TBD | 🔄 |
| GET `/api/poi/{id}` | < 100ms | TBD | 🔄 |
| POST `/api/itinerary/generate` | < 50ms | TBD | 🔄 |
| GET `/api/itinerary/{id}` | < 150ms | TBD | 🔄 |

### Background Tasks
| Task | Target | Current | Status |
|------|--------|---------|--------|
| AI Itinerary Generation | < 30s | TBD | 🔄 |
| Email Sending | < 5s | TBD | 🔄 |
| POI Embedding Generation | < 10s | TBD | 🔄 |

### Cache Performance
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Redis Hit Rate | > 70% | TBD | 🔄 |
| Cache Latency (p95) | < 10ms | TBD | 🔄 |
| POI Cache Hit Rate | > 80% | TBD | 🔄 |

### Database Performance
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| PG Connection Pool Usage | < 80% | TBD | 🔄 |
| Mongo Query Time (p95) | < 50ms | TBD | 🔄 |
| Redis Command Time (p95) | < 5ms | TBD | 🔄 |

---

## 🧪 Testing Strategy

### Unit Tests
```bash
# Run all unit tests
pytest tests/unit/

# Tests to write:
# - POI deduplication algorithm (strict + fuzzy)
# - JWT blacklist operations
# - Rate limiter logic
# - Cache helper functions
# - AI prompt template rendering
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/

# Tests to write:
# - Full auth flow (register → verify → login → logout)
# - POI search with filters
# - AI itinerary generation end-to-end
# - Cache hit/miss scenarios
# - Database transactions
```

### Load Tests
```bash
# Run load tests (Locust)
locust -f tests/load/locustfile.py

# Scenarios:
# - 100 concurrent users searching POI
# - 50 users generating itineraries simultaneously
# - Cache effectiveness under load
```

### Test Coverage Target
- **Unit Tests:** > 80% coverage
- **Integration Tests:** All critical paths
- **Load Tests:** Passes with 100 concurrent users

---

## 📦 Dependencies to Install

### Python Packages (Week 1-2)
```bash
# MongoDB
pip install pymongo==4.6.0
pip install motor==3.3.2  # Async MongoDB driver

# Deduplication
pip install unidecode==1.3.8
pip install pygeohash==1.2.1
pip install python-Levenshtein==0.25.0
pip install geopy==2.4.1

# Validation
pip install pydantic==2.5.3
pip install jsonschema==4.20.0
```

### Python Packages (Week 3-4)
```bash
# AI/ML
pip install langchain==0.1.0
pip install openai==1.10.0
pip install sentence-transformers==2.3.1
pip install transformers==4.36.0
pip install torch==2.1.2  # For embeddings

# Async tasks
pip install celery[redis]==5.5.2
pip install kombu==5.3.5
```

### Python Packages (Week 5-6)
```bash
# Elasticsearch
pip install elasticsearch==8.11.1

# Performance
pip install gunicorn==21.2.0
pip install gevent==23.9.1
```

### Infrastructure Services
```bash
# PostgreSQL 12+
# Already running ✅

# Redis 5.0+
# Already running ✅

# MongoDB 6.0+
docker run -d -p 27017:27017 --name mongodb mongo:6.0

# Elasticsearch 8.x (Optional)
docker run -d -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  --name elasticsearch elasticsearch:8.11.1
```

---

## 🎓 Key Learnings & Design Decisions

### 1. Why Multiple Databases?
**Decision:** PostgreSQL + MongoDB + Redis

**Rationale:**
- **PostgreSQL:** ACID transactions for user auth, payments (critical data)
- **MongoDB:** Flexible schema for POI, itineraries (evolving data model)
- **Redis:** Speed (O(1)) for cache, blacklist, rate limiting

**Alternative Rejected:**
- Single SQL DB → No GeoJSON support, slow for document queries
- Single NoSQL DB → No ACID for payments, complex joins

### 2. Why Geohash for Deduplication?
**Decision:** `dedupe_key = normalize(name) + geohash(lat,lng,7)`

**Rationale:**
- Precision 7 (~150m) perfect for tourist POI (same building = duplicate)
- Handles coordinate drift from different providers (±50m GPS error)
- Fast: O(1) unique index check vs. O(n) distance calculation

**Alternative Rejected:**
- Exact coordinates → Fails due to GPS drift
- Precision 8 (~38m) → Too strict, misses duplicates in same complex

### 3. Why JSON Schema for AI Output?
**Decision:** Enforce structure via `plan_v1.json`

**Rationale:**
- LLMs hallucinate unpredictable JSON structures
- Validation prevents broken frontend rendering
- Forces inclusion of critical fields (budget, duration, POI IDs)

**Alternative Rejected:**
- Freeform output → 30% invalid JSON, missing fields
- Post-processing → Too slow, can't fix missing data

### 4. Why Redis as Message Broker?
**Decision:** Redis for both cache AND Celery queue

**Rationale:**
- Single service → Less infrastructure complexity
- Fast (in-memory)
- Built-in TTL for auto-cleanup

**Alternative Rejected:**
- RabbitMQ → Overkill for MVP, another service to manage
- AWS SQS → Vendor lock-in, higher cost

### 5. Why Elasticsearch is Optional?
**Decision:** MongoDB text search for MVP, ES for v2

**Rationale:**
- MongoDB text search covers 80% of needs (basic search)
- ES adds infrastructure complexity (indexing, sync)
- Vietnamese analyzer requires custom config

**When to Add ES:**
- Traffic > 10k daily searches
- Users complain about typo handling
- Need advanced features (suggestions, fuzzy match)

---

## 📞 Next Steps & Open Questions

### Immediate Actions (This Week)
1. ✅ Review this summary document
2. 🔄 Install MongoDB + pymongo
3. 🔄 Create MongoDB connection helper
4. 🔄 Implement POI repository
5. 🔄 Create POI CRUD endpoints

### Open Questions
1. **HuggingFace API Key:** Do we use free tier or paid? (Rate limits)
2. **OpenAI Model:** GPT-4 Turbo ($0.01/1K tokens) or GPT-3.5 ($0.0015/1K tokens)?
3. **Vietnam POI Data Source:** Scrape Google Places or buy dataset?
4. **Image Storage:** Firebase Storage or S3? (Cost comparison)
5. **Deployment:** Docker Compose or Kubernetes? (Complexity vs. scalability)

### Future Features (Post-MVP)
- 💡 User reviews & ratings
- 💡 Booking integration (hotels, flights)
- 💡 Payment processing (VNPay, MoMo)
- 💡 Social features (follow travelers, share itineraries)
- 💡 Mobile app (React Native)
- 💡 Offline mode (PWA with service workers)
- 💡 Real-time chat support (WebSocket)
- 💡 Multi-language support (EN, VI, JP, KR, CN)

---

## 📚 Reference Documents

| Document | File Path | Lines | Purpose |
|----------|-----------|-------|---------|
| **Architecture Diagram** | `docs/ARCHITECTURE_DIAGRAM.md` | 180 | System layers & data flows |
| **ERD & Schemas** | `docs/ERD_DATABASE_SCHEMA.md` | 350 | Database design (PG, Mongo, Redis, ES) |
| **Acceptance Criteria** | `docs/MVP_ACCEPTANCE_CRITERIA.md` | 450 | Feature requirements & test cases |
| **API Payload Examples** | `docs/API_PAYLOAD_EXAMPLES.md` | 500+ | Request/response samples |
| **JSON Schema: Itinerary** | `docs/schemas/plan_v1.json` | 225 | AI output structure |
| **JSON Schema: POI** | `docs/schemas/poi_unified.json` | 292 | POI data model |
| **Deduplication Algorithm** | `server/app/utils/poi_dedupe.py` | 165 | POI dedupe logic |
| **Environment Variables** | `server/.env.example` | 400+ | Configuration template |
| **Redis Setup Guide** | `docs/REDIS_SETUP.md` | 300+ | Redis integration (previous) |

---

## ✅ Sign-Off

**Planning Phase Status:** ✅ **COMPLETE**

**Next Phase:** 🚀 **Implementation (Week 1-2: POI Foundation)**

**Estimated MVP Completion:** 8 weeks from start (Week of Dec 22, 2025)

**Team:** Ready to proceed with MongoDB setup and POI implementation.

---

*Document End. For questions, refer to individual docs or contact project lead.*
