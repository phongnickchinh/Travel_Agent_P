# Travel Agent P - MVP Acceptance Criteria (AC)

## 📋 OVERVIEW

**MVP Goal:** Hệ thống AI planning cơ bản với POI search và itinerary generation

**Timeline:** 4-6 weeks
**Target Users:** Vietnamese travelers planning domestic trips

---

## ✅ AC-001: User Authentication & Authorization

### **User Stories:**
- **US-001:** As a user, I can register with email/password
- **US-002:** As a user, I can verify my email before logging in
- **US-003:** As a user, I can login with verified account
- **US-004:** As a user, I can login with Google OAuth
- **US-005:** As a user, I can logout and invalidate my tokens

### **Acceptance Criteria:**

#### ✅ AC-001.1: Registration
- [ ] User can register with: email, password, username, full name
- [ ] Password must be 6-20 characters
- [ ] Email verification code sent via email (Celery async)
- [ ] Rate limit: 3 registrations per hour per IP
- [ ] Returns: `confirmToken` (no access/refresh tokens)
- [ ] User created with `is_verified=false`

#### ✅ AC-001.2: Email Verification
- [ ] User can verify email with `confirmToken` + 6-digit code
- [ ] Verification code expires after 30 minutes
- [ ] After verify: `is_verified=true`
- [ ] Returns: success message (no tokens)
- [ ] Redirect to login page

#### ✅ AC-001.3: Login
- [ ] User cannot login if `is_verified=false`
- [ ] Returns 403 with "Please verify email" message
- [ ] Successful login returns: `access_token`, `refresh_token`, user info, role
- [ ] Rate limit: 5 attempts per 5 minutes per email
- [ ] Failed login increments attempt counter

#### ✅ AC-001.4: Google OAuth
- [ ] User can login with Google account
- [ ] Auto-verify email (Google verified)
- [ ] Link Google to existing email account
- [ ] Create new account if email not exists
- [ ] Update `auth_provider`: local/google/both

#### ✅ AC-001.5: Logout
- [ ] Access token added to Redis blacklist with TTL
- [ ] Refresh token deleted from PostgreSQL
- [ ] Blacklisted token returns 401 on subsequent requests
- [ ] Returns 204 No Content

#### ✅ AC-001.6: Token Refresh
- [ ] User can refresh access token with valid refresh token
- [ ] Refresh token validated against PostgreSQL
- [ ] Returns new `access_token`
- [ ] Old access token still valid until expiry

### **Technical Requirements:**
- PostgreSQL: users, roles, tokens tables
- Redis: blacklist, rate limiting
- JWT: access (1h), refresh (7d)
- Celery: async email sending
- Rate limiting headers: X-RateLimit-*

### **Test Cases:**
```bash
# TC-001: Register → Verify → Login
POST /register → 201 (confirmToken)
POST /verify-email → 200 (verified=true)
POST /login → 200 (access_token, refresh_token)

# TC-002: Login without verification
POST /register → 201
POST /login → 403 (EMAIL_NOT_VERIFIED)

# TC-003: Rate limiting
POST /login (6 times) → 429 (Rate limit exceeded)

# TC-004: Logout blacklist
POST /login → 200 (access_token)
POST /logout → 204
GET /user/profile (with old token) → 401 (Invalid token)
```

---

## ✅ AC-002: POI Management

### **User Stories:**
- **US-006:** As a user, I can search for POI by name/location
- **US-007:** As a user, I can view POI details
- **US-008:** As a user, I can filter POI by category/price
- **US-009:** As a admin, I can add/edit/delete POI

### **Acceptance Criteria:**

#### ✅ AC-002.1: POI Search
- [ ] Search by text query: "bãi biển đà nẵng"
- [ ] Search by location (lat/lng) + radius
- [ ] Search by category: beach, historical, restaurant, etc.
- [ ] Fuzzy matching: "hoi an" → "Hội An"
- [ ] Pagination: page, limit (default 20)
- [ ] Sort by: distance, popularity, rating
- [ ] Results cached in Redis (TTL 1 hour)

**Request:**
```json
GET /api/poi/search?q=bãi+biển&lat=16.0544&lng=108.2428&radius=10km&category=beach&page=1&limit=20

Response: 200
{
  "results": [
    {
      "poi_id": "poi_mykhebeach",
      "name": "Mỹ Khê Beach",
      "category": ["beach"],
      "distance_km": 2.5,
      "rating": 4.7,
      "location": {"lat": 16.0544, "lng": 108.2428}
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 20
}
```

