# Plan_2026-04-09_流式OpenAICompat风险与修复计划

## 1. 背景

在 `Plan0409_DualRoutePatch_Validation_Run.json` 的复跑结果中，流式故事生成链路出现了如下 warning：

1. `entity_patch async update failed`
2. `stream_options should be set along with stream = true`

这说明当前仓库在 `DeepSeek / OpenAI compat` 的流式参数构造与复用上，存在“流式客户端被复用于非流式调用”的风险点。虽然现有代码已经通过 fallback 保住了主流程，但这会带来：

1. 字段级 patch 缺失
2. world update 退化为 fallback rebuild
3. 前端 patch 时间线与真实流式体验不一致
4. 不同 provider 间兼容性表现不稳定

---

## 2. 已确认的风险

### 风险 A：流式 LLM 被复用于非流式 entity patch 抽取

#### 原因

流式故事正文路径使用 `for_streaming=True` 创建 LLM，此时 `openai_compat` 客户端会带上 `stream_options`。如果后续又把同一个 LLM 实例用于 `ainvoke()` 形式的结构化 patch 抽取，就可能向 provider 发送“不带 stream=true、却仍带 stream_options”的请求。

#### 可能影响

1. `entity_state_updates` 为空
2. `world_update.entity_patch.fallback_used = true`
3. 字段级 patch 无法落库到 `entity_state_events`
4. timeline 中看不到当前流式轮次的 patch 事件

#### 当前状态

1. 已修复
2. 修复方式：SSE 正文生成继续使用流式 LLM，`entity patch` 抽取改为单独使用非流式 LLM

### 风险 B：流式 LLM 被复用于输入增强

#### 原因

流式主链路在真正开始 `astream()` 之前，会先执行 `_enhance_user_input(...)`。该函数内部使用 `llm.ainvoke(...)`。如果这里复用的是 `for_streaming=True` 的 LLM，同样存在参数错配风险。

#### 可能影响

1. 输入增强 silently fail
2. 当前轮提示词增强失效
3. activation log 中增强结果不稳定
4. 不同 provider 上表现不一致

### 风险 C：流式 LLM 被复用于 Lorebook 长条目压缩

#### 原因

流式链路在进入正文生成前，还会调用 `lorebook_compressor.compress_contexts(...)`。该过程内部同样使用 `llm.ainvoke(...)`。如果复用流式 LLM，则会与风险 A/B 一样存在潜在参数错配。

#### 可能影响

1. 压缩失败并回退原文
2. prompt 变长，影响成本与上下文预算
3. 长 lorebook 条目命中的场景下更容易出现 provider 差异

### 风险 D：部分 OpenAI-compatible provider 可能不支持 `stream_options`

#### 原因

当前 `stream_openai_compat(...)` 默认总是发送：

1. `stream = true`
2. `stream_options = {"include_usage": true}`

虽然这对 OpenAI 兼容实现通常成立，但 `custom provider` 或某些兼容层可能不支持 `stream_options`，即使支持 streaming 本身，也可能因此直接报错。

#### 可能影响

1. SSE 正文流式直接失败
2. usage 统计缺失
3. 自定义 provider 的兼容性变差

---

## 3. 修复计划

### Phase 1：拆分流式正文 LLM 与流式前处理 LLM

#### 目标

把流式链路中所有 `ainvoke()` 型前处理与真正的 `astream()` 正文生成分离。

#### 改动点

1. `StoryGenerator.generate_story_stream(...)`

#### 实施方式

1. 新增 `preprocess_llm = _get_llm(..., for_streaming=False)`
2. 保留 `stream_llm = _get_llm(..., for_streaming=True)`
3. 使用 `preprocess_llm` 处理：
   - 输入增强
   - lorebook 压缩
   - entity patch 抽取
4. 使用 `stream_llm` 仅处理：
   - `astream(messages)`

#### 预期效果

1. 避免再次把流式参数带入非流式调用
2. 流式 patch 抽取恢复为主路径
3. 输入增强与压缩逻辑在 DeepSeek / OpenAI compat 下更稳定

### Phase 2：为 OpenAI compat 流式请求增加无 `stream_options` 回退

#### 目标

在 provider 不支持 `stream_options` 时，仍能保住 SSE 正文生成能力。

#### 改动点

1. `services/ai_proxy/streamers.py`

#### 实施方式

1. 第一次请求保持发送 `stream_options`
2. 如果返回的错误内容明确指向 `stream_options` 非法或不支持，则自动重试一次：
   - 保留 `stream = true`
   - 去掉 `stream_options`
3. 重试成功后继续正常流式输出

#### 预期效果

1. `custom provider` 的兼容性更高
2. `DeepSeek / Qwen / Gemini` 兼容层差异不会直接打断正文流式输出
3. usage 缺失时最多退化为“无精确 usage”，而不是整条流失败

---

## 4. 验收标准

1. 流式生成路径中：
   - 输入增强
   - lorebook 压缩
   - entity patch 抽取
   均不再复用 `for_streaming=True` 的 LLM
2. `stream_openai_compat(...)` 在 `stream_options` 被拒绝时，可自动重试无 `stream_options` 版本
3. 轻量静态校验通过
4. 现有非流式 generate / regenerate 行为不被破坏

---

## 5. 备注

本轮优先修复“已确认存在且会影响当前主链路稳定性”的风险，不扩大到新的协议抽象重构。后续若还要继续增强，可再考虑：

1. 为 provider registry 增加 `supports_stream_options` 能力位
2. 为 smoke 增加“流式 + 输入增强开启”“流式 + 长 lorebook 压缩”的专项回归项
