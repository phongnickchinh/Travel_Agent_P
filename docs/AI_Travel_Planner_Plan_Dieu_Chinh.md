# 🧭 KẾ HOẠCH TRIỂN KHAI DỰ ÁN: AI TRAVEL PLANNER (ĐÃ ĐIỀU CHỈNH)
**Tác giả:** Phạm Văn Phong  
**Thời gian thực hiện:** 9 tuần (14/10/2025 – 15/12/2025)

---

## 🎯 MỤC TIÊU CHUNG (MVP)
- Sinh **lịch trình JSON chuẩn** từ input (điểm đến, số ngày, ngân sách, sở thích).
- Dữ liệu thật: **Google Places** (bắt buộc), **TripAdvisor** (tùy chọn qua feature flag).
- **Tìm kiếm địa điểm** mượt bằng **Elasticsearch** (autocomplete, fuzzy, geo-distance; có thể hybrid lexical + vector giai đoạn sau).
- Lưu & hiển thị lịch trình; **export PDF**; **Google Maps**.
- Kiểm soát **quota/chi phí/độ trễ** (cache, rate-limit, retry, job async).
- **Routing**: đơn giản + rule-based. (TSP nâng cao, cá nhân hóa ML → Phase 2).

---

## 🧱 KIẾN TRÚC CHỐT
- **Auth + user**: PostgreSQL (đang có).
- **Domain động**: MongoDB (plans, pois, flags, queries).
- **Cache/limit/queue**: Redis.
- **LLM**: HuggingFace (HF) + **LangChain** (PromptTemplate, PydanticOutputParser, LCEL chain, callbacks).
- **Search**: **Elasticsearch** (autocomplete/fuzzy/geo; tùy chọn vector cho hybrid).
- **Providers**: Google Places (bắt buộc), TripAdvisor (optional, feature-flag).

---

## 🗓️ TIẾN ĐỘ CHI TIẾT (9 TUẦN)

### Tuần 1 (14–20/10) – Kiến trúc & Chuẩn dữ liệu
- Chốt kiến trúc: PG, Mongo, Redis, **HF + LangChain**, Providers, **ES**.
- Định nghĩa **JSON Schema** `plan_v1.json` (ép đầu ra LLM).
- Thiết kế **POI unified model** + `dedupe_key` *(unidecode(name)+geohash)*.
- Lập **Acceptance Criteria (AC)** cho MVP (kèm AC search).
**Deliverables:** sơ đồ, schema JSON, payload mẫu, ERD rút gọn, `.env.example`.

### Tuần 2 (21–27/10) – Hạ tầng vận hành
- **Redis**: cache nóng, **token-bucket rate-limit**, queue nhẹ.
- **Retry + backoff + circuit breaker**; **request dedup** (hash body).
- **Mock servers**: `/mock/places`, `/mock/ta`, `/mock/llm`.
- **Cost meter**: log chi phí/tokens/latency vào PG (`cost_usage`).
- **ES bootstrap**: Elastic Cloud (khuyến nghị) hoặc Docker ES/Kibana.
**Deliverables:** utils (rate_limit, retry_backoff, cost_meter), mock endpoints, ES connectivity test.

### Tuần 3 (28/10–3/11) – Google Places sớm + ES lexical/geo
- **GooglePlacesProvider** (search/details) + **write-through cache** vào Mongo (`pois`).
- **ES index `pois`**: mapping `name(text+edge_ngram)`, `types(keyword)`, `rating(float)`, `price_level`, `location(geo_point)`.
- **Ingestion**: đồng bộ một chiều Mongo → ES (bulk + upsert).
- API: `GET /api/places/*` (Mongo), `GET /api/search` (ES lexical+geo, sort distance/rating).
**Deliverables:** provider Google, `pois_repo`, `es_repo` (index/bulk/search), FE thử **autocomplete**.

### Tuần 4 (4–10/11) – AI prototype (**HF + LangChain**) với mock POIs
- **LangChain**: `PromptTemplate` + `PydanticOutputParser` + **LCEL chain** (ép JSON đúng schema).
- **Orchestrator v1**: build prompt từ input + **mock POIs**, parse/validate → lưu `plans (pending→ready)`.
- API: `POST /api/plan` (enqueue **Celery**, trả `plan_id`), `GET /api/plan/{id}` (polling).
**Deliverables:** `hf_adapter`, `lc_chain`, `planner_service`, `plan_controller`, Celery task `generate_plan`.

### Tuần 5 (11–17/11) – TA optional & ES ổn định
- **TripAdvisorProvider** bật qua `FEATURE_TA`; **merge & dedupe** (ưu tiên Google).
- **ES analyzers**: `asciifolding`, `lowercase`, `edge_ngram`; **synonym** cơ bản (ẩm thực/địa danh).
- Báo cáo **chi phí theo provider** (PG).
**Deliverables:** `providers/factory`, flag TA, `es_repo` synonyms/analyzers, báo cáo chi phí tuần.

### Tuần 6 (18–24/11) – Refine AI (dữ liệu thật) & Test tích hợp R1 + *(tùy)* Vector
- **Orchestrator v2**: dùng POIs **thật** (từ ES hoặc Mongo), top-K vào prompt (**LangChain**).
- **Routing**: nearest-neighbor + **time-window** (giờ mở cửa) + giới hạn quãng đường/ngày (Haversine).
- **Cá nhân hóa rule-based nhẹ**: `budget_tier` + `prefs`.
- *(Tùy chọn bật `FEATURE_ES_VECTOR`)*: tạo **embeddings HF** cho POI → `dense_vector` trong ES; Celery tasks `build_embeddings`, `reindex_es`.
- **Integration Test R1** (10 case): % POI hợp lệ, trùng lặp, vi phạm giờ mở cửa, latency, chi phí; smoke test relevance search.
**Deliverables:** `routing_simple`, `embedding.py`, bulk vector upsert, báo cáo R1.

