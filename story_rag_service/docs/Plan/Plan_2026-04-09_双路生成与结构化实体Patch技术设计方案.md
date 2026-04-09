# Plan_2026-04-09_双路生成与结构化实体Patch技术设计方案

## 1. 背景与目标

当前仓库中的实体状态追踪能力，已经完成了第一阶段落地：

1. 已有 `entity_state_snapshot` 响应能力
2. 已有 `story_entity_states` 当前快照存储
3. 已有 `memory_update_journal` 可视化与审计链路
4. 已支持 `generate / stream / regenerate / rollback / rebuild` 后的实体状态重建

这些能力已经能够满足“实体状态可展示、可重建、可审计”的第一阶段要求，但从“逐实体、逐字段、逐回合地追踪世界事实变化”的角度看，当前方案仍然偏向“重建型快照系统”，尚未真正达到“事件驱动的结构化世界状态系统”。

结合当前项目目标与现有验证结果，本方案提出一套更贴近本仓库演进方向的第二阶段设计：

1. 保留现有正文故事生成链路
2. 在同一轮生成后增加第二路结构化输出链路
3. 让模型输出严格约束的 `entity_patch / world_update`
4. 用结构化 patch 驱动 `entity_state_events` 和 `entity_state_current`
5. 让回滚、重生成、时间线审计从“全文重建”逐步演进为“事件回放 + 快照物化”

本方案不是推翻现有实体状态系统，而是在当前 `StoryGenerator -> memory updates -> entity_state_snapshot -> dashboard/story page` 链路上增量升级。

### 1.1 本次方案要解决的问题

当前系统在功能上“可用”，但仍存在以下结构性问题：

1. 当前实体状态主要依赖规则抽取后全量重建，无法准确表达“这一轮到底改了什么”
2. 角色状态变化没有独立的字段级事件真相源
3. 回滚与重生成更多依赖重新扫描消息或 story segments，而不是对 patch 事件回放
4. 现有规则提取对多人同段、物品转移、状态归属等复杂叙事场景精度有限
5. 前端虽然能看到当前状态和近期事件，但难以稳定回答“为什么这个状态变成这样”

### 1.2 本次设计目标

本次设计希望在当前仓库内达成以下目标：

1. 将生成拆成两路：
   - 一路生成叙事正文
   - 一路生成结构化 `entity_patch / world_update`
2. 让结构化状态更新不再依赖纯规则重建，而是以“本轮 patch”为主要来源
3. 新增独立的 `entity_state_events` 事件流，作为字段级状态变化真相源
4. 保留并继续复用 `entity_state_current` 快速读取能力
5. 保持与现有 `summary_memory`、`story_state`、`runtime_state` 的职责边界清晰
6. 保持与现有 `memory_update_journal`、前端故事页、dashboard 页兼容
7. 保证 extractor 失败时不影响主文本生成

### 1.3 非目标

本方案首期不追求以下内容：

1. 不做完整知识图谱或多实体关系图数据库
2. 不做任意物件、组织、场景规则的全量结构化世界模拟
3. 不一次性替换全部现有 rebuild 逻辑
4. 不首期要求 provider 原生支持 tool calling / native structured output
5. 不要求把所有动态状态实时回写到 Lorebook 主数据

---

## 2. 现状基线与代码事实

以下结论均基于当前仓库实现，而不是假设。

### 2.1 当前生成主链路已经有统一 post-generation 挂点

- `story_rag_service/services/story_generator.py`
  - `generate_story(...)`
  - `generate_story_sync(...)`
  - `generate_story_stream(...)`
- 当前生成后已经统一执行：
  1. 原始消息持久化
  2. history index 更新
  3. summary 更新
  4. entity-state rebuild

其中，实体状态重建挂点位于 `_rebuild_entity_state_after_generation(...)`，说明本项目已经具备一个天然的“双路生成后处理入口”。

### 2.2 当前实体状态系统本质是“重建型快照”

- `story_rag_service/services/entity_state_manager.py`
  - `rebuild_story_state(...)`
  - `rebuild_session_state(...)`
  - `_consume_text(...)`

