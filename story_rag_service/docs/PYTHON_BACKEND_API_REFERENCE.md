# Story RAG Service Python 后端 API 完整说明文档

> 生成时间：2026-02-26 15:03:34 CST  
> 适用范围：`story_rag_service`（FastAPI 后端）  
> 说明：本文基于源码静态梳理（路由、Pydantic 模型、服务挂载关系）。当前环境未安装 `fastapi` 依赖，无法直接导出运行时 OpenAPI。
>
> 2026-03-17 更新：独立 AI 对话接口已从代码中删除。当前文档仅描述保留的故事生成、世界管理及 `/api/v2/providers*` Provider 配置接口。

## 1. 服务总览

- 框架：FastAPI
- 应用入口：`story_rag_service/main.py`
- API 文档地址：`/docs`（Swagger UI）、`/redoc`（ReDoc）
- OpenAPI 地址：`/openapi.json`（默认）
- 对外主版本前缀：`/api/v2`
- 健康检查：`GET /api/v2/health`
- 根接口：`GET /`

### 1.1 已挂载路由

- `app.include_router(v2_router, prefix="/api/v2", tags=["v2"])`
- `v2_router` 组合来源：`story_routes`、`world_story_routes`、`lorebook_routes`、`roleplay_routes`、`analytics_routes`、`provider_routes`

## 2. 全局约定

### 2.1 请求与响应

- 请求体格式：`application/json`
- 默认响应格式：JSON
- 特殊响应：`/api/v2/story/generate/stream` 为 `text/event-stream`

### 2.2 Header 约定

- `X-Request-ID`：由中间件写回响应头（用于链路追踪）
- `X-API-Version`：当路径以 `/api/v2/` 开头时写回 `v2`
- `X-User-ID`：
  - `POST /api/v2/story/generate`：可选
  - `/api/v2/providers*`：必需

### 2.3 CORS

当前配置为宽松模式：

- `allow_origins=["*"]`
- `allow_methods=["*"]`
- `allow_headers=["*"]`
- `allow_credentials=True`

### 2.4 鉴权

- 当前没有 JWT/OAuth 统一鉴权中间件
- 用户身份主要通过 `X-User-ID` 透传（用于上下文与密钥查询）

### 2.5 错误处理

- 主要使用 `HTTPException`
- 常见状态码：
  - `200`：成功（默认）
  - `404`：资源不存在
  - `500`：服务内部错误/生成失败

## 3. API 清单（已挂载，真实可调用）

## 3.1 Root 与健康检查

### 3.1.1 GET `/`

- 描述：服务根信息
- 请求参数：无
- 响应示例：

```json
{
  "service": "Story RAG Service",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "api": "/api/v2"
}
```

### 3.1.2 GET `/api/v2/health`

- 描述：v2 健康状态
- 请求参数：无
- 响应示例：

```json
{
  "status": "healthy",
  "api_version": "v2"
}
```

## 3.2 故事生成接口

### 3.2.1 POST `/api/v2/story/generate`

- 描述：核心故事生成入口（RAG + 图编排 + 可选 roleplay 状态）
- Header：
  - `X-User-ID`（可选）
- 请求体：`V2GenerateRequest`
- 响应体：`V2GenerateResponse`
- 失败场景：生成链路异常返回 `500`

请求示例：

```json
{
  "session_id": "sess_001",
  "thread_id": null,
  "user_input": "主角进入古城，继续推进剧情",
  "world_id": "world_123",
  "model": "deepseek-chat",
  "temperature": 0.8,
  "max_tokens": 2000,
  "use_rag": true,
  "top_k": 5,
  "style": "narrative",
  "language": "zh-CN",
  "character_card_id": null,
  "persona_id": null,
  "story_state_mode": "light"
}
```

响应示例：

