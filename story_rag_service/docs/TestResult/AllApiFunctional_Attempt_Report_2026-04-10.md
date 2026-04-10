# All API Functional Attempt Report (2026-04-10)

## 1. Scope

- OpenAPI-driven traversal of all routes
- Dependency-aware fixture preparation before probing
- Failure policy: only network errors and 5xx count as FAIL

## 2. Summary

- base_url: http://127.0.0.1:8012
- openapi_status: 200
- total_endpoints: 69
- PASS: 69
- WARN: 0
- SKIP: 0
- FAIL: 0
- transport_available_endpoints: 69

## 3. FAIL Details

- No FAIL endpoints.

## 4. WARN Details

- No WARN endpoints.

## 5. Fixture Lifecycle

### 5.1 Prepare
- GET /api/v2/health -> 200
- POST /api/v2/worlds -> 200
- POST /api/v2/worlds/7c9eefab-1dda-420b-b02d-1c9709f73b8d/lorebook/character -> 200
- POST /api/v2/stories -> 200
- POST /api/v2/story/session -> 200
- PUT /api/v2/roleplay/story-state/story-2d231748-c23d-414b-93fd-bc84d293e7bf-v2 -> 200
- POST /api/v2/roleplay/personas -> 200
- POST /api/v2/script-designs -> 200
- POST /api/v2/stories/2d231748-c23d-414b-93fd-bc84d293e7bf/segments -> 200

### 5.2 Cleanup
- DELETE /api/v2/stories/2d231748-c23d-414b-93fd-bc84d293e7bf -> 200
- DELETE /api/v2/roleplay/personas/db6c49bd-1181-4391-9247-8467aff02959 -> 200
- DELETE /api/v2/worlds/7c9eefab-1dda-420b-b02d-1c9709f73b8d -> 200

## 6. Outputs

- JSON: E:/CODE/AI_ChatBox/story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Run_2026-04-10.json
- Markdown: E:/CODE/AI_ChatBox/story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Report_2026-04-10.md