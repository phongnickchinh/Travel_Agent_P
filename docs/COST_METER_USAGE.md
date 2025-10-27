# Cost Meter - Hướng dẫn sử dụng với DI

## 📋 Tổng quan

Cost Meter đã được tích hợp hoàn toàn với **Dependency Injection** system của project.

---

## 🏗️ Kiến trúc

```
DIContainer
    ├─ CostUsageInterface → CostUsageRepository (Singleton)
    └─ CostUsageService (Factory function)
```

### **Files:**

1. **Model**: `app/model/cost_usage.py`
   - `CostUsage` model (kế thừa BaseModel)
   - `ProviderPricing` class

2. **Interface**: `app/repo/postgre/interfaces/cost_usage_interface.py`
   - `CostUsageInterface` (abstract methods)

3. **Repository**: `app/repo/postgre/implementations/cost_usage_repository.py`
   - `CostUsageRepository` (implementation)

4. **Service**: `app/service/cost_usage_service.py`
   - `CostUsageService` (business logic)

5. **Decorator**: `app/utils/cost_meter.py`
   - `@track_cost()` decorator
   - Convenience decorators

6. **DI Setup**: `app/config/di_setup.py`
   - Register repository & service

---

## 🚀 Sử dụng

### **1. Với Decorator (Recommended)**

```python
from app.utils.cost_meter import (
    track_google_places_cost,
    track_openai_cost,
    track_huggingface_cost,
    track_tripadvisor_cost
)

# Google Places API
@track_google_places_cost("text_search")
def search_places(query: str, user_id: str = None):
    response = requests.get(GOOGLE_PLACES_URL, params={"query": query})
    return response.json()

# OpenAI API
@track_openai_cost("gpt-4")
def generate_itinerary(prompt: str, plan_id: str = None):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response

# HuggingFace API
@track_huggingface_cost()
def generate_embeddings(text: str):
    response = model.encode(text)
    return response

# TripAdvisor API
@track_tripadvisor_cost("location_search")
def search_locations(query: str):
    response = requests.get(TRIPADVISOR_URL, params={"query": query})
    return response.json()
```

### **2. Với Service (Business Logic)**

```python
from app.core.di_container import DIContainer
from app.service.cost_usage_service import CostUsageService

# Get service from DI
container = DIContainer.get_instance()
cost_service = container.resolve(CostUsageService.__name__)

# Track manual API call
cost_service.track_api_call(
    provider="google_places",
    service="text_search",
    cost_usd=0.032,
    latency_ms=150,
    success=True,
    user_id="user_123",
    plan_id="plan_abc"
)

# Get plan cost summary
summary = cost_service.get_plan_cost_summary("plan_abc")
print(f"Total cost: ${summary['total_cost']:.2f}")
print(f"Total requests: {summary['total_requests']}")

# Get user cost summary (last 30 days)
user_summary = cost_service.get_user_cost_summary("user_123", days=30)
print(f"User total cost: ${user_summary['total_cost']:.2f}")

# Get daily cost report (last 7 days)
daily_report = cost_service.get_daily_cost_report(days=7)
for day in daily_report:
    print(f"{day['date']}: ${day['cost']:.2f} ({day['requests']} requests)")

# Compare providers
comparison = cost_service.get_provider_comparison(days=7)
for provider in comparison:
    print(f"{provider['provider']}: ${provider['cost']:.2f}")

# Check provider health
health = cost_service.get_provider_health("google_places", days=1)
print(f"Status: {health['health_status']}")
print(f"Success rate: {health['success_rate']:.1f}%")
print(f"Avg latency: {health['latency']['avg_ms']:.0f}ms")
```

### **3. Với Repository (Direct Access)**

```python
from app.core.di_container import DIContainer
from app.repo.postgre.interfaces.cost_usage_interface import CostUsageInterface

# Get repository from DI
container = DIContainer.get_instance()
cost_repo = container.resolve(CostUsageInterface.__name__)

# Create cost record
cost_record = cost_repo.create(
    provider="google_places",
    service="text_search",
    cost_usd=0.032,
    latency_ms=150,
    success=True,
    commit=True
)

# Query by provider
records = cost_repo.get_by_provider("google_places", limit=10)

# Query by plan
plan_costs = cost_repo.get_by_plan_id("plan_abc")

# Get total cost
total = cost_repo.get_total_cost(
    start_date=datetime.now() - timedelta(days=7),
    provider="google_places"
)
```

---

## 🎯 Use Cases

### **Case 1: Track all Google Places calls**

```python
# places_service.py
from app.utils.cost_meter import track_google_places_cost

class PlacesService:
    @track_google_places_cost("text_search")
    def search(self, query, user_id=None):
        # API call automatically tracked
        return self._call_google_api(query)
    
    @track_google_places_cost("details")
    def get_details(self, place_id, user_id=None):
        return self._call_google_api_details(place_id)
```

### **Case 2: Track OpenAI with custom extraction**

```python
from app.utils.cost_meter import track_cost
from app.model.cost_usage import ProviderPricing

def calc_llm_cost(response):
    usage = response.get('usage', {})
    return ProviderPricing.calculate_llm_cost(
        'openai', 'gpt-4',
        usage.get('prompt_tokens', 0),
        usage.get('completion_tokens', 0)
    )

def extract_tokens(response):
    return response.get('usage', {})

@track_cost(
    provider="openai",
    service="chat_completion",
    calculate_cost=calc_llm_cost,
    extract_tokens=extract_tokens,
    user_id_param="user_id",
    plan_id_param="plan_id"
)
def generate_plan(prompt, user_id, plan_id):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response
```