```json
{
  "version": "v2",
  "session_id": "sess_001",
  "thread_id": "thread_001",
  "output_text": "夜色垂落，城门吱呀而开……",
  "contexts": [],
  "activation_logs": [],
  "story_state_snapshot": null,
  "summary_memory_snapshot": null,
  "model": "deepseek-chat",
  "generation_time": 1.24,
  "timestamp": "2026-02-26T15:03:34"
}
```

## 3.3 世界与故事管理

## 3.3.1 世界（World）

### GET `/api/v2/worlds`

- 描述：获取世界列表
- Query：
  - `world_id`（可选，具体行为由 service 实现决定）
- 响应：`World[]`

### POST `/api/v2/worlds`

- 描述：创建世界
- 请求体：`WorldCreate`
- 响应：`World`

### GET `/api/v2/worlds/{world_id}`

- 描述：获取单个世界
- Path：
  - `world_id`（必填）
- 响应：`World`
- 错误：不存在返回 `404`

### PUT `/api/v2/worlds/{world_id}`

- 描述：更新世界
- Path：
  - `world_id`（必填）
- 请求体：`WorldUpdate`
- 响应：`World`
- 错误：不存在返回 `404`

### DELETE `/api/v2/worlds/{world_id}`

- 描述：删除世界
- Path：
  - `world_id`（必填）
- 响应：删除结果（JSON）
- 错误：不存在返回 `404`

## 3.3.2 故事（Story）

### GET `/api/v2/stories`

- 描述：获取故事列表
- Query：
  - `world_id`（可选，用于按世界过滤）
- 响应：`StoredStory[]`

### POST `/api/v2/stories`

- 描述：创建故事
- 请求体：`StoryCreate`
- 响应：`StoredStory`
- 错误：关联世界不存在返回 `404`

### GET `/api/v2/stories/{story_id}`

- 描述：获取故事详情
- Path：
  - `story_id`（必填）
- 响应：`StoredStory`
- 错误：不存在返回 `404`

### PUT `/api/v2/stories/{story_id}`

- 描述：更新故事
- Path：
  - `story_id`（必填）
- 请求体：`StoryUpdate`
- 响应：`StoredStory`
- 错误：不存在返回 `404`

### DELETE `/api/v2/stories/{story_id}`

- 描述：删除故事
- Path：
  - `story_id`（必填）
- 响应示例：

```json
{
  "success": true,
  "story_id": "story_001"
}
```

- 错误：不存在返回 `404`

### POST `/api/v2/stories/{story_id}/segments`

- 描述：为故事追加片段
- Path：
  - `story_id`（必填）
- 请求体：`StorySegmentCreate`
- 响应：更新后的 `StoredStory`
- 错误：不存在返回 `404`

## 3.4 Lorebook 接口

### GET `/api/v2/lorebook/entries`

- 描述：查询 Lorebook 条目
- Query：
  - `world_id`（可选）
- 响应示例：

```json
{
  "entries": [],
  "count": 0,
  "world_id": "world_123"
}
```

### POST `/api/v2/worlds/{world_id}/lorebook/character`

- 描述：新增角色条目（Character -> LorebookEntry）
- Path：
  - `world_id`（必填）
- 请求体：`Character`
- 响应：`LorebookEntry`
- 错误：世界不存在返回 `404`

### POST `/api/v2/worlds/{world_id}/lorebook/location`

- 描述：新增地点条目（Location -> LorebookEntry）
- Path：
  - `world_id`（必填）
- 请求体：`Location`
- 响应：`LorebookEntry`
- 错误：世界不存在返回 `404`

### POST `/api/v2/worlds/{world_id}/lorebook/event`

- 描述：新增事件条目（Event -> LorebookEntry）
- Path：
  - `world_id`（必填）
- 请求体：`Event`
- 响应：`LorebookEntry`
- 错误：世界不存在返回 `404`

### DELETE `/api/v2/lorebook/entry/{entry_id}`

- 描述：删除 Lorebook 条目
- Path：
  - `entry_id`（必填）
- 响应示例：

```json
{
  "success": true,
  "entry_id": "entry_001"
}
```

- 错误：条目不存在返回 `404`

