# Travel Agent P - API Payload Examples

## 🔐 Authentication APIs

### 1. Register
```http
POST /api/auth/register
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "username": "john_doe",
  "name": "John Doe",
  "language": "vi",
  "timezone": "Asia/Ho_Chi_Minh",
  "deviceId": "device_abc123"
}

Response: 201 Created
{
  "resultMessage": {
    "en": "Registration successful. Please check your email to verify your account before logging in.",
    "vn": "Đăng ký thành công. Vui lòng kiểm tra email để xác minh tài khoản trước khi đăng nhập."
  },
  "resultCode": "00035",
  "data": {
    "user": {
      "id": 123,
      "email": "user@example.com",
      "username": "john_doe",
      "name": "John Doe",
      "is_verified": false,
      "auth_provider": "local",
      "created_at": "2025-10-27T10:30:00Z"
    },
    "confirmToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "Please verify your email before logging in"
  }
}
```

### 2. Verify Email
```http
POST /api/auth/verify-email
Content-Type: application/json

Request:
{
  "confirm_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "verification_code": "123456"
}

Response: 200 OK
{
  "resultMessage": {
    "en": "Your email address has been verified successfully. Please login to continue.",
    "vn": "Địa chỉ email của bạn đã được xác minh thành công. Vui lòng đăng nhập để tiếp tục."
  },
  "resultCode": "00058",
  "data": {
    "verified": true,
    "email": "user@example.com"
  }
}
```

### 3. Login
```http
POST /api/auth/login
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "SecurePass123"
}

Response: 200 OK
{
  "resultMessage": {
    "en": "You have successfully logged in.",
    "vn": "Bạn đã đăng nhập thành công."
  },
  "resultCode": "00047",
  "data": {
    "user": {
      "id": 123,
      "email": "user@example.com",
      "username": "john_doe",
      "name": "John Doe",
      "is_verified": true,
      "profile_picture": null
    },
    "role": "user",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}

Rate Limit Headers:
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1698765432
```

### 4. Logout
```http
POST /api/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 204 No Content
```

---

## 📍 POI APIs

### 5. Search POI
```http
GET /api/poi/search?q=bãi+biển&lat=16.0544&lng=108.2428&radius=10km&category=beach&page=1&limit=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 200 OK
{
  "results": [
    {
      "poi_id": "poi_mykhebeach",
      "name": "Mỹ Khê Beach",
      "name_unaccented": "my khe beach",
      "categories": ["beach", "nature"],
      "location": {
        "type": "Point",
        "coordinates": [108.2428, 16.0544]
      },
      "distance_km": 0.5,
      "ratings": {
        "average": 4.7,
        "count": 15234
      },
      "pricing": {
        "level": "free"
      },
      "image_url": "https://firebase.com/images/mykhe.jpg",
      "popularity_score": 87.5
    },
    {
      "poi_id": "poi_nonnocbeach",
      "name": "Non Nước Beach",
      "categories": ["beach"],
      "location": {
        "type": "Point",
        "coordinates": [108.2627, 16.0199]
      },
      "distance_km": 2.3,
      "ratings": {
        "average": 4.5,
        "count": 8901
      }
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 20,
  "total_pages": 1
}
```

### 6. Get POI Details
```http
GET /api/poi/poi_mykhebeach
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 200 OK
{
  "poi_id": "poi_mykhebeach",
  "dedupe_key": "mykhebeach_wecq6uk",
  "name": "Mỹ Khê Beach",
  "name_unaccented": "my khe beach",
  "name_alternatives": [
    {"language": "en", "name": "My Khe Beach"},
    {"language": "vi", "name": "Bãi biển Mỹ Khê"}
  ],
  "location": {
    "type": "Point",
    "coordinates": [108.2428, 16.0544]
  },
  "address": {
    "street": "Võ Nguyên Giáp",
    "ward": "Phước Mỹ",
    "district": "Sơn Trà",
    "city": "Đà Nẵng",
    "country": "Vietnam",
    "full_address": "Võ Nguyên Giáp, Phước Mỹ, Sơn Trà, Đà Nẵng"
  },
  "categories": ["beach", "nature"],
  "description": {
    "short": "One of the most beautiful beaches in Vietnam with white sand and clear water",
    "long": "Mỹ Khê Beach is a 20-mile stretch of beach..."
  },
  "ratings": {
    "average": 4.7,
    "count": 15234,
    "breakdown": {
      "5_star": 10000,
      "4_star": 3000,
      "3_star": 1500,
      "2_star": 500,
      "1_star": 234
    }
  },
  "pricing": {
    "level": "free",
    "entrance_fee": {
      "adult": 0,
      "child": 0,
      "currency": "VND"
    }
  },
  "opening_hours": {
    "monday": "00:00-23:59",
    "tuesday": "00:00-23:59",
    "is_24_hours": true,
    "notes": "Beach is always open, but lifeguards on duty 06:00-18:00"
  },
  "contact": {
    "phone": "+84 236 3847 111",
    "website": "https://danang.gov.vn"
  },
  "images": [
    {
      "url": "https://firebase.com/images/mykhe1.jpg",
      "caption": "Sunrise at My Khe Beach",
      "is_primary": true
    },
    {
      "url": "https://firebase.com/images/mykhe2.jpg",
      "caption": "Beach view"
    }
  ],
  "amenities": ["wifi", "parking", "restroom", "cafe"],
  "best_time_to_visit": {
    "season": ["spring", "summer"],
    "time_of_day": "early_morning",
    "duration_minutes": 180
  },
  "metadata": {
    "created_at": "2025-10-27T10:00:00Z",
    "updated_at": "2025-10-27T10:30:00Z",
    "verified": true,
    "popularity_score": 87.5,
    "view_count": 5001,
    "booking_count": 500
  }
}
```

