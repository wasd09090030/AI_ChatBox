# Story Adjustment Windows Smoke 路线（2026-03-17）

## 1. 目标

本 smoke 路线用于在 **Windows 原生环境** 下验证“故事调整”功能的最小可用链路，避免 WSL 环境启动慢、I/O 重、前后端热更新卡顿对验证造成干扰。

本轮 smoke 的目标不是做全面回归，而是快速确认以下关键点：

1. 前后端都能在 Windows 下独立启动。
2. “故事调整”路由可进入，且与“故事创作”共享当前故事工作区。
3. 单段内文本选区后可触发 AI 润色。
4. 润色只进入草稿层，不立即写库。
5. 撤销只回退未保存草稿。
6. 保存后故事正文更新成功。
7. 保存后回到“故事创作”页面能看到最新文本。
8. 保存后继续续写时，模型沿用的是新文本上下文，而不是旧文本。

---

## 2. 测试范围

### 2.1 覆盖范围

- `frontend/src/views/StoryAdjustmentView.vue`
- `frontend/src/stores/storyWorkspace.ts`
- `frontend/src/domains/story/api/storyAdjustmentApi.ts`
- `story_rag_service/api/v2/story/adjustment_routes.py`
- `story_rag_service/api/v2/world_story_routes.py`
- `story_rag_service/services/story_consistency_rebuild_service.py`

### 2.2 本轮不覆盖

- 跨多个 segment 的选区润色
- 持久化版本回滚
- 自动化 UI 测试
- 高并发或长会话压力验证

---

## 3. 前置条件

### 3.1 Windows 环境建议

- 使用 **PowerShell**，不要在 WSL 里启动本轮 smoke。
- 建议开两个 PowerShell 窗口：
  - 窗口 A：后端
  - 窗口 B：前端

### 3.2 依赖准备

- 前端依赖已安装：`frontend/node_modules` 可用
- 后端虚拟环境已安装：`story_rag_service/myenv`
- 如果 embedding 模型还没准备好，先在 Windows 下执行一次：

```powershell
Set-Location E:\CODE\AI_ChatBox\story_rag_service
.\myenv\Scripts\Activate.ps1
python download_model.py
```

### 3.3 本轮建议使用隔离数据目录

为了不污染你日常使用的数据，建议本轮 smoke 使用临时目录承载：

- SQLite 数据库
- Chroma 目录
- LangGraph checkpoint

这样测试后可直接删除，不影响现有故事。

---

## 4. Windows 启动方式

## 4.1 后端启动（PowerShell 窗口 A）

```powershell
Set-Location E:\CODE\AI_ChatBox\story_rag_service
.\myenv\Scripts\Activate.ps1

$SmokeRoot = Join-Path $env:TEMP "ai_chatbox_story_adjustment_smoke_20260317"
New-Item -ItemType Directory -Force -Path $SmokeRoot | Out-Null

$env:API_HOST = "127.0.0.1"
$env:API_PORT = "8012"
$env:API_RELOAD = "false"
$env:DATABASE_PATH = Join-Path $SmokeRoot "chatbox.db"
$env:CHROMA_PERSIST_DIRECTORY = Join-Path $SmokeRoot "chroma_db"
$env:LANGGRAPH_CHECKPOINT_SQLITE_PATH = Join-Path $SmokeRoot "langgraph_checkpoints.db"
$env:HUGGINGFACE_CACHE_DIR = Join-Path (Get-Location) "data\huggingface_cache"

uvicorn main:app --host 127.0.0.1 --port 8012
```

预期：

- 控制台无启动即退出
- 服务监听 `http://127.0.0.1:8012`

### 4.1.1 后端健康检查

另开一个 PowerShell 或直接浏览器访问：

```powershell
Invoke-RestMethod http://127.0.0.1:8012/api/v2/health
```

预期：

- HTTP 200
- 返回：

```json
{
  "status": "healthy",
  "api_version": "v2"
}
```

## 4.2 前端启动（PowerShell 窗口 B）

```powershell
Set-Location E:\CODE\AI_ChatBox\frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:8012"
npm run dev -- --host 127.0.0.1 --port 5174
```

预期：

- 打开 `http://127.0.0.1:5174`
- 页面可正常加载

---

## 5. Provider 前置检查

“故事调整”的 AI 润色与“故事创作”的模型配置共用一套 provider/model 链路，所以本轮 smoke 在进入正文测试前，必须先确认 provider 可用。

## 5.1 获取当前 `X-User-ID`

打开前端页面后，在浏览器控制台执行：