## 3.5 Roleplay 接口

## 3.5.1 Character Card

### GET `/api/v2/roleplay/character-cards`

- 描述：角色卡列表
- 响应：`CharacterCard[]`

### POST `/api/v2/roleplay/character-cards`

- 描述：创建角色卡
- 请求体：`CharacterCardCreate`
- 响应：`CharacterCard`

### GET `/api/v2/roleplay/character-cards/{card_id}`

- 描述：角色卡详情
- Path：`card_id`
- 响应：`CharacterCard`
- 错误：不存在返回 `404`

### PUT `/api/v2/roleplay/character-cards/{card_id}`

- 描述：更新角色卡
- Path：`card_id`
- 请求体：`CharacterCardUpdate`
- 响应：`CharacterCard`
- 错误：不存在返回 `404`

### DELETE `/api/v2/roleplay/character-cards/{card_id}`

- 描述：删除角色卡
- Path：`card_id`
- 响应：`{"success": true, "card_id": "..."}`（结构以实现为准）
- 错误：不存在返回 `404`

## 3.5.2 Persona

### GET `/api/v2/roleplay/personas`

- 描述：人设列表
- 响应：`PersonaProfile[]`

### POST `/api/v2/roleplay/personas`

- 描述：创建人设
- 请求体：`PersonaProfileCreate`
- 响应：`PersonaProfile`

### GET `/api/v2/roleplay/personas/{persona_id}`

- 描述：人设详情
- Path：`persona_id`
- 响应：`PersonaProfile`
- 错误：不存在返回 `404`

### PUT `/api/v2/roleplay/personas/{persona_id}`

- 描述：更新人设
- Path：`persona_id`
- 请求体：`PersonaProfileUpdate`
- 响应：`PersonaProfile`
- 错误：不存在返回 `404`

### DELETE `/api/v2/roleplay/personas/{persona_id}`

- 描述：删除人设
- Path：`persona_id`
- 响应：`{"success": true, "persona_id": "..."}`（结构以实现为准）
- 错误：不存在返回 `404`

## 3.5.3 Story State

### GET `/api/v2/roleplay/story-state/{session_id}`

- 描述：读取会话故事状态
- Path：`session_id`
- 响应：`StoryState`
- 错误：不存在返回 `404`

### PUT `/api/v2/roleplay/story-state/{session_id}`

- 描述：更新会话故事状态
- Path：`session_id`
- 请求体：`StoryStateUpdate`
- 响应：`StoryState`

## 4. 数据模型字段定义（完整）

## 4.1 `api/v2/schemas.py`

## 4.1.1 V2GenerateRequest

| 字段 | 类型 | 必填 | 默认值/约束 |
|---|---|---|---|
| `session_id` | `str` | 是 | - |
| `thread_id` | `Optional[str]` | 否 | `None` |
| `user_input` | `str` | 是 | - |
| `world_id` | `Optional[str]` | 否 | `None` |
| `model` | `Optional[str]` | 否 | `None` |
| `temperature` | `Optional[float]` | 否 | `0.8`，`0 <= x <= 2` |
| `max_tokens` | `Optional[int]` | 否 | `2000`，`1 <= x <= 32000` |
| `use_rag` | `bool` | 否 | `true` |
| `top_k` | `Optional[int]` | 否 | `5` |
| `style` | `Optional[str]` | 否 | `"narrative"` |
| `language` | `str` | 否 | `"zh-CN"` |
| `character_card_id` | `Optional[str]` | 否 | `None` |
| `persona_id` | `Optional[str]` | 否 | `None` |
| `story_state_mode` | `Optional[str]` | 否 | `None`，建议值 `off/light/strict` |

## 4.1.2 V2GenerateResponse

