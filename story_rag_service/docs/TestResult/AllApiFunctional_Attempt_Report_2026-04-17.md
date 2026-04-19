# All API Functional Attempt Report (2026-04-17)

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
- POST /api/v2/worlds/4c1e04f3-bc46-4188-9c59-87e3bdbffce1/lorebook/character -> 200
- POST /api/v2/stories -> 200
- POST /api/v2/story/session -> 200
- PUT /api/v2/roleplay/story-state/story-bd981e2b-dae8-4bdf-a01a-8fe7ac0525da-v2 -> 200
- POST /api/v2/roleplay/personas -> 200
- POST /api/v2/script-designs -> 200
- POST /api/v2/stories/bd981e2b-dae8-4bdf-a01a-8fe7ac0525da/segments -> 200

### 5.2 Cleanup
- DELETE /api/v2/stories/bd981e2b-dae8-4bdf-a01a-8fe7ac0525da -> 200
- DELETE /api/v2/roleplay/personas/a8966fb8-da69-41d6-a143-ab195c8d2fea -> 200
- DELETE /api/v2/worlds/4c1e04f3-bc46-4188-9c59-87e3bdbffce1 -> 200

## 6. Outputs

- JSON: E:/CODE/AI_ChatBox/story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Run_2026-04-17.json
- Markdown: E:/CODE/AI_ChatBox/story_rag_service/docs/TestResult/AllApiFunctional_Attempt_Report_2026-04-17.md