```js
localStorage.getItem('storybox_user_id')
```

记下结果，例如：

```text
user_1742200000000_xxxxxxxx
```

## 5.2 检查 provider 状态

在 PowerShell 中执行：

```powershell
$UserId = "把刚才控制台里的 storybox_user_id 粘贴到这里"

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8012/api/v2/providers" `
  -Headers @{ "X-User-ID" = $UserId }
```

预期：

- 返回 `providers` 列表
- 当前默认 provider 至少有一个 `available=true`

## 5.3 检查 provider 连通性

以 deepseek 为例：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8012/api/v2/providers/test-connection" `
  -Headers @{ "X-User-ID" = $UserId } `
  -ContentType "application/json" `
  -Body '{"provider":"deepseek"}'
```

预期：

- `success=true`
- `status=ok`

如果失败，先不要进入故事调整 smoke，先在前端 `Dashboard -> API & 模型` 里把 API Key 配好，再继续。

---

## 6. Smoke 路线

## 6.1 用故事创作页准备测试素材

目标：

- 为故事调整页准备至少 2 段已有 AI 输出内容

步骤：

1. 打开 `http://127.0.0.1:5174/story`
2. 选择一个已有世界；如果没有，先在 `Dashboard -> Lorebook` 新建一个简单世界
3. 新建一个故事
4. 发送至少两轮故事生成，让当前故事里有至少 2 个 AI segment

建议 prompt：

- 第 1 轮：`主角深夜回到旧宅，发现门口有一封没有署名的信。`
- 第 2 轮：`主角拆开信，发现里面提到阁楼和一把生锈的钥匙。`

预期：

- `StoryView` 中出现至少两段 AI 输出
- 当前故事能正常继续续写

通过条件：

- 有可供选区的真实 story segment 内容

---

## 6.2 进入故事调整页并确认共享工作区

目标：

- 验证 `/story-adjustment` 与 `/story` 共享同一个当前故事

步骤：

1. 点击左侧导航“故事调整”
2. 观察顶部标题与左侧故事列表

预期：

- 路由切换到 `http://127.0.0.1:5174/story-adjustment`
- 当前选中的世界和故事没有丢失
- 页面中按顺序展示该故事已有的 `segments`

通过条件：

- 不需要重新选故事
- 段落内容与故事创作页一致

---

## 6.3 单段选区与 AI 润色草稿

目标：

- 验证单段内选区可触发润色，且结果只进入草稿层

步骤：

1. 在故事调整页中，选中某一段 AI 输出里的 1 到 2 句
2. 等页面出现“AI 润色”按钮
3. 点击“AI 润色”
4. 在弹窗中：
   - 先选 `语言润色`
   - 自定义 prompt 先留空
5. 点击“应用润色”

预期：

- Network 面板出现：
  - `POST /api/v2/story/adjustments/polish`
- 返回 200
- 页面该段内容变成新的草稿文本
- 该段出现“草稿中”标记
- 顶部显示“未保存”或相近状态

关键验证点：

- 此时 **不要** 立即切回故事创作页期望看到变化
- 因为此时还没保存，变更应该只存在于故事调整页本地草稿

通过条件：

- 润色后的文本只影响当前页草稿，不影响正式故事正文

---

## 6.4 撤销本地草稿

目标：

- 验证撤销只回退未保存修改

步骤：

1. 在刚才润色成功后，点击顶部“撤销本地改动”

预期：

- 最近一次润色被回退
- 段落恢复成保存前文本
- 若该段没有其他草稿操作，则“草稿中”标记消失

通过条件：

- 撤销只影响当前未保存草稿，不调用后端 commit 接口

---

## 6.5 二次润色并保存

目标：

- 验证“预设方案 + 自定义 prompt + 保存”完整闭环

步骤：

1. 再次选中同一段或另一段文本
2. 点击“AI 润色”
3. 选择 `文风统一`
4. 输入自定义 prompt，例如：

```text
语气更冷一点，但不要变成诗化表达。
```

5. 点击“应用润色”
6. 确认页面进入草稿态
7. 点击“保存到故事”

预期：

- Network 面板先出现：
  - `POST /api/v2/story/adjustments/polish`
- 点击保存后再出现：
  - `POST /api/v2/stories/{story_id}/adjustments/commit`
- commit 返回 200
- commit 响应体中应包含：
  - `story`
  - `session_id`
  - `rebuild_summary_reset`
  - `rebuild_history_reindexed`
  - `warnings`

通过条件：