| 字段 | 类型 | 必填 | 默认值/说明 |
|---|---|---|---|
| `version` | `str` | 是 | `"v2"` |
| `session_id` | `str` | 是 | 会话 ID |
| `thread_id` | `str` | 是 | 线程 ID |
| `output_text` | `str` | 是 | 生成文本 |
| `contexts` | `List[V2ContextItem]` | 否 | `[]` |
| `activation_logs` | `List[Dict[str, Any]]` | 否 | `[]` |
| `story_state_snapshot` | `Optional[Dict[str, Any]]` | 否 | `None` |
| `summary_memory_snapshot` | `Optional[Dict[str, Any]]` | 否 | `None` |
| `model` | `str` | 是 | 实际模型 |
| `generation_time` | `float` | 是 | 生成耗时（秒） |
| `timestamp` | `datetime` | 否 | 当前时间 |

## 4.2 `models/world.py`

## 4.2.1 World

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `id` | `str` | 否 | `uuid4()` |
| `name` | `str` | 是 | - |
| `description` | `str` | 是 | - |
| `genre` | `Optional[str]` | 否 | `"fantasy"` |
| `setting` | `Optional[str]` | 否 | `None` |
| `rules` | `Optional[str]` | 否 | `None` |
| `style_preset` | `Optional[str]` | 否 | `None` |
| `narrative_tone` | `Optional[str]` | 否 | `None` |
| `pacing_style` | `Optional[str]` | 否 | `None` |
| `vocabulary_style` | `Optional[str]` | 否 | `None` |
| `style_tags` | `List[str]` | 否 | `[]` |
| `default_time_of_day` | `Optional[str]` | 否 | `None` |
| `default_weather` | `Optional[str]` | 否 | `None` |
| `default_mood` | `Optional[str]` | 否 | `None` |
| `metadata` | `Dict[str, Any]` | 否 | `{}` |
| `created_at` | `datetime` | 否 | `now()` |
| `updated_at` | `datetime` | 否 | `now()` |

## 4.2.2 WorldCreate

字段与 `World` 基本对应，去掉 `id/created_at/updated_at`，其中必填字段为：

- `name`
- `description`

## 4.2.3 WorldUpdate

- 与 `WorldCreate` 对应字段一致
- 所有字段均为可选（增量更新）

## 4.3 `models/stored_story.py`

## 4.3.1 StoredStory

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `id` | `str` | 否 | `uuid4()` |
| `world_id` | `str` | 是 | - |
| `world_name` | `str` | 是 | - |
| `title` | `str` | 否 | `"未命名故事"` |
| `segments` | `List[StorySegment]` | 否 | `[]` |
| `created_at` | `str` | 否 | `now().isoformat()` |
| `updated_at` | `str` | 否 | `now().isoformat()` |
| `metadata` | `Dict[str, Any]` | 否 | `{}` |

## 4.3.2 StoryCreate

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `world_id` | `str` | 是 | - |
| `title` | `str` | 否 | `"未命名故事"` |
| `metadata` | `Dict[str, Any]` | 否 | `{}` |

## 4.3.3 StoryUpdate

| 字段 | 类型 | 必填 |
|---|---|---|
| `title` | `Optional[str]` | 否 |
| `metadata` | `Optional[Dict[str, Any]]` | 否 |

## 4.3.4 StorySegmentCreate

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `prompt` | `str` | 是 | - |
| `content` | `str` | 是 | - |
| `retrieved_context` | `List[str]` | 否 | `[]` |

## 4.4 `models/lorebook.py`

## 4.4.1 LorebookEntry

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `id` | `Optional[str]` | 否 | `None` |
| `world_id` | `str` | 是 | - |
| `type` | `LorebookType` | 是 | - |
| `name` | `str` | 是 | - |
| `description` | `str` | 是 | - |
| `keywords` | `List[str]` | 否 | `[]` |
| `metadata` | `Dict[str, Any]` | 否 | `{}` |
| `created_at` | `datetime` | 否 | `now()` |
| `updated_at` | `datetime` | 否 | `now()` |