当前实现逻辑是：

1. 从 lorebook 角色与地点构建 lookup
2. 从 story segments 或 session messages 遍历文本
3. 按名字命中、关键词、正则模板提取地点/状态/物品/目标
4. 最终得到一组 `EntityStateSnapshot`
5. 以整故事维度覆盖写回当前快照

这说明当前方案是“扫描文本 -> 推导快照”，而不是“记录事件 -> 回放快照”。

### 2.3 当前只有 `entity_state_current`，还没有真正独立的 `entity_state_events`

- `story_rag_service/repositories/entity_state_repository.py`
  - 当前只有 `story_entity_states`
  - 存储粒度为 `(story_id, entity_id)` 对应的最新 JSON payload

当前实体事件虽然已经映射进 `memory_update_journal`，但那更偏向“审计与展示事件”，不是专门用于状态回放的字段级事件真相源。

### 2.4 当前 `memory_update_journal` 已具备 operation chain 基础设施

- `story_rag_service/services/database.py`
  - `memory_update_journal` 已包含：
    - `operation_id`
    - `sequence`
    - `memory_layer`
    - `before_payload`
    - `after_payload`
    - `status`

这意味着：

1. 第二路结构化 patch 可以与当前 generate/rollback/regenerate 共用同一 `operation_id`
2. 不需要另起一套完全独立的审计时间线
3. `memory_update_journal` 可以继续作为“用户可视时间线”，而 `entity_state_events` 作为“状态真相事件流”

### 2.5 当前响应契约已经为扩展结构化输出留有空间

- `story_rag_service/models/story.py`
  - `StoryGenerationResponse` 已有 `entity_state_snapshot`
- `story_rag_service/api/v2/schemas.py`
  - `V2GenerateResponse` 已有 `entity_state_snapshot`
- `story_rag_service/graph/story_v2/nodes.py`
  - `build_v2_response_node(...)` 统一负责组装最终 v2 响应

这意味着：如果新增 `entity_state_updates`、`world_update`、`entity_patch_result` 等字段，修改集中在响应模型和 graph 映射层即可，不需要重新设计整个 API 结构。

### 2.6 当前 LLM 工厂尚未统一封装结构化输出能力

- `story_rag_service/services/story_generation/llm_factory.py`
  - 当前主要创建 `ChatOpenAI` / `ChatAnthropic`
  - 尚未看到统一的 `with_structured_output(...)` 或 tool call 封装

这意味着：

1. 双路生成首期不宜强依赖 provider 原生结构化输出
2. 更稳妥的方案是“强约束 JSON prompt + 本地 schema 校验 + 失败降级”

### 2.7 当前系统已经存在多个状态层，需要明确边界

当前系统中的四类状态分别是：

1. `summary_memory`
2. `story_state`
3. `runtime_state`
4. `entity_state`

其中：

- `story_state` 适合剧情抽象状态
- `runtime_state` 适合严格剧本运行态
- `entity_state` 才适合逐人物动态事实层

因此，双路生成中的 `world_update` 不应无边界扩张，否则会与 `story_state` / `runtime_state` 冲突。

---

## 3. 现有方案的工作方式与局限

### 3.1 现有方案的工作方式

当前实体状态链路可以概括为：

1. 正文生成完成
2. 先更新 `episodic` 与 `summary`
3. 再对当前 session messages 执行一次 `rebuild_session_state(...)`
4. 通过规则提取生成新的 `entity_state_snapshot`
5. 覆盖写回 `story_entity_states`
6. 生成 `memory_layer = entity_state` 的 journal 事件
7. 将 `entity_state_snapshot` 返回给前端

### 3.2 现有方案的优点

当前方案并不是错误设计，它有以下优点：

1. 工程实现简单，接入成本低
2. 不依赖额外 LLM 抽取调用，性能成本低
3. 可完全复现，重建逻辑可预测
4. rollback / rebuild 路径容易实现
5. 已与现有 dashboard / memory timeline / story page 对接完成

### 3.3 现有方案的核心局限

但它的上限也很明确：