#### ✅ AC-002.2: POI Details
- [ ] View full POI information by `poi_id`
- [ ] Returns: name, description, location, ratings, hours, pricing, images
- [ ] Increment `view_count` on each view
- [ ] Cache result in Redis (TTL 10 minutes)

**Request:**
```json
GET /api/poi/poi_mykhebeach

Response: 200
{
  "poi_id": "poi_mykhebeach",
  "name": "Mỹ Khê Beach",
  "description": {...},
  "location": {...},
  "ratings": {"average": 4.7, "count": 15234},
  "opening_hours": {...},
  "images": [...]
}
```

#### ✅ AC-002.3: POI Deduplication
- [ ] Auto-generate `dedupe_key` on POI creation
- [ ] Format: `normalize(name)_geohash(lat,lng,7)`
- [ ] Unique index on `dedupe_key` in MongoDB
- [ ] Reject duplicate POI with 409 Conflict
- [ ] Merge duplicate POI from multiple sources

**Example:**
```python
name = "Phố Cổ Hội An"
lat, lng = 15.8801, 108.3259
dedupe_key = "phocohoan_wecpueb"

# Try insert
db.poi.insert_one({
    "poi_id": "poi_new123",
    "name": name,
    "dedupe_key": dedupe_key,  # ← Unique constraint
    ...
})
# → E11000 duplicate key error (if exists)
```

#### ✅ AC-002.4: POI Categories
- [ ] Predefined categories: beach, historical, museum, restaurant, etc.
- [ ] POI can have multiple categories
- [ ] Filter POI by category (OR logic)
- [ ] Category hierarchy: historical → temple/palace/fortress

### **Technical Requirements:**
- MongoDB: poi collection with GeoJSON
- Redis: search results cache
- Indexes: dedupe_key (unique), location (2dsphere), categories, text
- Libraries: unidecode, pygeohash, geopy

### **Test Cases:**
```bash
# TC-005: Search POI
GET /api/poi/search?q=beach&lat=16.0544&lng=108.2428
→ 200 (results with distance)

# TC-006: View POI details
GET /api/poi/poi_mykhebeach
→ 200 (full details)

# TC-007: Duplicate prevention
POST /api/admin/poi (same dedupe_key)
→ 409 (Duplicate POI detected)
```

---

## ✅ AC-003: AI Itinerary Planning

### **User Stories:**
- **US-010:** As a user, I can generate AI itinerary with preferences
- **US-011:** As a user, I can view my itinerary history
- **US-012:** As a user, I can save/edit itinerary
- **US-013:** As a user, I can share itinerary link

### **Acceptance Criteria:**

#### ✅ AC-003.1: Generate Itinerary
- [ ] User inputs: destination, days, budget, interests
- [ ] AI generates day-by-day plan with POI
- [ ] Output follows `plan_v1.json` schema
- [ ] Each day has: morning/afternoon/evening activities
- [ ] POI selected based on: category match, distance optimization, budget fit
- [ ] Total cost estimate for trip
- [ ] Generation time < 30 seconds (async with Celery)

**Request:**
```json
POST /api/itinerary/generate
{
  "destination": {
    "city": "Da Nang",
    "country": "Vietnam"
  },
  "duration": {
    "days": 3,
    "nights": 2
  },
  "budget": {
    "total": 5000000,
    "currency": "VND"
  },
  "preferences": {
    "interests": ["beach", "cultural", "food"],
    "travel_style": "mid-range",
    "pace": "moderate"
  }
}

Response: 202 Accepted
{
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_time": 25
}

# Poll for result
GET /api/itinerary/status/job_abc123
Response: 200
{
  "status": "completed",
  "itinerary_id": "itin_xyz789"
}

# Get itinerary
GET /api/itinerary/itin_xyz789
Response: 200
{
  "plan_id": "itin_xyz789",
  "destination": {...},
  "days": [
    {
      "day_number": 1,
      "date": "2025-11-01",
      "theme": "Beach Day & Seafood",
      "activities": [
        {
          "time_slot": "morning",
          "start_time": "09:00",
          "duration_minutes": 120,
          "poi": {
            "poi_id": "poi_mykhebeach",
            "name": "Mỹ Khê Beach",
            "location": {...}
          },
          "description": "...",
          "tips": ["..."]
        }
      ]
    }
  ]
}
```

#### ✅ AC-003.2: Itinerary History
- [ ] User can view list of generated itineraries
- [ ] Sort by: created_at (newest first)
- [ ] Filter by: destination, dates
- [ ] Pagination: 10 per page
- [ ] Delete itinerary