## 4.4.2 Character（请求模型）

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `name` | `str` | 是 | - |
| `age` | `Optional[int]` | 否 | `None` |
| `gender` | `Optional[str]` | 否 | `None` |
| `appearance` | `Optional[str]` | 否 | `None` |
| `personality` | `Optional[str]` | 否 | `None` |
| `background` | `Optional[str]` | 否 | `None` |
| `relationships` | `Dict[str, str]` | 否 | `{}` |
| `abilities` | `List[str]` | 否 | `[]` |
| `inventory` | `List[str]` | 否 | `[]` |
| `current_location` | `Optional[str]` | 否 | `None` |
| `speaking_style` | `Optional[str]` | 否 | `None` |
| `accent` | `Optional[str]` | 否 | `None` |
| `verbal_tics` | `List[str]` | 否 | `[]` |
| `vocabulary_level` | `str` | 否 | `"normal"` |
| `emotional_expression` | `Optional[str]` | 否 | `None` |
| `speech_examples` | `List[str]` | 否 | `[]` |

## 4.4.3 Location（请求模型）

| 字段 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `name` | `str` | 是 | - |
| `description` | `str` | 是 | - |
| `region` | `Optional[str]` | 否 | `None` |
| `climate` | `Optional[str]` | 否 | `None` |
| `population` | `Optional[int]` | 否 | `None` |
| `notable_features` | `List[str]` | 否 | `[]` |
| `connected_locations` | `List[str]` | 否 | `[]` |
| `inhabitants` | `List[str]` | 否 | `[]` |
| `default_time_of_day` | `Optional[str]` | 否 | `None` |
| `default_weather` | `Optional[str]` | 否 | `None` |
| `mood` | `Optional[str]` | 否 | `None` |
| `lighting` | `Optional[str]` | 否 | `None` |
| `sensory_visual` | `List[str]` | 否 | `[]` |
| `sensory_auditory` | `List[str]` | 否 | `[]` |
| `sensory_olfactory` | `List[str]` | 否 | `[]` |
| `sensory_tactile` | `List[str]` | 否 | `[]` |
| `ambient_sounds` | `List[str]` | 否 | `[]` |
| `special_effects` | `List[str]` | 否 | `[]` |

## 4.4.4 Event（请求模型）

| 字段 | 类型 | 必填 | 默认值/约束 |
|---|---|---|---|
| `name` | `str` | 是 | - |
| `description` | `str` | 是 | - |
| `time` | `Optional[str]` | 否 | `None` |
| `location` | `Optional[str]` | 否 | `None` |
| `participants` | `List[str]` | 否 | `[]` |
| `consequences` | `Optional[str]` | 否 | `None` |
| `importance` | `int` | 否 | `5`，`1 <= x <= 10` |

## 4.5 `models/roleplay.py`

## 4.5.1 CharacterCard / Create / Update

`CharacterCard` 字段：

- `id: str`（默认 `uuid4()`）
- `name: str`（必填，`min_length=1`）
- `description: str`（默认 `""`）
- `system_prompt: str`（默认 `""`）
- `first_message: Optional[str]`（默认 `None`）
- `example_messages: List[str]`（默认 `[]`）
- `tags: List[str]`（默认 `[]`）
- `metadata: Dict[str, Any]`（默认 `{}`）
- `created_at: datetime`（默认 `now()`）
- `updated_at: datetime`（默认 `now()`）

`CharacterCardCreate`：同上去掉 `id/created_at/updated_at`。  
`CharacterCardUpdate`：对应字段全部可选。

## 4.5.2 PersonaProfile / Create / Update

`PersonaProfile` 字段：

- `id: str`（默认 `uuid4()`）
- `name: str`（必填）
- `description: str`（默认 `""`）
- `title: Optional[str]`（默认 `None`）
- `traits: List[str]`（默认 `[]`）
- `metadata: Dict[str, Any]`（默认 `{}`）
- `created_at: datetime`（默认 `now()`）
- `updated_at: datetime`（默认 `now()`）

`PersonaProfileCreate`：同上去掉 `id/created_at/updated_at`。  
`PersonaProfileUpdate`：对应字段全部可选。