### 7. Add POI (Admin)
```http
POST /api/admin/poi
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

Request:
{
  "name": "Ba Na Hills",
  "name_alternatives": [
    {"language": "en", "name": "Ba Na Hills"},
    {"language": "vi", "name": "Bà Nà Hills"}
  ],
  "location": {
    "type": "Point",
    "coordinates": [107.9989, 15.9973]
  },
  "address": {
    "ward": "Hòa Ninh",
    "district": "Hòa Vang",
    "city": "Đà Nẵng",
    "country": "Vietnam"
  },
  "categories": ["adventure", "landmark"],
  "description": {
    "short": "Mountain resort with Golden Bridge",
    "long": "Ba Na Hills is a hill station and resort..."
  },
  "pricing": {
    "level": "expensive",
    "entrance_fee": {
      "adult": 750000,
      "child": 550000,
      "currency": "VND"
    }
  },
  "opening_hours": {
    "monday": "07:00-18:00",
    "tuesday": "07:00-18:00",
    "wednesday": "07:00-18:00",
    "thursday": "07:00-18:00",
    "friday": "07:00-18:00",
    "saturday": "07:00-19:00",
    "sunday": "07:00-19:00"
  },
  "sources": [
    {
      "provider": "manual",
      "confidence": 1.0
    }
  ]
}

Response: 201 Created
{
  "message": "POI created successfully",
  "poi_id": "poi_banahills",
  "dedupe_key": "banahills_wedyb72"
}
```

---

## 🗺️ Itinerary APIs

### 8. Generate Itinerary
```http
POST /api/itinerary/generate
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

Request:
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
  },
  "start_date": "2025-11-01"
}

Response: 202 Accepted
{
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_time_seconds": 25,
  "message": "Your itinerary is being generated. Please check status."
}

# Poll for status
GET /api/itinerary/status/job_abc123
Response: 200 OK
{
  "job_id": "job_abc123",
  "status": "completed",
  "itinerary_id": "itin_xyz789",
  "message": "Itinerary generated successfully"
}

# Alternative: Still processing
Response: 200 OK
{
  "job_id": "job_abc123",
  "status": "processing",
  "progress": 65,
  "message": "Selecting POIs based on your preferences..."
}
```