- 保存后页面不再是脏状态
- 草稿标记消失
- 没有出现保存成功但页面仍停留在旧文本的情况

---

## 6.6 回到故事创作页验证跨页面同步

目标：

- 验证保存后的新内容已经同步到 `StoryView`

步骤：

1. 点击左侧“故事创作”
2. 打开同一个故事
3. 找到刚才被改写的段落

预期：

- 该段已经变成保存后的新文本
- 不需要刷新浏览器，不需要重新进入故事

通过条件：

- `StoryView` 与 `StoryAdjustmentView` 显示一致

---

## 6.7 保存后继续续写

目标：

- 验证保存后正式续写上下文已切到新文本

步骤：

1. 在 `StoryView` 输入新一轮 prompt，例如：

```text
主角把那封信重新折好，决定立刻去阁楼确认线索。
```

2. 发送一轮续写

预期：

- 模型生成的内容应承接“修改后的段落措辞与事实”
- 不应出现明显沿用“旧文本版本”的表达

关键观察点：

- 如果你刚才把某句语气从“平缓”改成“冷峻”，续写通常会更贴近新语气
- 如果你刚才修改了某个关键措辞，续写不应继续沿用旧措辞作为最近上下文

通过条件：

- 后续续写逻辑明显以保存后的版本为基础

---

## 6.8 浏览器刷新后的持久性验证

目标：

- 验证保存后的故事正文能在重新加载后保持

步骤：

1. 在 `StoryView` 或 `StoryAdjustmentView` 刷新浏览器
2. 重新打开同一个故事

预期：

- 改写后的段落依然存在
- 不会恢复成保存前内容

通过条件：

- 保存结果持久化成功

---

## 7. 推荐记录方式

建议你在 smoke 时按下表记录：

| 步骤 | 操作 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | 健康检查 | `/health` 200 |  |  |
| 2 | provider 检查 | `available=true` |  |  |
| 3 | 故事创作准备两段内容 | 至少 2 个 AI segment |  |  |
| 4 | 进入故事调整页 | 自动带出当前故事 |  |  |
| 5 | 单段选区润色 | `polish` 200，进入草稿态 |  |  |
| 6 | 撤销草稿 | 本地回退成功 |  |  |
| 7 | 保存改动 | `commit` 200 |  |  |
| 8 | 回到故事创作页 | 新文本可见 |  |  |
| 9 | 再续写一轮 | 基于新文本上下文续写 |  |  |
| 10 | 刷新后重开故事 | 修改仍存在 |  |  |

---

## 8. 故障快速定位

## 8.1 `/health` 不通

优先检查：

- 后端窗口是否正常启动
- `8012` 端口是否被占用
- PowerShell 环境变量是否生效

## 8.2 `/providers` 返回不可用

优先检查：

- 当前浏览器 localStorage 中的 `storybox_user_id`
- 前端 Dashboard 中该 `user_id` 对应的 provider API Key 是否已保存
- `POST /api/v2/providers/test-connection` 是否成功

## 8.3 润色弹窗能开，但点击后失败

优先检查：

- `POST /api/v2/story/adjustments/polish` 的返回体
- provider 是否缺 key
- 默认模型是否可用

## 8.4 保存成功，但故事创作页还是旧文本

优先检查：

- `POST /api/v2/stories/{story_id}/adjustments/commit` 是否真的返回 200
- commit 响应里的 `story` 是否已经是新文本
- commit 响应里的 `warnings` 是否提示 history rebuild 失败

## 8.5 故事创作页显示新文本，但继续续写像是在用旧上下文

优先检查：

- commit 响应中的：
  - `rebuild_summary_reset`
  - `rebuild_history_reindexed`
  - `warnings`
- 后端日志中是否有 session rebuild 或 history reindex 错误

---

## 9. 本轮通过标准

如果以下 6 项全部满足，可视为本轮 smoke 通过：

1. Windows 下前后端可正常启动。
2. `/story-adjustment` 可进入，并共享当前故事工作区。
3. 单段选区润色成功，且先进入草稿层。
4. 撤销本地草稿成功。
5. 保存后 `StoryView` 立即显示新文本。
6. 保存后继续续写时，模型按新文本上下文推进。

---

## 10. 建议的下一轮扩展 smoke

若本轮通过，下一轮建议增加：

1. 多次连续润色同一段后再保存
2. 两个不同 segment 同时修改后再保存
3. 保存时 history rebuild 失败的降级提示验证
4. 刷新浏览器后再进入故事调整页继续编辑
5. 切换世界/切换故事时未保存提醒验证