1. 它产出的是“当前快照”，不是“本轮 patch”
2. 它很难准确表达“张三把铜钥匙给了李四”这类字段级转移
3. 多角色同段文本时，状态和物品归因容易串位
4. 证据主要是片段截断，不是严格结构化证据
5. 回滚更多依赖全文重建，而不是按事件流回放
6. 当叙事复杂到多人、多地点、多轮物品转移时，规则提取精度会明显下降

### 3.4 为什么需要升级为双路生成

因为用户真正需要的并不只是“最后的当前状态”，而是：

1. 本轮到底谁变了
2. 哪个字段变了
3. 为什么变
4. 根据哪段证据变
5. 回滚时该撤销哪次变化

这类问题天然更适合由结构化 patch 来回答，而不适合由全文重建快照来间接推导。

---

## 4. 目标方案总览：双路生成

### 4.1 核心思想

将当前一次故事生成拆为两条职责明确的输出链：

#### 4.1.1 叙事正文链

职责：

1. 输出用户可阅读的故事正文
2. 保持现有流式/非流式生成体验
3. 继续复用现有 RAG、prompt builder、summary、runtime 等能力

#### 4.1.2 结构化 patch 链

职责：

1. 输出本轮结构化世界变化
2. 重点覆盖人物实体的：
   - 所在地点
   - 携带物增减
   - 状态标签增减
   - 同行关系变化
   - 短期目标变化
3. 形成事件流并驱动当前快照物化

### 4.2 推荐的首期实现形式

首期建议采用：

1. 主文本生成完成后
2. 使用第二次 LLM 调用执行结构化 patch 抽取
3. 输出严格 JSON 的 `entity_patch`
4. 经本地 validator 校验后再写入状态系统

不建议首期直接做：

1. 单次调用同时输出正文与 JSON
2. 强依赖 provider 原生 tool calling
3. 让 `world_update` 覆盖 `story_state / runtime_state`

原因是：

1. 当前流式链路已经稳定，单次双输出会显著增加兼容风险
2. 当前 provider 层尚未统一结构化输出能力
3. 当前最迫切的问题是实体状态 patch，而不是所有世界状态统一收口

---

## 5. 目标架构设计

### 5.1 设计原则

#### 5.1.1 正文优先原则

结构化抽取失败时，绝不能影响主文本生成成功。

#### 5.1.2 patch 优先原则

当前状态应优先由“本轮 patch 应用”得到，而不是每轮全文重建。

#### 5.1.3 快照物化原则

仍然保留 `entity_state_current` 快速读取能力，避免前端每次都回放事件流。

#### 5.1.4 repair fallback 原则

现有 `rebuild_session_state(...)` / `rebuild_story_state(...)` 不删除，转为 fallback 修复路径。

#### 5.1.5 边界清晰原则

首期 `entity_patch` 只处理角色级动态事实，不承担剧情推进职责。

### 5.2 新增的核心组件

建议新增以下组件：

1. `EntityPatchExtractor`
2. `EntityPatchValidator`
3. `EntityPatchApplier`
4. `EntityStateEventRepository`
5. `EntityStateProjectionService`

### 5.3 组件职责说明

#### 5.3.1 `EntityPatchExtractor`

职责：

1. 基于本轮 `user_input + generated_text + 当前实体快照 + lorebook 边界` 生成结构化 patch
2. 输出严格 JSON schema
3. 不直接写数据库

#### 5.3.2 `EntityPatchValidator`

职责：

1. 校验 patch 的字段合法性
2. 校验引用是否合法：
   - entity_id
   - location / companion / inventory item 的格式边界
3. 过滤非法 patch
4. 为 patch 打上降级状态或 warning

#### 5.3.3 `EntityPatchApplier`

职责：

1. 将 patch 应用到当前快照
2. 生成新的 `entity_state_current`
3. 输出可持久化的 before/after 视图

#### 5.3.4 `EntityStateEventRepository`

职责：

1. 存储字段级 patch 事件
2. 支持按 story/session/entity/turn 查询
3. 支持按 operation_id 回查同轮 patch

