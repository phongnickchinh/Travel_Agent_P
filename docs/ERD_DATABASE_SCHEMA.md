# Travel Agent P - Entity Relationship Diagram (ERD)

## PostgreSQL Schema (Relational Data)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  POSTGRESQL DATABASE - Structured Relational Data                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐         ┌──────────────────────────────┐
│          users               │         │          roles               │
├──────────────────────────────┤         ├──────────────────────────────┤
│ id (PK)              SERIAL  │         │ id (PK)              SERIAL  │
│ email                VARCHAR │◀───┐    │ role_name            VARCHAR │
│ password_hash        VARCHAR │    │    │ description          TEXT    │
│ username             VARCHAR │    │    │ created_at           TIMESTAMP│
│ name                 VARCHAR │    │    └──────────────────────────────┘
│ is_verified          BOOLEAN │    │              ▲
│ auth_provider        VARCHAR │    │              │
│ google_id            VARCHAR │    │              │
│ profile_picture      VARCHAR │    │    ┌─────────┴──────────┐
│ language             VARCHAR │    │    │                    │
│ timezone             VARCHAR │    │    │   user_roles       │
│ device_id            VARCHAR │    │    ├────────────────────┤
│ created_at           TIMESTAMP    │    │ id (PK)    SERIAL  │
│ updated_at           TIMESTAMP    └────│ user_id (FK)       │
└──────────────────────────────┘         │ role_id (FK)       │
            │                             │ created_at  TIMESTAMP
            │                             └────────────────────┘
            │
            │                             ┌──────────────────────────────┐
            │                             │          tokens              │
            │                             ├──────────────────────────────┤
            └─────────────────────────────│ id (PK)              SERIAL  │
                                          │ user_id (FK)         INT     │
                                          │ refresh_token        TEXT    │
                                          │ confirm_token        TEXT    │
                                          │ reset_token          TEXT    │
                                          │ verification_code    VARCHAR │
                                          │ reset_code           VARCHAR │
                                          │ verification_code_expires_at │
                                          │ reset_code_expires_at        │
                                          │ created_at           TIMESTAMP
                                          │ updated_at           TIMESTAMP
                                          └──────────────────────────────┘

┌──────────────────────────────┐
│      login_attempts          │     (Rate limiting backup - primary in Redis)
├──────────────────────────────┤
│ id (PK)              SERIAL  │
│ email                VARCHAR │
│ ip_address           VARCHAR │
│ attempt_count        INT     │
│ last_attempt_at      TIMESTAMP
│ window_start_at      TIMESTAMP
└──────────────────────────────┘

┌──────────────────────────────┐
│        bookings              │     (Future)
├──────────────────────────────┤
│ id (PK)              SERIAL  │
│ user_id (FK)         INT     │
│ itinerary_id         VARCHAR │  ← MongoDB itinerary._id
│ status               VARCHAR │  ← pending/confirmed/cancelled
│ total_amount         DECIMAL │
│ currency             VARCHAR │
│ payment_method       VARCHAR │
│ payment_status       VARCHAR │
│ booked_at            TIMESTAMP
│ created_at           TIMESTAMP
└──────────────────────────────┘
```

---

## MongoDB Collections (Document Data)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  MONGODB DATABASE - Flexible Document Data                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

Collection: poi (Points of Interest)
────────────────────────────────────────
{
  _id: ObjectId("..."),
  poi_id: "poi_mykhebeach",
  dedupe_key: "mykhebeach_wecq6uk",      ← UNIQUE INDEX
  name: "Mỹ Khê Beach",
  name_unaccented: "my khe beach",
  name_alternatives: [
    {language: "en", name: "My Khe Beach"},
    {language: "vi", name: "Bãi biển Mỹ Khê"}
  ],
  location: {                             ← 2DSPHERE INDEX
    type: "Point",
    coordinates: [108.2428, 16.0544]      // [lng, lat]
  },
  address: {...},
  categories: ["beach", "nature"],        ← INDEX
  description: {...},
  ratings: {
    average: 4.7,
    count: 15234,
    breakdown: {5_star: 10000, ...}
  },
  pricing: {...},
  opening_hours: {...},
  contact: {...},
  images: [...],
  amenities: ["wifi", "parking", "restroom"],
  best_time_to_visit: {...},
  sources: [
    {
      provider: "google_places",
      external_id: "ChIJ...",
      last_updated: ISODate("2025-10-27"),
      confidence: 0.95
    }
  ],
  embedding: [0.123, -0.456, ...],        // 384-dim vector
  metadata: {
    created_at: ISODate("2025-10-27"),
    updated_at: ISODate("2025-10-27"),
    verified: true,
    popularity_score: 87.5,
    view_count: 5000,
    booking_count: 500
  }
}

Indexes:
- dedupe_key (unique)
- location (2dsphere) for geo queries
- categories (multikey)
- {name: "text", name_unaccented: "text", description.short: "text"}


Collection: itineraries
────────────────────────────────────────
{
  _id: ObjectId("..."),
  plan_id: "itin_abc123",
  user_id: "user_123",                    ← FK to PostgreSQL users.id
  destination: {
    city: "Da Nang",
    country: "Vietnam",
    region: "Central Vietnam"
  },
  duration: {
    days: 3,
    nights: 2
  },
  budget: {
    total: 5000000,
    currency: "VND",
    breakdown: {...}
  },
  user_preferences: {
    interests: ["beach", "cultural", "food"],
    travel_style: "mid-range",
    pace: "moderate"
  },
  days: [
    {
      day_number: 1,
      date: "2025-11-01",
      theme: "Beach Day & Seafood",
      activities: [
        {
          time_slot: "morning",
          start_time: "09:00",
          duration_minutes: 120,
          activity_type: "visit_poi",
          poi: {
            poi_id: "poi_mykhebeach",     ← Reference to poi collection
            name: "Mỹ Khê Beach",
            category: "beach",
            location: {lat: 16.0544, lng: 108.2428},
            estimated_cost: {amount: 0, currency: "VND"}
          },
          description: "...",
          tips: ["..."]
        }
      ],
      total_cost: 500000
    }
  ],
  metadata: {
    created_at: ISODate("2025-10-27"),
    updated_at: ISODate("2025-10-27"),
    ai_model: "gpt-4-turbo",
    version: "1.0",
    is_public: false,
    share_token: "share_xyz789",
    view_count: 0
  }
}

Indexes:
- user_id (for user's itinerary list)
- destination.city (for search by destination)
- metadata.created_at (for sorting)
- metadata.share_token (unique, for public sharing)


Collection: reviews (Future)
────────────────────────────────────────
{
  _id: ObjectId("..."),
  review_id: "rev_abc123",
  user_id: "user_123",                    ← FK to PostgreSQL users.id
  poi_id: "poi_mykhebeach",               ← FK to poi collection
  rating: 5,
  title: "Amazing beach!",
  content: "...",
  images: [...],
  helpful_count: 15,
  visit_date: ISODate("2025-10-15"),
  created_at: ISODate("2025-10-27")
}

Indexes:
- poi_id (for POI reviews)
- user_id (for user's reviews)
- rating (for filtering)
```