### 9. Get Itinerary
```http
GET /api/itinerary/itin_xyz789
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 200 OK
{
  "plan_id": "itin_xyz789",
  "destination": {
    "city": "Da Nang",
    "country": "Vietnam",
    "region": "Central Vietnam"
  },
  "duration": {
    "days": 3,
    "nights": 2
  },
  "budget": {
    "total": 5000000,
    "currency": "VND",
    "breakdown": {
      "accommodation": 1500000,
      "food": 1500000,
      "transportation": 500000,
      "activities": 1200000,
      "other": 300000
    }
  },
  "user_preferences": {
    "interests": ["beach", "cultural", "food"],
    "travel_style": "mid-range",
    "pace": "moderate"
  },
  "days": [
    {
      "day_number": 1,
      "date": "2025-11-01",
      "theme": "Beach Relaxation & Seafood",
      "activities": [
        {
          "time_slot": "morning",
          "start_time": "09:00",
          "duration_minutes": 120,
          "activity_type": "visit_poi",
          "poi": {
            "poi_id": "poi_mykhebeach",
            "name": "Mỹ Khê Beach",
            "category": "beach",
            "location": {
              "lat": 16.0544,
              "lng": 108.2428
            },
            "estimated_cost": {
              "amount": 0,
              "currency": "VND"
            }
          },
          "description": "Start your day with a relaxing beach walk and swim at one of Vietnam's most beautiful beaches",
          "tips": [
            "Arrive early to avoid crowds (before 8am)",
            "Bring sunscreen and beach towel",
            "Nearby cafes serve breakfast with ocean view"
          ]
        },
        {
          "time_slot": "afternoon",
          "start_time": "12:00",
          "duration_minutes": 90,
          "activity_type": "meal",
          "poi": {
            "poi_id": "poi_bemanseafood",
            "name": "Bé Mặn Seafood Restaurant",
            "category": "restaurant",
            "location": {
              "lat": 16.0620,
              "lng": 108.2370
            },
            "estimated_cost": {
              "amount": 300000,
              "currency": "VND"
            }
          },
          "description": "Enjoy fresh seafood lunch with local specialties",
          "tips": [
            "Try the grilled fish and clams",
            "Average cost: 250-400k VND per person"
          ]
        },
        {
          "time_slot": "evening",
          "start_time": "18:00",
          "duration_minutes": 120,
          "activity_type": "visit_poi",
          "poi": {
            "poi_id": "poi_dragonbridge",
            "name": "Dragon Bridge",
            "category": "landmark",
            "location": {
              "lat": 16.0611,
              "lng": 108.2272
            },
            "estimated_cost": {
              "amount": 0,
              "currency": "VND"
            }
          },
          "description": "Watch the dragon breathe fire and water show (weekends at 9pm)",
          "tips": [
            "Best viewing spot: East side of bridge",
            "Show happens at 9pm on Sat/Sun",
            "Grab street food nearby"
          ]
        }
      ],
      "total_cost": 300000
    },
    {
      "day_number": 2,
      "date": "2025-11-02",
      "theme": "Cultural Exploration",
      "activities": [
        {
          "time_slot": "morning",
          "start_time": "08:00",
          "duration_minutes": 240,
          "activity_type": "visit_poi",
          "poi": {
            "poi_id": "poi_marblemt",
            "name": "Marble Mountains",
            "category": "historical",
            "location": {
              "lat": 16.0084,
              "lng": 108.2609
            },
            "estimated_cost": {
              "amount": 40000,
              "currency": "VND"
            }
          },
          "description": "Explore ancient caves and pagodas in marble mountains",
          "tips": [
            "Wear comfortable shoes for climbing",
            "Entry fee: 40k VND",
            "Hire a guide for full history (100k VND)"
          ]
        }
      ],
      "total_cost": 400000
    },
    {
      "day_number": 3,
      "date": "2025-11-03",
      "theme": "Adventure Day",
      "activities": [
        {
          "time_slot": "morning",
          "start_time": "07:00",
          "duration_minutes": 480,
          "activity_type": "visit_poi",
          "poi": {
            "poi_id": "poi_banahills",
            "name": "Ba Na Hills",
            "category": "adventure",
            "location": {
              "lat": 15.9973,
              "lng": 107.9989
            },
            "estimated_cost": {
              "amount": 750000,
              "currency": "VND"
            }
          },
          "description": "Full day trip to Ba Na Hills with Golden Bridge",
          "tips": [
            "Book cable car tickets online to avoid queues",
            "Bring a light jacket (cooler at top)",
            "Entry fee: 750k VND (includes cable car)"
          ]
        }
      ],
      "total_cost": 900000
    }
  ],
  "metadata": {
    "created_at": "2025-10-27T10:30:00Z",
    "updated_at": "2025-10-27T10:30:00Z",
    "ai_model": "gpt-4-turbo",
    "user_id": "user_123",
    "version": "1.0",
    "is_public": false,
    "share_token": null,
    "view_count": 1
  }
}
```

### 10. List User Itineraries
```http
GET /api/itinerary/my-itineraries?page=1&limit=10
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 200 OK
{
  "itineraries": [
    {
      "plan_id": "itin_xyz789",
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
      "created_at": "2025-10-27T10:30:00Z",
      "is_public": false,
      "thumbnail": "https://firebase.com/itinerary/thumb_xyz789.jpg"
    },
    {
      "plan_id": "itin_abc456",
      "destination": {
        "city": "Hoi An",
        "country": "Vietnam"
      },
      "duration": {
        "days": 2,
        "nights": 1
      },
      "budget": {
        "total": 3000000,
        "currency": "VND"
      },
      "created_at": "2025-10-25T14:20:00Z",
      "is_public": true,
      "share_token": "share_def789"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 10
}
```

### 11. Share Itinerary (Public Link)
```http
GET /share/itin_xyz789
# No authentication required

Response: 200 OK
{
  "plan_id": "itin_xyz789",
  "destination": {...},
  "days": [...],
  "metadata": {
    "created_at": "2025-10-27T10:30:00Z",
    "view_count": 150,
    "is_public": true
  },
  "author": {
    "username": "john_doe",
    "name": "John Doe"
  }
}
```

---

## ❌ Error Responses

### Rate Limit Exceeded
```http
POST /api/auth/login
# After 5 failed attempts

Response: 429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Try again in 300 seconds.",
  "retry_after": 300,
  "limit": 5,
  "reset_at": 1698765432
}

Headers:
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1698765432
```

### Unauthorized (Blacklisted Token)
```http
GET /api/user/profile
Authorization: Bearer <blacklisted_token>

Response: 401 Unauthorized
{
  "resultMessage": {
    "en": "Invalid token.",
    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
  },
  "resultCode": "00012"
}
```

### Duplicate POI
```http
POST /api/admin/poi
# With same dedupe_key

Response: 409 Conflict
{
  "error": "Duplicate POI",
  "message": "A POI with this location and name already exists",
  "existing_poi_id": "poi_mykhebeach",
  "dedupe_key": "mykhebeach_wecq6uk"
}
```