#### 5.3.5 `EntityStateProjectionService`

职责：

1. 把事件流投影成当前快照
2. 在 rollback / rebuild 时负责重放
3. 与现有 `EntityStateRepository` 协作

---

## 6. 数据模型设计

### 6.1 保留现有 `entity_state_current`

继续保留当前的 `story_entity_states` 表，作为物化后的“当前事实视图”。

原因：

1. 现有接口和前端已依赖它
2. 当前读取性能简单稳定
3. 可避免前端直接面对事件回放复杂度

### 6.2 新增 `entity_state_events`

建议新增表：

`entity_state_events`

建议字段：

1. `event_id`
2. `story_id`
3. `session_id`
4. `entity_id`
5. `entity_type`
6. `field_name`
7. `op`
8. `value_payload`
9. `before_payload`
10. `after_payload`
11. `evidence_text`
12. `source_turn`
13. `source`
14. `operation_id`
15. `sequence`
16. `confidence`
17. `status`
18. `committed_at`

### 6.3 `op` 设计建议

首期建议只支持少量高价值操作：

1. `set`
2. `add`
3. `remove`
4. `clear`
5. `reset`

### 6.4 首期建议支持的字段

建议只覆盖以下角色级字段：

1. `current_location`
2. `inventory`
3. `status_tags`
4. `companions`
5. `short_goal`
6. `state_summary`

### 6.5 `entity_patch` JSON schema 建议

建议 LLM 输出结构如下：

```json
{
  "patches": [
    {
      "entity_id": "character-entry-id",
      "entity_name": "张三",
      "field": "current_location",
      "op": "set",
      "value": "地下仓库",
      "confidence": 0.93,
      "evidence": "张三和李四赶到地下仓库。",
      "source_turn": 2
    },
    {
      "entity_id": "character-entry-id",
      "entity_name": "张三",
      "field": "inventory",
      "op": "remove",
      "value": "铜钥匙",
      "confidence": 0.95,
      "evidence": "张三将手中的铜钥匙扔向角落的阴影里。",
      "source_turn": 2
    }
  ],
  "warnings": []
}
```

### 6.6 为什么首期不把 `world_update` 做得过大

因为如果首期把 `world_update` 扩大到包括：

1. stage 推进
2. 事件完成
3. 线索抽象状态
4. 世界规则变化

就会和以下现有系统产生边界冲突：

1. `story_state`
2. `runtime_state`
3. story progress metadata

因此首期建议：

1. 对外文档继续保留“world_update”概念
2. 实际实现聚焦“角色实体 patch”
3. 等角色 patch 稳定后，再扩展到更宽的 world state

---

## 7. 详细执行链路设计

### 7.1 非流式 generate

目标链路：

1. 接收 `V2GenerateRequest`
2. `generation_routes.py` 为本轮创建 `memory_operation_id`
3. `story_v2` graph 将请求映射为 `StoryGenerationRequest`
4. `StoryGenerator.generate_story(...)` 生成正文
5. 运行现有 `MemoryUpdateService.run_post_generation_updates(...)`
6. 调用 `EntityPatchExtractor`
7. 调用 `EntityPatchValidator`
8. 调用 `EntityPatchApplier`
9. 写入：
   - `entity_state_events`
   - `story_entity_states`
   - `memory_update_journal`
10. 返回：
   - `generated_text`
   - `entity_state_snapshot`
   - `entity_state_updates`
   - 可选 `world_update`

### 7.2 流式 generate

流式路径建议策略：

1. 保持正文 chunk 流式输出不变
2. 在 done 事件前或 done 事件构造阶段执行结构化 patch 抽取
3. 只在最终 done payload 中附加：
   - `entity_state_snapshot`
   - `entity_state_updates`
   - `world_update`

原因：

1. patch 依赖完整正文
2. 不应把结构化状态抽取塞进增量 chunk 流程
3. 这样可以最大化复用现有 SSE done payload 模式

### 7.3 regenerate

`regenerate` 路径已经具备显式 `operation_id` 链路。

在双路生成方案下，应保持：

