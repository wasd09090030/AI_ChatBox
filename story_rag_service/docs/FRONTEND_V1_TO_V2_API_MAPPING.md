# 前端 v1 -> v2 接口迁移对照表（历史映射）

> 生成时间：2026-02-18
> 
> 2026-03-17 更新：
> - 前端当前已不再使用 `/api/v1/*`，主入口为 `/story`。
> - 当前仍在使用的客户端为 `frontend/src/domains/story/api/storyGenerationApi.ts`、`frontend/src/domains/settings/api/providerConfigApi.ts`、`frontend/src/domains/user/api/userIdentity.ts`。
> - 下表保留的是已完成迁移的历史映射，用于追溯 v1 到 v2 的替换关系与已下线路径。

## 后端当前可用 v2 接口（基线）

- `GET /api/v2/health`
- `POST /api/v2/story/generate`
- `GET /api/v2/providers`
- `POST /api/v2/providers/config`
- `POST /api/v2/providers/test-connection`
- `GET /api/v2/providers/{provider}/models`

## 历史迁移对照

| 历史前端调用位置 | 旧接口（v1） | 当前状态 / v2 对照 | 迁移动作结果 | 优先级 |
|---|---|---|---|---|
| 旧用户设置/密钥/会话客户端（已删除） | `GET /api/v1/user/settings` | 无直替 | 设置页已改为本地配置流，未再接入服务端用户设置接口 | P0 |
| 旧用户设置/密钥/会话客户端（已删除） | `PUT /api/v1/user/settings` | 无直替 | 同上 | P0 |
| 旧用户设置/密钥/会话客户端（已删除） | `POST /api/v1/user/api-key` | 无直替 | 服务端托管密钥路径已下线；现阶段以本地配置为主 | P0 |
| 旧用户设置/密钥/会话客户端（已删除） | `DELETE /api/v1/user/api-key/{provider}` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `GET /api/v1/user/api-key/{provider}` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `POST /api/v1/conversations` | 无直替 | 独立聊天会话 CRUD 已整体下线 | P0 |
| 旧用户设置/密钥/会话客户端（已删除） | `GET /api/v1/conversations` | 无直替 | 同上 | P0 |
| 旧用户设置/密钥/会话客户端（已删除） | `GET /api/v1/conversations/{id}` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `PUT /api/v1/conversations/{id}` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `DELETE /api/v1/conversations/{id}` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `POST /api/v1/conversations/{id}/messages` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `GET /api/v1/conversations/{id}/messages` | 无直替 | 同上 | P1 |
| 旧用户设置/密钥/会话客户端（已删除） | `PUT /api/v1/conversations/{id}/messages/{messageId}` | 无直替 | 同上 | P2 |
| 旧用户设置/密钥/会话客户端（已删除） | `DELETE /api/v1/conversations/{id}/messages` | 无直替 | 同上 | P2 |
| 旧流式聊天客户端（已删除） | 历史 v1 流式聊天端点 | `POST /api/v2/story/generate` | 独立聊天流式入口已下线，故事生成统一走故事主链路 | P0 |
| 旧流式聊天客户端（已删除） | `GET /api/v1/chat/providers` | `GET /api/v2/providers` | Provider 探测与模型列表已切换到 `/api/v2/providers*` | P1 |
| 旧通用聊天客户端（已删除） | `POST /api/v1/chat` | `POST /api/v2/story/generate` | 已由故事生成客户端接管 | P0 |
| 旧通用聊天客户端（已删除） | 历史 v1 流式聊天端点 | `POST /api/v2/story/generate` | 已取消独立聊天流式链路 | P0 |
| 旧通用聊天客户端（已删除） | `GET /api/v1/conversations` | 无直替 | 独立会话列表能力已下线 | P1 |
| 旧通用聊天客户端（已删除） | `PATCH /api/v1/conversations/{id}` | 无直替 | 同上 | P2 |
| 旧角色客户端（历史路径） | `/api/v1/roles*`（GET/POST/PUT/DELETE） | 无直替 | 角色体系仍以本地数据流或故事设计相关流程为主，尚未恢复独立 v2 角色接口 | P1 |

## 当前落地结论

1. 前端主调用已切到 `v2`，旧 `v1` 说明仅用于历史追溯。
2. 故事生成主链路已统一到 `POST /api/v2/story/generate`。
3. Provider 配置、连通性测试、模型列表已统一到 `/api/v2/providers*`。
4. 独立 AI 对话、会话 CRUD、服务端托管用户密钥路径已下线；如需恢复，必须以新的 v2 接口重新设计而不是复活旧路径。

## 历史改造顺序（留档）

- 第 1 批（阻断级）
  - 历史聊天入口与 API 版本常量
- 第 2 批（功能降级或替代）
  - 历史用户设置、密钥、会话接口
- 第 3 批（可延后）
  - 历史角色接口