### Tuần 7 (25/11–1/12) – Maps & Export + UX
- **Google Maps** (markers + polyline).
- **Export PDF** (server-side) + QR “Mở Google Maps”.
- UX polling/progress/retry/empty states; ô tìm kiếm dùng **ES autocomplete**.
**Deliverables:** `export_service` (PDF), FE Map/Timeline/Search UI.

### Tuần 8 (2–8/12) – Tối ưu & Test tích hợp R2 (gồm search)
- **Cache layer** theo bbox+type; tinh chỉnh rate-limit.
- **Giảm chi phí LLM**: reuse prompt, đẩy logic sang rule-based, giảm token; **LangChain callbacks** log token/latency.
- **ES scoring**: `function_score` (gauss(location, 2km) + rating boost + price bucket). Nếu vector bật → **hybrid query** (bool lexical + kNN).
- **Integration Test R2** (20–30 case): so sánh vs R1; đo thêm **P95 search latency**, **typo tolerance**.
**Deliverables:** báo cáo R2, bảng chi phí/latency, cấu hình ES final, QA checklist release.

### Tuần 9 (9–15/12) – Đóng gói, Deploy, Demo
- **CI** mini: lint + unit + build image.
- Deploy: FE (Firebase Hosting/Vercel), BE (Render), DB (PG managed, Mongo Atlas), Redis managed, **ES (Elastic Cloud)**.
- Dashboard quan sát (Kibana/log aggregator nhẹ), alert cơ bản.
- **Video demo** + tài liệu người dùng.
**Deliverables:** URL staging/production, **Kibana dashboard**, script demo, video, hướng dẫn triển khai.

---

## 🧩 CẤU TRÚC DỰ ÁN (ĐIỀU CHỈNH)
```
/travel-planner
├── client/ (React: Vite + Tailwind)
│   ├── src/components/
│   ├── src/pages/
│   ├── src/services/api.js
│   └── vite.config.js
├── server/ (Flask)
│   ├── app/
│   │   ├── controller/{auth,user,health}/...
│   │   ├── controller/plan/plan_controller.py
│   │   ├── controller/places/places_controller.py
│   │   ├── controller/search/search_controller.py
│   │   ├── domain/{models.py,routing_simple.py,schemas/plan_v1.json}
│   │   ├── providers/{base.py,google_places.py,tripadvisor.py,factory.py}
│   │   ├── repo/mg/{plans_repo.py,pois_repo.py,flags_repo.py}
│   │   ├── repo/pg/{cost_usage_repo.py}
│   │   ├── repo/es/{es_repo.py}
│   │   ├── llm/{hf_adapter.py,lc_chain.py}
│   │   ├── service/{planner_service.py,places_service.py,search_service.py}
│   │   ├── utils/{rate_limit.py,retry_backoff.py,cost_meter.py,embedding.py}
│   │   ├── AppConfig/di_setup.py
│   │   └── core/di_container.py
│   ├── celery_worker.py
│   ├── docker-compose.yml
│   └── app.py
├── docker-compose.yml
└── README.md
```

---

## 🔌 API CHÍNH
- `POST /api/plan` → **202** `{ plan_id }`
- `GET /api/plan/{id}` → `{ status: pending|ready|error, data? }`
- `GET /api/places/search?q=&lat=&lng=&type=&radius=`
- `GET /api/places/{id}`
- `GET /api/search?q=&lat=&lng=&radius=&types=&limit=` *(ES lexical+geo; nếu bật vector → hybrid)*
- `POST /api/plan/{id}/export/pdf`
- `GET /api/healthz`, `GET /api/readiness`

---

## 🗃️ LƯU TRỮ & INDEX
- **Mongo `plans`**: `user_id`, `destination{name,lat,lng}`, `days[]`, `budget_tier`, `status`, `providers_used`, `created_at`, `schema_version`.
- **Mongo `pois`**: `source+id` *(unique)*, `dedupe_key` *(unique)*, `location` *(2dsphere)*.
- **ES `pois`**: mapping như trên; ingestion từ Mongo; *(tuỳ)* `dense_vector` cho hybrid.
- **PG `cost_usage`**: `provider`, `tokens`, `price`, `latency`, `ts`.

---

## ✅ ACCEPTANCE CRITERIA (MVP)
- **AC-1:** ≥ 90% POI trong plan **hợp lệ** (details lấy được).
- **AC-2:** Không **trùng POI** trong cùng ngày; **quãng đường/ngày** ≤ ngưỡng.
- **AC-3:** ≥ 80% slot trong **giờ mở cửa**.
- **AC-4:** **P95** thời gian tạo plan (cache nóng) ≤ ngưỡng mục tiêu.
- **AC-5:** **Chi phí LLM/100 kế hoạch** ≤ mục tiêu.
- **AC-6 (Search):** **P95 `/api/search` ≤ 150ms** (ES cloud); query **fuzzy 1 lỗi** vẫn hợp lệ; top-5 có ≥1 kết quả đúng ý trong **≥ 80%** truy vấn thử.

---

## ⚠️ RỦI RO & GIẢM THIỂU
- **ES** vận hành phức tạp → Elastic Cloud; `FEATURE_ES=false` để fallback Mongo text.
- **Vector search** tốn tài nguyên → bật sau khi có embedding batch + kiểm soát chi phí.
- **LangChain agent** “lang thang” → ưu tiên **LCEL + rule-based**, giới hạn tool.
- **TA** không ổn định → feature-flag + fallback Google.
- **LLM lệch schema** → JSON Schema validator + auto-repair + rule-based fallback.
