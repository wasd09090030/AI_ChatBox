# Task Record: 登录认证与用户数据隔离改造

## Date

- Local date: 2026-04-26

## Goal

- 为项目补齐账号密码登录能力。
- 不引入权限分级，所有登录用户功能一致。
- 让故事、世界、会话、角色扮演、远端 client-storage 等数据按真实用户隔离。
- 保留旧匿名 `storybox_user_id` / `chatbox_user_id` 的兼容迁移入口。

## Agreed Design

- 浏览器使用 `HttpOnly Cookie` 保存会话，后端通过 `current_user` 依赖解析身份。
- 前端新增独立登录页、认证 store、路由守卫和会话恢复流程，不再通过 `X-User-ID` 作为真实身份。
- 后端为核心业务资源补齐 `owner_user_id` 约束，并将相关路由切换为基于登录用户访问。
- 本地 `localStorage` 缓存也按 `user_id` 做命名空间切分，避免同浏览器切换账号时串缓存。
- legacy 认领采用保守策略：只迁移能明确证明属于 legacy user id 的设置与 owner 资源，不自动认领 owner 为空的数据。

## Stages

### Stage 1

- Scope:
  - 后端认证基础设施与 Cookie/CORS 接入。
- Changes:
  - 新增 `auth_routes`、`api/dependencies/auth.py`、`models/auth.py`、`auth_session_repository.py`、`auth_service.py`。
  - 扩展 `users` 认证字段与 `auth_sessions`。
  - `bootstrap/app_factory.py` 使用显式 CORS origins + `allow_credentials=True`。
  - `auth_service.py` 的密码哈希改为“优先 `pwdlib`，缺失时回退标准库 PBKDF2”。
- Review result:
  - `.venv` 缺少 `pwdlib` 时也可正常导入与运行，不再被可选依赖阻断。

### Stage 2

- Scope:
  - 核心 owner 迁移与后端业务路由鉴权收口。
- Changes:
  - `worlds`、`stories`、`script_designs`、`story_sessions`、`story_runtime_states`、`lorebook_entries`、`persona_profiles`、`story_states` 等链路补 owner 约束。
  - `client_storage_routes.py` 改为按 `current_user.id` 读写 `client_storage_entries`。
  - Alembic 新增 `20260426_0007_auth_owner_isolation.py`。
- Review result:
  - Alembic 已在 `.venv + 临时 SQLite` 上完整升级到 `20260426_0007`。

### Stage 3

- Scope:
  - 前端认证壳层与登录页。
- Changes:
  - 新增 `frontend/src/domains/auth/api/authApi.ts`、`frontend/src/stores/auth.ts`、`frontend/src/stores/pinia.ts`、`frontend/src/views/LoginView.vue`。
  - `router.beforeEach` 接入登录守卫，未登录跳转 `/login?redirect=...`。
  - `App.vue` 改为先解析认证，再恢复 config/story session。
  - `AppSidebar.vue` 补退出登录入口和当前账号展示。
- Review result:
  - 前端构建通过；登录页视觉采用“编辑台 / 手稿页”方向，未复用默认工作台壳层。

### Stage 4

- Scope:
  - 前端去除 `X-User-ID` 依赖，并处理本地/远端存储隔离。
- Changes:
  - `frontend/src/domains/user/api/userIdentity.ts` 改为只保留 legacy id 读取/清理。
  - `frontend/src/services/api.ts`、`storyGenerationApi.ts`、`storyAdjustmentApi.ts`、`fetchAvailableModels.ts`、`testApiConnection.ts`、`ragStory.ts`、`lorebookImport.ts` 等切到 Cookie + `credentials: 'include'`。
  - `frontend/src/utils/storage.ts` 增加用户作用域命名空间与旧 key 一次性本地迁移。
  - `config.ts`、`storySession.ts` 增加换账号后的内存态重置，避免跨用户 fallback 泄漏。
- Review result:
  - 解决了一个额外隐患：即使后端隔离了 `client-storage`，如果前端 localStorage 仍是全局 key，同浏览器多账号仍会串缓存。

### Stage 5

- Scope:
  - legacy 数据认领。
