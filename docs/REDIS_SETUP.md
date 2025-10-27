# Redis Setup Guide for Travel Agent P

## 📋 Overview

Redis is used in Travel Agent P for:
- **JWT Token Blacklist** - Fast O(1) token invalidation with automatic TTL cleanup
- **Rate Limiting** - Prevent brute-force attacks on login/register/reset-password
- **Caching** - Future use for user profiles and travel data

## 🚀 Installation

### Windows

**Option 1: Using Memurai (Recommended for Windows)**
```bash
# Download from: https://www.memurai.com/get-memurai
# Install and run as Windows service
```

**Option 2: Using Docker**
```bash
docker pull redis:7-alpine
docker run -d -p 6379:6379 --name redis-travelagent redis:7-alpine
```

**Option 3: Using WSL**
```bash
# In WSL terminal
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### macOS

```bash
brew install redis
brew services start redis
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

## ⚙️ Configuration

### 1. Install Python Redis Client

```bash
pip install redis==5.0.1
```

### 2. Update `.env` File

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password_here  # Uncomment if Redis has password

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=True
RATE_LIMIT_LOGIN=5                    # 5 attempts per 5 minutes
RATE_LIMIT_LOGIN_WINDOW=300           
RATE_LIMIT_REGISTER=3                 # 3 attempts per hour
RATE_LIMIT_REGISTER_WINDOW=3600       
RATE_LIMIT_RESET_PASSWORD=3           
RATE_LIMIT_RESET_PASSWORD_WINDOW=3600 

# Cache Configuration
CACHE_ENABLED=True
CACHE_DEFAULT_TTL=300                 # 5 minutes
CACHE_USER_PROFILE_TTL=600            # 10 minutes
```

## 🧪 Testing Redis Connection

```bash
# Test Redis CLI
redis-cli ping
# Expected output: PONG

# Check Redis is running
redis-cli INFO server
```

### Python Test

```python
from app.core.redis_client import get_redis

redis_client = get_redis()
if redis_client:
    redis_client.set('test', 'hello')
    print(redis_client.get('test'))  # Should print: hello
    redis_client.delete('test')
    print("✅ Redis is working!")
else:
    print("❌ Redis connection failed")
```

## 📊 Features Implemented

### 1. **JWT Blacklist with Redis**

**Before (Database)**:
- Cron job cleanup every 5 minutes
- Slower DB queries
- Manual expiration management

**After (Redis)**:
- ✅ Automatic TTL cleanup
- ✅ Sub-millisecond O(1) lookup
- ✅ No cron job needed

**Usage:**
```python
from app.cache.redis_blacklist import RedisBlacklist

# Logout: Blacklist token
RedisBlacklist.add_token(token, user_id, expires_at)

# Middleware: Check if token is blacklisted
if RedisBlacklist.is_blacklisted(token):
    return "Token invalid", 401
```

### 2. **Rate Limiting**

**Protected Endpoints:**
- `/login` - 5 attempts per 5 minutes per email
- `/register` - 3 attempts per hour per email
- `/request-reset-password` - 3 attempts per hour per email

**Response Headers:**
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1698765432
```

**429 Rate Limit Exceeded Response:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Try again in 300 seconds.",
  "retry_after": 300,
  "limit": 5,
  "reset_at": 1698765432
}
```

**Usage Example:**
```python
from app.rate_limiter import rate_limit, get_identifier_by_email
from config import Config

@rate_limit(
    max_requests=Config.RATE_LIMIT_LOGIN,
    window_seconds=Config.RATE_LIMIT_LOGIN_WINDOW,
    identifier_func=get_identifier_by_email,
    key_prefix='login'
)
def login():
    # Your login logic
    pass
```

### 3. **Caching (Future Use)**

```python
from app.cache import cache_result, invalidate_cache

# Cache function result
@cache_result('user:profile', ttl=600)
def get_user_profile(user_id):
    return user_repo.get_user_by_id(user_id)

# Invalidate cache on update
@invalidate_cache('user:profile:*')
def update_user_profile(user_id, data):
    return user_repo.update_user(user_id, data)
```

## 🔧 Troubleshooting

### Redis Not Starting

**Windows (Memurai):**
```bash
# Check service status
sc query Memurai

# Restart service
net stop Memurai
net start Memurai
```

**Docker:**
```bash
docker ps -a  # Check container status
docker logs redis-travelagent  # Check logs
docker restart redis-travelagent
```

**Linux/macOS:**
```bash
sudo systemctl status redis-server
sudo systemctl restart redis-server
```

### Application Running Without Redis

The application has **graceful degradation**:
- ✅ App will start even if Redis is down
- ⚠️  Rate limiting disabled
- ⚠️  Blacklist checks fail-open (allow access)
- ⚠️  Cache disabled

**Log Output:**
```
⚠️  Redis initialization failed: Connection refused
⚠️  Application will continue in degraded mode (without Redis features)
```

### Connection Refused Error

1. **Check if Redis is running:**
   ```bash
   redis-cli ping
   ```

2. **Check Redis port:**
   ```bash
   netstat -an | findstr 6379  # Windows
   netstat -an | grep 6379     # Linux/macOS
   ```

3. **Check `.env` configuration:**
   - Ensure `REDIS_HOST=localhost` (not 127.0.0.1 on some systems)
   - Ensure `REDIS_PORT=6379`

### Performance Issues

**Monitor Redis:**
```bash
redis-cli INFO stats
redis-cli --latency
redis-cli --stat
```

**Check memory usage:**
```bash
redis-cli INFO memory
```

**Clear Redis database (development only):**
```bash
redis-cli FLUSHDB
```

## 📈 Monitoring

### Check Blacklisted Tokens Count

```python
from app.cache.redis_blacklist import RedisBlacklist

count = RedisBlacklist.get_blacklist_count()
print(f"Blacklisted tokens: {count}")
```

### Check Rate Limit Status

```bash
redis-cli KEYS "rate_limit:*"
redis-cli GET "rate_limit:login:email:user@example.com"
```

### Check Cache Keys

```bash
redis-cli KEYS "cache:*"
redis-cli TTL "cache:user:profile:123"
```

## 🔐 Security Best Practices

### Production Redis

1. **Enable Authentication:**
   ```bash
   # redis.conf
   requirepass your_strong_password_here
   ```

2. **Update `.env`:**
   ```env
   REDIS_PASSWORD=your_strong_password_here
   ```

3. **Bind to localhost only:**
   ```bash
   # redis.conf
   bind 127.0.0.1
   ```

4. **Disable dangerous commands:**
   ```bash
   # redis.conf
   rename-command FLUSHDB ""
   rename-command FLUSHALL ""
   rename-command CONFIG ""
   ```

5. **Enable SSL/TLS (if needed):**
   ```bash
   # Use Redis with TLS
   redis-cli --tls -p 6380
   ```

## 📚 Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Memurai for Windows](https://www.memurai.com/)
- [Rate Limiting Algorithms](https://redis.io/glossary/rate-limiting/)

## 🎯 Next Steps

1. ✅ Install Redis locally
2. ✅ Update `.env` with Redis configuration
3. ✅ Test Redis connection
4. ✅ Test rate limiting on `/login` endpoint
5. ✅ Test logout/blacklist functionality
6. 🔄 Monitor Redis performance
7. 🔄 Implement user profile caching (optional)