## 4.5.3 StoryState / Update

`StoryState` 字段：

- `session_id: str`（必填）
- `chapter: Optional[str]`（默认 `None`）
- `objective: Optional[str]`（默认 `None`）
- `conflict: Optional[str]`（默认 `None`）
- `clues: List[str]`（默认 `[]`）
- `relationship_arcs: Dict[str, Any]`（默认 `{}`）
- `metadata: Dict[str, Any]`（默认 `{}`）
- `updated_at: datetime`（默认 `now()`）

`StoryStateUpdate` 字段（全部可选）：

- `chapter`
- `objective`
- `conflict`
- `clues`
- `relationship_arcs`
- `metadata`

## 5. Provider 配置接口

## 5.1 GET `/api/v2/providers`

- Header：`X-User-ID`（必填）
- 描述：获取当前用户各 Provider 的可用状态、默认 Base URL、已保存自定义 Base URL。
- 响应结构：

```json
{
  "providers": [
    {
      "provider": "openai",
      "available": true,
      "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
      "default_base_url": "https://api.openai.com",
      "custom_base_url": "",
      "protocol": "openai_compat"
    },
    {
      "provider": "deepseek",
      "available": true,
      "models": ["deepseek-chat", "deepseek-coder"],
      "default_base_url": "https://api.deepseek.com",
      "custom_base_url": "",
      "protocol": "openai_compat"
    }
  ]
}
```

## 5.2 POST `/api/v2/providers/config`

- Header：`X-User-ID`（必填）
- 描述：保存或清空指定 Provider 的 `api_key` / `base_url`。
- 请求体字段：
  - `provider: str`（必填）
  - `api_key: Optional[str]`
  - `base_url: Optional[str]`

## 5.3 POST `/api/v2/providers/test-connection`

- Header：`X-User-ID`（必填）
- 描述：探测指定 Provider 的可达性与鉴权状态。
- 请求体字段：
  - `provider: str`（必填）
  - `base_url: Optional[str]`

## 5.4 GET `/api/v2/providers/{provider}/models`

- Header：`X-User-ID`（必填）
- 描述：拉取指定 Provider 的模型列表；失败时回退到内置预设模型。
- Query：
  - `base_url`（可选）

## 6. 调用示例（curl）

## 6.1 健康检查

```bash
curl -sS http://127.0.0.1:8000/api/v2/health
```

## 6.2 创建世界

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v2/worlds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "修仙世界",
    "description": "一个充满仙门、秘境和法宝的世界",
    "genre": "xianxia"
  }'
```

## 6.3 生成故事

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v2/story/generate \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user_001" \
  -d '{
    "session_id": "sess_001",
    "user_input": "继续剧情",
    "use_rag": true,
    "language": "zh-CN"
  }'
```

## 7. 文档与源码映射（关键文件）

- 应用入口：`story_rag_service/main.py`
- v2 路由聚合：`story_rag_service/api/v2/__init__.py`
- 生成接口：`story_rag_service/api/v2/story_routes.py`
- 世界/故事接口：`story_rag_service/api/v2/world_story_routes.py`
- Lorebook 接口：`story_rag_service/api/v2/lorebook_routes.py`
- Roleplay 接口：`story_rag_service/api/v2/roleplay_routes.py`
- Provider 接口：`story_rag_service/api/v2/provider_routes.py`
- v2 Schema：`story_rag_service/api/v2/schemas.py`
- 业务模型：`story_rag_service/models/world.py`
- 业务模型：`story_rag_service/models/stored_story.py`
- 业务模型：`story_rag_service/models/lorebook.py`
- 业务模型：`story_rag_service/models/roleplay.py`
## 8. 已知注意事项

- 当前默认只暴露 `/api/v2/*`，旧版 v1 已下线。
- 独立 AI 对话路由已删除，不再提供 `/chat/*`。
- 目前未提供统一分页参数（如 `limit/offset`）与排序参数，调用方需按现状处理。