- Changes:
  - `auth_service.py` 新增保守版 `claim_legacy_user_data(...)`。
  - 认领当前只迁移：
    - legacy `user_settings` 中可安全覆盖到当前账号默认值的位置；
    - `owner_user_id == legacy_user_id` 的 worlds/stories/script_designs/story_sessions/lorebook/story_runtime/roleplay 相关资源。
  - `auth_routes.py` 的 `/api/v2/auth/claim-legacy` 不再是占位实现。
- Review result:
  - 该实现是“最小安全版本”，不会替当前账号认领 owner 为空的旧核心数据。

### Stage 6

- Scope:
  - 旧 SQLite 数据库兼容修复与登录态运行级 smoke。
- Changes:
  - `story_rag_service/services/database.py` 调整 legacy `owner_user_id` 列补齐顺序，避免在列不存在时抢先创建索引。
  - `story_rag_service/repositories/world_repository.py`
  - `story_rag_service/repositories/story_repository.py`
  - `story_rag_service/repositories/script_design_repository.py`
  - `story_rag_service/repositories/story_runtime_repository.py`
    - 统一改为先 `PRAGMA table_info(...)` 检查列、缺列时补 `owner_user_id`，再创建 owner 索引。
  - 新增 `story_rag_service/scripts/smoke_auth_story_runtime.py`
    - 以真实 `.venv` 启动的服务为目标；
    - 用真实登录 Cookie 跑 `/auth/login -> /providers/test-connection -> /worlds -> /stories -> /story/session -> /story/generate -> /stories/{id}/segments`；
    - 最后直接查 SQLite 验证 `worlds/stories/story_sessions/story_session_messages.owner_user_id` 与新用户一致。
- Review result:
  - 历史 `chatbox.db` 不再因 `login_identifier` / `owner_user_id` 缺列而启动失败。
  - 运行级 smoke 已通过，且确认真实前端链路是“生成后再追加 story segment”，而不是由 `/story/generate` 自动回写 `stories.segments`。

## Files Changed

- `frontend/src/router/index.ts`, `frontend/src/App.vue`, `frontend/src/components/layout/AppSidebar.vue`: 登录路由、守卫、工作台恢复顺序与登出入口。
- `frontend/src/domains/auth/api/authApi.ts`, `frontend/src/stores/auth.ts`, `frontend/src/views/LoginView.vue`, `frontend/src/stores/pinia.ts`: 认证 API、状态与登录页。
- `frontend/src/utils/storage.ts`, `frontend/src/stores/config.ts`, `frontend/src/stores/storySession.ts`: 用户作用域缓存与换账号内存态重置。
- `frontend/src/domains/story/api/storyGenerationApi.ts`, `frontend/src/domains/story/api/storyAdjustmentApi.ts`, `frontend/src/services/api.ts`, `frontend/src/services/fetchAvailableModels.ts`, `frontend/src/services/testApiConnection.ts`, `frontend/src/stores/ragStory.ts`, `frontend/src/utils/lorebookImport.ts`, `frontend/src/domains/settings/api/*`: 从 `X-User-ID` 切到 Cookie 凭证模式。
- `story_rag_service/api/v2/auth_routes.py`, `story_rag_service/api/dependencies/auth.py`, `story_rag_service/services/auth_service.py`, `story_rag_service/repositories/auth_session_repository.py`, `story_rag_service/models/auth.py`: 后端认证主干。
- `story_rag_service/api/client_storage_routes.py`, `story_rag_service/bootstrap/app_factory.py`, `story_rag_service/config.py`: Cookie/CORS 与 client-storage 用户隔离。
- `story_rag_service/services/database.py`, `story_rag_service/repositories/world_repository.py`, `story_rag_service/repositories/story_repository.py`, `story_rag_service/repositories/script_design_repository.py`, `story_rag_service/repositories/story_runtime_repository.py`: 旧 SQLite 库 owner 列兼容修复。
- `story_rag_service/scripts/smoke_auth_story_runtime.py`: 登录后世界/故事/会话/生成/片段落库运行级 smoke。
- `story_rag_service/migrations/versions/20260426_0007_auth_owner_isolation.py`: 认证/owner/client-storage 迁移。
- `PROJECT_STRUCTURE.md`: 更新认证、存储隔离与新职责边界说明。

## Sources Checked