#### ✅ AC-003.3: Edit Itinerary
- [ ] User can modify: POI, activities, times
- [ ] Re-calculate total cost after edit
- [ ] Save as new version (history tracking)
- [ ] Invalidate cache after edit

#### ✅ AC-003.4: Share Itinerary
- [ ] Generate public share link: `/share/itin_xyz789`
- [ ] Public link accessible without login
- [ ] Option to make itinerary private/public
- [ ] View count for shared itineraries

### **Technical Requirements:**
- MongoDB: itineraries collection
- Redis: job queue (Celery)
- LangChain: prompt engineering for LLM
- HuggingFace: text generation API (or OpenAI)
- JSON Schema validation: plan_v1.json

### **Test Cases:**
```bash
# TC-008: Generate itinerary
POST /api/itinerary/generate → 202 (job_id)
GET /api/itinerary/status/{job_id} → 200 (completed)
GET /api/itinerary/{itinerary_id} → 200 (full plan)

# TC-009: Edit itinerary
PATCH /api/itinerary/{itinerary_id} → 200 (updated)

# TC-010: Share itinerary
GET /share/{itinerary_id} → 200 (public view)
```

---

## ✅ AC-004: Search with Elasticsearch (Optional MVP)

### **User Stories:**
- **US-014:** As a user, I can search POI with typo tolerance
- **US-015:** As a user, I can search POI in multiple languages

### **Acceptance Criteria:**

#### ✅ AC-004.1: Fuzzy Search
- [ ] Search with typos: "hoi an" → "Hội An"
- [ ] Multi-language: "ancient town" → "Phố Cổ"
- [ ] Search with partial name: "my khe" → "Mỹ Khê Beach"
- [ ] Boost by popularity/rating

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
          "raw": {"type": "keyword"}
        }
      },
      "name_unaccented": {
        "type": "text",
        "analyzer": "standard"
      },
      "categories": {"type": "keyword"},
      "location": {"type": "geo_point"},
      "popularity_score": {"type": "float"}
    }
  }
}
```

**Query:**
```json
GET /poi/_search
{
  "query": {
    "multi_match": {
      "query": "hoi an beach",
      "fields": ["name^3", "name_unaccented^2", "description"],
      "fuzziness": "AUTO"
    }
  },
  "sort": [
    {"_score": "desc"},
    {"popularity_score": "desc"}
  ]
}
```

### **Technical Requirements:**
- Elasticsearch 8.x
- Vietnamese analyzer plugin
- Sync POI: MongoDB → Elasticsearch (change streams)
- Fallback to MongoDB text search if ES unavailable

### **Test Cases:**
```bash
# TC-011: Fuzzy search
GET /api/poi/search?q=hoi+an → 200 (Hội An results)

# TC-012: Multi-language
GET /api/poi/search?q=ancient+town → 200 (Phố Cổ results)
```

---

## 📊 MVP Success Metrics

### **Functional Metrics:**
- [ ] 100% AC coverage with passing tests
- [ ] API response time < 500ms (p95)
- [ ] Itinerary generation < 30s
- [ ] Search results relevance > 80%

### **Technical Metrics:**
- [ ] Redis hit rate > 70%
- [ ] POI deduplication accuracy > 95%
- [ ] Zero security vulnerabilities (High/Critical)
- [ ] Test coverage > 80%

### **User Metrics (Post-Launch):**
- [ ] 100 registered users in first month
- [ ] 50 itineraries generated per week
- [ ] 70% user satisfaction score
- [ ] 30% return user rate

---

## 🚀 MVP Roadmap

### **Week 1-2: Foundation**
- [ ] Setup tech stack (PG, Mongo, Redis, HF)
- [ ] Implement AC-001 (Auth) - DONE ✅
- [ ] Setup CI/CD pipeline
- [ ] Database schema & migrations

### **Week 3-4: POI Management**
- [ ] Implement AC-002.1-002.2 (POI Search & Details)
- [ ] Implement AC-002.3 (Deduplication)
- [ ] Seed initial POI data (Top 100 Vietnam POI)
- [ ] Admin panel for POI management

### **Week 5-6: AI Planning**
- [ ] Implement AC-003.1 (Generate Itinerary)
- [ ] LangChain integration with HuggingFace
- [ ] JSON Schema validation
- [ ] Implement AC-003.2-003.4 (History, Edit, Share)

### **Week 7 (Optional): Elasticsearch**
- [ ] Setup Elasticsearch cluster
- [ ] Implement AC-004.1 (Fuzzy Search)
- [ ] Sync MongoDB → ES

### **Week 8: Testing & Launch**
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Deploy to production