1. 回滚前置 reconcile 保持不变
2. 新正文生成后走同一套 `EntityPatchExtractor`
3. patch 事件继续挂在本轮 `regenerate:*` operation chain 下

### 7.4 rollback / rebuild

建议分成两层：

#### 7.4.1 主路径：事件回放

1. 按 `source_turn` 或 `operation_id` 裁剪 `entity_state_events`
2. 从起点回放到目标 turn
3. 重建 `story_entity_states`

#### 7.4.2 修复路径：全文重建

1. 保留现有 `rebuild_session_state(...)`
2. 保留现有 `rebuild_story_state(...)`
3. 当事件流损坏、旧数据缺失、patch 校验失败过多时可回退到 repair 模式

---

## 8. 与现有方案的对比优势

### 8.1 对比维度一：状态更新方式

#### 现有方案

1. 正文生成后全文扫描
2. 规则提取
3. 得到新快照

#### 新方案

1. 正文生成后输出本轮结构化 patch
2. patch 落为事件流
3. 事件投影成新快照

#### 新方案优势

1. 更容易回答“这一轮改变了什么”
2. 更容易审计“为什么改”
3. 更适合回滚与回放

### 8.2 对比维度二：归因精度

#### 现有方案

1. 依赖名字共现
2. 依赖关键词和正则
3. 多人同段场景容易串位

#### 新方案

1. 由模型直接按实体输出 patch
2. 每个字段变化自带 evidence
3. 可引入 confidence 与 validator

#### 新方案优势

1. 更适合处理“张三把钥匙给李四”
2. 更适合处理“只有张三受伤，李四只是紧张”
3. 更容易做字段级降级而不是整轮全失败

### 8.3 对比维度三：回滚与重建

#### 现有方案

1. 更多依赖消息/segments 重扫
2. 本质是“重推导”

#### 新方案

1. 首选事件回放
2. 全文重建作为 repair fallback

#### 新方案优势

1. 回滚语义更清晰
2. 更容易做 turn 级或 operation 级回放
3. 更利于后续做前端“状态时间旅行”

### 8.4 对比维度四：解释性与可视化

#### 现有方案

1. 主要看到当前状态
2. journal 事件偏粗粒度

#### 新方案

1. 可以展示字段级 patch
2. 可以展示“set/add/remove”的具体变化
3. 可以附带 evidence 和 confidence

#### 新方案优势

1. dashboard 可读性更强
2. 调试与审计效率更高
3. 用户更容易理解状态变化原因

### 8.5 对比维度五：扩展性

#### 现有方案

1. 规则越加越复杂
2. 复杂叙事下维护成本不断上升

#### 新方案

1. patch schema 可以逐步扩展
2. validator 和 applier 可以独立演进
3. 可单独配置更便宜的 extractor 模型

#### 新方案优势

1. 更适合后续演进到多实体、多状态层
2. 可扩展到物件状态、场景状态、阵营关系等
3. 不会把所有复杂度都堆进一份规则重建代码

---

## 9. 预期效果

如果该方案按推荐方式落地，预期会带来以下效果：

### 9.1 对用户体验的效果

1. 故事页能更稳定地展示“谁变了、怎么变的”
2. 当前实体状态与最近变更更容易理解
3. rollback / regenerate 后的状态一致性更强

### 9.2 对产品能力的效果

1. 实体状态系统从“快照型”升级为“事件驱动型”
2. 前端能够支持更细粒度的 entity timeline
3. 后续可支持“按角色查看状态演化史”

### 9.3 对工程可维护性的效果

1. 把“正文生成”和“状态理解”职责解耦
2. 避免将越来越复杂的规则继续塞进 `EntityStateManager`
3. 为未来引入轻量结构化模型留出明确位置

### 9.4 对一致性与审计的效果

1. 同一轮操作可以把 `episodic / semantic / entity_patch` 串进同一 `operation_id`
2. 更容易排查“这一轮状态为什么错了”
3. 更容易做自动 smoke 与字段级断言

---

## 10. 详细模块改造建议

### 10.1 后端新增模块建议