- Context7:
  - `/fastapi/fastapi/0.128.0`: 核对 `Response.set_cookie`、`CORSMiddleware`、`allow_credentials` 与显式 origins 约束。
  - `/fastapi/fastapi`: 核对 `TestClient` / lifespan 测试行为，确认 `with TestClient(app)` 会触发生命周期。
  - `/vuejs/router`: 核对 `RouteMeta` 扩展、`beforeEach` 返回重定向对象、`query.redirect = to.fullPath` 的写法。
- Fetch:
  - `https://router.vuejs.org/guide/advanced/meta`，检查日期：2026-04-26。
  - `https://router.vuejs.org/guide/advanced/navigation-guards.html`，检查日期：2026-04-26。
  - `https://www.sqlite.org/lang_altertable.html`，检查日期：2026-04-26，用于确认 legacy SQLite `ADD COLUMN` 兼容处理方式。
  - `https://fastapi.tiangolo.com/tutorial/cors/`，检查日期：2026-04-26，抓取失败（robots / connection issue）。
  - `https://fastapi.tiangolo.com/advanced/response-cookies/`，检查日期：2026-04-26，抓取失败（robots / connection issue）。

## Validation

- 前端：
  - `cd frontend && npm run build`
  - 结果：通过。
- 后端语法编译：
  - `& '.venv\\Scripts\\python.exe' -m compileall story_rag_service\\bootstrap story_rag_service\\api story_rag_service\\models story_rag_service\\repositories story_rag_service\\services story_rag_service\\migrations`
  - 结果：通过。
- 应用导入验证：
  - `& '.venv\\Scripts\\python.exe' -c "from bootstrap.app_factory import create_app; app = create_app(); print(app.title); print(len(app.routes))"`
  - 结果：通过。
- 历史数据库启动验证：
  - `& '.venv\\Scripts\\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 8001`
  - 结果：真实 `story_rag_service/data/chatbox.db` 可完成启动，不再出现 `sqlite3.OperationalError: no such column: login_identifier/owner_user_id`。
- 迁移验证：
  - `& '.venv\\Scripts\\python.exe' -m alembic -c alembic.ini upgrade head`（临时 SQLite）
  - `SELECT version_num FROM alembic_version`
  - 结果：通过，版本为 `20260426_0007`。
- 后端 smoke：
  - `TestClient + 临时 SQLite` 验证 `register/login/me/logout`
  - `TestClient + 临时 SQLite` 验证 `client-storage` 跨用户隔离
  - `TestClient + 临时 SQLite` 验证 `/api/v2/auth/claim-legacy` 可迁移 legacy user settings 和 legacy owned world
  - 结果：通过。
- 运行级人工 smoke：
  - 启动命令：`& '.venv\\Scripts\\python.exe' -m uvicorn main:app --host 127.0.0.1 --port 8001`
  - 执行命令：`& '.venv\\Scripts\\python.exe' story_rag_service\\scripts\\smoke_auth_story_runtime.py --base-url http://127.0.0.1:8001 --database-path story_rag_service\\data\\chatbox.db`
  - 结果：通过。
  - 关键结论：
    - 真实登录 Cookie 可用；
    - 真实 `deepseek` provider 连通成功；
    - `/api/v2/story/generate` 真实返回成功并持久化 user/assistant 消息；
    - 前端真实主链路需要随后调用 `/api/v2/stories/{story_id}/segments` 才会把结果落到 `stories.segments`；
    - smoke 最终确认新建 `world/story/session/message` 的 `owner_user_id` 全部归属于登录账号。

## Risks and Follow-Up

- legacy 认领仍是保守版：不会自动认领 `owner_user_id IS NULL` 的核心业务数据，避免误归属。若要进一步迁移无 owner 历史数据，需要额外设计人工确认或更强归属判定。
- `client_storage` 的旧全局后端缓存无法安全自动归属到某个新账号；同浏览器数据依赖新的本地命名空间兼容，同服务端历史全局缓存需要单独清理策略。
- 当前已完成登录态下的真实生成 smoke，但仍主要覆盖“即兴模式 + 单轮生成 + 片段落库”。
- 若后续要把 scripted/runtime/story_state 也纳入同级别运行 smoke，建议在现有 `smoke_auth_story_runtime.py` 基础上扩展脚本设计夹具与 runtime 断言。