---

## Redis Keys Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  REDIS - In-Memory Cache & Queue                                                │
└─────────────────────────────────────────────────────────────────────────────────┘

Key Pattern: blacklist:{token}
Type: String
TTL: Token expiry time
Value: user_id
Example:
  blacklist:eyJhbGciOiJIUzI1NiIs... → "user_123"

Key Pattern: rate_limit:{prefix}:{identifier}
Type: Sorted Set
TTL: Window duration
Members: timestamp scores
Example:
  rate_limit:login:email:user@example.com → [(1698765432.123, 1698765432.123), ...]

Key Pattern: cache:poi:{poi_id}
Type: String (JSON)
TTL: 600 seconds (10 minutes)
Value: POI JSON
Example:
  cache:poi:poi_mykhebeach → "{\"poi_id\":\"poi_mykhebeach\", ...}"

Key Pattern: cache:search:{query_hash}
Type: String (JSON)
TTL: 3600 seconds (1 hour)
Value: Search results JSON
Example:
  cache:search:md5(beach+danang+...) → "[{\"poi_id\":...}, ...]"

Key Pattern: session:{user_id}
Type: Hash
TTL: 7 days
Fields: last_activity, ip_address, device_id
Example:
  session:user_123 → {last_activity: "2025-10-27 10:30", ip: "1.2.3.4"}

Key Pattern: celery (Celery Queue)
Type: List
No TTL
Value: Celery task messages
Example:
  celery → ["task1", "task2", ...]
```

---

## Elasticsearch Index (Optional MVP)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ELASTICSEARCH - Full-Text Search Engine                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

Index: poi
────────────────────────────────────────
{
  "mappings": {
    "properties": {
      "poi_id": {
        "type": "keyword"
      },
      "name": {
        "type": "text",
        "analyzer": "vietnamese",
        "fields": {
          "raw": {"type": "keyword"},
          "english": {"type": "text", "analyzer": "english"}
        }
      },
      "name_unaccented": {
        "type": "text",
        "analyzer": "standard"
      },
      "description": {
        "type": "text",
        "analyzer": "vietnamese"
      },
      "categories": {
        "type": "keyword"
      },
      "location": {
        "type": "geo_point"
      },
      "ratings": {
        "properties": {
          "average": {"type": "float"},
          "count": {"type": "integer"}
        }
      },
      "popularity_score": {
        "type": "float"
      },
      "created_at": {
        "type": "date"
      }
    }
  }
}

Document Example:
{
  "poi_id": "poi_mykhebeach",
  "name": "Mỹ Khê Beach",
  "name_unaccented": "my khe beach",
  "description": "One of the most beautiful beaches...",
  "categories": ["beach", "nature"],
  "location": {"lat": 16.0544, "lon": 108.2428},
  "ratings": {"average": 4.7, "count": 15234},
  "popularity_score": 87.5
}
```

---

## Cross-Database Relationships

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  DATA RELATIONSHIP ACROSS DATABASES                                          │
└──────────────────────────────────────────────────────────────────────────────┘

PostgreSQL (users) ──────user_id──────▶ MongoDB (itineraries)
                                        ▲
                                        │
                                        └── Reference to poi_id in activities

PostgreSQL (users) ──────user_id──────▶ MongoDB (reviews)
                                        │
MongoDB (poi) ───────poi_id────────────┘

PostgreSQL (bookings) ──itinerary_id──▶ MongoDB (itineraries)
                      └─user_id────────▶ PostgreSQL (users)

MongoDB (poi) ───────poi_id───────────▶ Elasticsearch (poi index)
                                          (Synced via MongoDB Change Streams)

Redis (cache:poi:*) ──poi_id──────────▶ MongoDB (poi)
Redis (session:*) ────user_id─────────▶ PostgreSQL (users)
```