### **Case 3: Dashboard analytics**

```python
# cost_controller.py
from flask import Blueprint, jsonify
from app.core.di_container import DIContainer
from app.service.cost_usage_service import CostUsageService

cost_bp = Blueprint('cost', __name__)

@cost_bp.route('/api/analytics/cost/daily', methods=['GET'])
def get_daily_cost():
    container = DIContainer.get_instance()
    cost_service = container.resolve(CostUsageService.__name__)
    
    report = cost_service.get_daily_cost_report(days=30)
    return jsonify(report)

@cost_bp.route('/api/analytics/cost/providers', methods=['GET'])
def get_provider_stats():
    container = DIContainer.get_instance()
    cost_service = container.resolve(CostUsageService.__name__)
    
    comparison = cost_service.get_provider_comparison(days=7)
    return jsonify(comparison)

@cost_bp.route('/api/analytics/health/<provider>', methods=['GET'])
def get_provider_health(provider):
    container = DIContainer.get_instance()
    cost_service = container.resolve(CostUsageService.__name__)
    
    health = cost_service.get_provider_health(provider, days=1)
    return jsonify(health)
```

---

## 📊 Pricing Configuration

### **Update pricing in `app/model/cost_usage.py`:**

```python
class ProviderPricing:
    # OpenAI GPT-4
    OPENAI_GPT4_INPUT = 0.00003  # $0.03/1K tokens
    OPENAI_GPT4_OUTPUT = 0.00006  # $0.06/1K tokens
    
    # Google Places API
    GOOGLE_PLACES_TEXT_SEARCH = 0.032  # $0.032 per request
    GOOGLE_PLACES_DETAILS = 0.017  # $0.017 per request
    
    # TripAdvisor API
    TRIPADVISOR_LOCATION_SEARCH = 0.01  # $0.01 per request
```

---

## 🗄️ Database Migration

### **Tạo migration:**

```bash
cd server
flask db migrate -m "Add cost_usage table"
flask db upgrade
```

### **Schema:**

```sql
CREATE TABLE cost_usage (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    service VARCHAR(100),
    endpoint VARCHAR(200),
    method VARCHAR(10),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    tokens_total INTEGER DEFAULT 0,
    cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    latency_ms INTEGER,
    status_code INTEGER,
    success BOOLEAN DEFAULT TRUE,
    user_id VARCHAR(36),
    plan_id VARCHAR(50),
    request_id VARCHAR(100),
    metadata JSON,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_cost_usage_provider ON cost_usage(provider);
CREATE INDEX idx_cost_usage_created_at ON cost_usage(created_at);
CREATE INDEX idx_cost_usage_user_id ON cost_usage(user_id);
CREATE INDEX idx_cost_usage_plan_id ON cost_usage(plan_id);
CREATE INDEX idx_cost_usage_provider_created ON cost_usage(provider, created_at);
CREATE INDEX idx_cost_usage_success ON cost_usage(success);
```

---

## ✅ Testing

```python
# test_cost_meter.py
def test_track_google_places():
    @track_google_places_cost("text_search")
    def search_places(query):
        return {"results": []}
    
    result = search_places("Danang")
    
    # Verify cost was tracked
    container = DIContainer.get_instance()
    cost_repo = container.resolve(CostUsageInterface.__name__)
    records = cost_repo.get_by_provider("google_places", limit=1)
    
    assert len(records) > 0
    assert records[0].provider == "google_places"
    assert records[0].service == "text_search"

def test_cost_service():
    container = DIContainer.get_instance()
    cost_service = container.resolve(CostUsageService.__name__)
    
    # Track API call
    cost_service.track_api_call(
        provider="test_provider",
        cost_usd=0.01,
        latency_ms=100
    )
    
    # Verify
    report = cost_service.get_daily_cost_report(days=1)
    assert len(report) > 0
```

---

## 🎓 Best Practices

1. **Always use decorators** cho API calls:
   ```python
   @track_google_places_cost("text_search")
   def call_api():
       ...
   ```

2. **Pass user_id và plan_id** khi có:
   ```python
   def search_places(query, user_id=None, plan_id=None):
       # Decorator sẽ tự extract từ kwargs
       ...
   ```

3. **Monitor health regularly**:
   ```python
   # Scheduled task (Celery)
   @celery.task
   def check_provider_health():
       cost_service = container.resolve(CostUsageService.__name__)
       health = cost_service.get_provider_health("google_places")
       if health['health_status'] == 'unhealthy':
           send_alert()
   ```

4. **Cleanup old records**:
   ```python
   # Monthly cleanup
   @celery.task
   def cleanup_old_costs():
       cost_service = container.resolve(CostUsageService.__name__)
       deleted = cost_service.cleanup_old_records(days=90)
       logger.info(f"Deleted {deleted} old records")
   ```

---

## 📝 Summary

✅ **DI Integration** - Sử dụng DIContainer thay vì global instances
✅ **Repository Pattern** - Interface + Implementation
✅ **Service Layer** - Business logic tách biệt
✅ **Decorator Pattern** - Easy-to-use cost tracking
✅ **Analytics** - Daily reports, provider comparison, health monitoring
✅ **Testing** - Easy to mock with DI

**Ready to use!** 🚀