建议新增目录与模块：

1. `story_rag_service/services/story_generation/entity_patch_extractor.py`
2. `story_rag_service/services/story_generation/entity_patch_validator.py`
3. `story_rag_service/services/story_generation/entity_patch_applier.py`
4. `story_rag_service/repositories/entity_state_event_repository.py`

### 10.2 后端修改模块建议

建议重点修改：

1. `story_rag_service/services/story_generator.py`
   - 增加第二路 patch 抽取编排
2. `story_rag_service/models/story.py`
   - 增加新响应字段
3. `story_rag_service/api/v2/schemas.py`
   - 增加 v2 返回 schema
4. `story_rag_service/graph/story_v2/nodes.py`
   - 透传新的结构化输出字段
5. `story_rag_service/services/database.py`
   - 初始化 `entity_state_events`
6. `story_rag_service/services/entity_state_manager.py`
   - 从主路径降级为 repair / rebuild fallback

### 10.3 前端修改建议

前端首期不需要大改交互，只需要逐步增加读取和展示能力：

1. 继续消费 `entity_state_snapshot`
2. 新增可选 `entity_state_updates`
3. dashboard 中新增字段级 patch 视图
4. 逐步支持按角色查看最近 patch timeline

---

## 11. 风险与应对

### 11.1 额外一次模型调用带来的延迟

风险：

1. 每轮生成时间增加
2. 成本上升

应对：

1. 只在检测到实体命中时触发 extractor
2. 可配置专用 extractor provider/model
3. 后续可并行优化

### 11.2 provider 结构化输出不稳定

风险：

1. 非法 JSON
2. 字段名漂移
3. 值域不合法

应对：

1. 首期采用强约束 prompt
2. 本地 pydantic/schema 校验
3. 失败时整轮降级为“无 patch，不影响正文”

### 11.3 `world_update` 与现有状态层边界冲突

风险：

1. 与 `story_state` 重叠
2. 与 `runtime_state` 重叠

应对：

1. 首期只实现角色级 `entity_patch`
2. `world_update` 仅保留概念和兼容字段
3. 待角色 patch 稳定后再扩展

### 11.4 旧数据与新事件模型并存

风险：

1. 迁移期双真相源并存
2. rollback 逻辑复杂

应对：

1. 明确：
   - `entity_state_events` 是事件真相源
   - `story_entity_states` 是投影快照
2. rebuild 继续保留为 repair fallback

---

## 12. 实施阶段建议

### 12.1 Phase A：契约与事件层

目标：

1. 定义 `entity_patch` schema
2. 落地 `entity_state_events`
3. 保持现有 generate 不受影响

### 12.2 Phase B：双路生成首期接入

目标：

1. 在非流式 generate 中接入第二路 extractor
2. 返回 `entity_state_updates`
3. patch 成功时优先以 patch 物化当前快照

### 12.3 Phase C：stream / regenerate / rollback 对齐

目标：

1. 流式 done payload 支持 patch 结果
2. regenerate 支持 patch operation chain
3. rollback 优先走事件回放

### 12.4 Phase D：前端时间线增强

目标：

1. story 页展示字段级 patch
2. dashboard 支持按角色查看 patch timeline
3. 增加 confidence / warning 展示

---

## 13. 推荐结论

结合当前仓库现状，我建议：

1. 将“双路生成”作为实体状态系统的下一阶段正式方向
2. 首期聚焦 `entity_patch`，不要让 `world_update` 范围失控
3. 保留现有 `entity_state_manager` 作为 fallback 修复路径
4. 让 `entity_state_events` 成为新真相源，`story_entity_states` 继续作为当前快照投影
5. 继续复用当前 `StoryGenerator`、`story_v2 graph`、`memory_update_journal`、前端 story/dashboard 视图

简而言之：

**现有方案适合“快速补齐实体状态能力”，新方案更适合把实体状态系统真正升级为“可追踪、可回放、可解释、可扩展的结构化世界状态系统”。**

从当前项目演进角度看，双路生成不是过度设计，而是对现有方案最自然、最有价值的下一步升级。
