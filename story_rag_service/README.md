# Story RAG Service

一个基于 LangChain 和 RAG (Retrieval-Augmented Generation) 的交互式故事生成服务,类似于 AI Dungeon 或 Character AI 的酒馆模式。

## 执行计划

- 架构重构执行清单：`docs/ARCHITECTURE_REFACTOR_PLAN.md`
- SillyTavern 功能改进变更日志：`docs/SILLYTAVERN_FEATURE_CHANGELOG.md`
- API 兼容策略：`docs/API_COMPATIBILITY_POLICY.md`
- v1 退场计划：`docs/V1_DECOMMISSION_PLAN.md`

## Smoke 测试

```bash
# 基础 v2 接口验证
python scripts/smoke_v2_only.py

# P0 持久化+流式传输
python scripts/smoke_persistence_streaming.py

# P2 故事控制（Author's Note / 模式 / 重新生成）
python scripts/smoke_story_control.py

# SSE 终态契约验证（chunk + done + final text）
python scripts/smoke_story_stream_contract.py

# 摘要记忆功能（需在项目根目录运行）
python -c "import sys; sys.path.insert(0, '.'); exec(open('scripts/smoke_summary_memory.py').read())"
```

## 功能特性

### 核心功能
- 🌍 **多世界管理**: 创建和管理多个独立的故事世界（武侠、科幻、奇幻等）
- 🎭 **Lorebook (世界设定)管理**: 为每个世界创建角色、地点、事件等设定，SQLite + ChromaDB 双写持久化
- 🔍 **RAG 检索**: 智能检索相关设定，确保故事连贯性，世界间完全隔离
- ✍️ **故事生成**: 基于用户输入和检索的上下文生成连续故事
- 💾 **会话持久化**: SQLite + LRU 缓存双层保障，服务重启后会话自动恢复
- 📡 **SSE 流式推送**: Server-Sent Events 逐字符推送，极低首字延迟
- 🔄 **消息回滚与重新生成**: 一键撤销最后一轮或对同一输入重新生成答复
- 🧠 **LLM 摘要记忆**: 异步调用 LLM 压缩历史对话，突破 Token 上限
- 📝 **Author's Note (作者旁白)**: 任意时刻向系统提示注入叙事方向
- 🎮 **多模式生成**: narrative 叙事 / choices 分支选项 / instruction 强制推进
- 🗄️ **向量存储**: ChromaDB 高效存储和检索世界设定，支持语义相似度查询
- 🔌 **RESTful API**: 完整的 FastAPI 接口，Swagger 文档自动生成

### 世界设定类型
- **角色 (Character)**: 人物信息、性格、背景、关系等
- **地点 (Location)**: 地理位置、环境、特色等
- **事件 (Event)**: 历史事件、重要事件等
- **自定义**: 物品、派系、传说等

## 技术栈

- **LangChain**: LLM 框架和 RAG 实现
- **ChromaDB**: 向量数据库
- **FastAPI**: Web 框架
- **OpenAI/Anthropic/DeepSeek**: LLM 提供商
- **Pydantic**: 数据验证

## 快速开始

### 1. 安装依赖

```bash
cd story_rag_service
python -m venv myenv
myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```


### 数据库迁移（Alembic）

```bash
# 新库初始化到最新版本
python -m alembic -c alembic.ini upgrade head

# 现有库接入迁移基线（已存在表）
python -m alembic -c alembic.ini stamp head

# 查看当前版本
python -m alembic -c alembic.ini current
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写你的 API 密钥:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
OPENAI_API_KEY=sk-your-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-api-key-here  # 可选
DEEPSEEK_API_KEY=sk-your-deepseek-key-here  # 可选,推荐!

DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-3.5-turbo
# 或使用 DeepSeek (高性价比，中文优秀):
# DEFAULT_MODEL=deepseek-chat
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 访问 API 文档

打开浏览器访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 使用示例

> 当前服务以 **v2** 为唯一对外版本，示例均使用 `/api/v2/*`。

### 1. 生成故事（v2）

```bash
curl -X POST http://localhost:8000/api/v2/story/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "story-001",
    "user_input": "艾莉亚走进村庄的小酒馆,寻找关于黑雾的线索",
    "use_rag": true,
    "temperature": 0.8
  }'
```

### 2. 创建会话

```bash
curl -X POST http://localhost:8000/api/v2/story/session \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-001",
    "world_id": "fantasy-world"
  }'
```

### 3. SSE 流式生成

```bash
curl -N -X POST http://localhost:8000/api/v2/story/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-001",
    "user_input": "我推开酒馆的大门",
    "use_rag": true
  }'
# 服务器以 text/event-stream 推送：
# data: {"type":"chunk","content":"昏"}
# data: {"type":"chunk","content":"黄"}
# ...
# data: {"type":"done","session_id":"my-session-001","generated_text":"..."}
```

### 4. 使用 Author's Note 和模式切换

```bash
# narrative 模式（默认）+ Author's Note
curl -X POST http://localhost:8000/api/v2/story/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-001",
    "user_input": "我向老者询问",
    "authors_note": "保持神秘氛围，老者欲言又止",
    "mode": "narrative"
  }'

# choices 模式——AI 返回 3 个分支选项
curl -X POST http://localhost:8000/api/v2/story/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-001",
    "user_input": "我站在三条岔路前",
    "mode": "choices"
  }'

# instruction 模式——强制推进特定情节
curl -X POST http://localhost:8000/api/v2/story/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-001",
    "user_input": "继续",
    "mode": "instruction",
    "instruction": "进入战斗场景，引入神秘刺客"
  }'
```

### 5. 消息回滚与重新生成

```bash
# 撤销最后一轮对话（玩家输入 + AI 回复各一条）
curl -X DELETE http://localhost:8000/api/v2/story/session/my-session-001/messages/last

# 对同一个玩家输入重新生成 AI 回复
curl -X POST http://localhost:8000/api/v2/story/session/my-session-001/regenerate
```

### 6. 查询会话元数据

```bash
curl http://localhost:8000/api/v2/story/session/my-session-001
```

## 项目结构

```
story_rag_service/
├── main.py                      # FastAPI 应用入口
├── config.py                    # 配置管理
├── requirements.txt             # 依赖列表
├── test_story_persistence.py   # 故事持久化测试
├── .env.example                 # 环境变量示例
├── models/                      # 数据模型
│   ├── lorebook.py             # Lorebook 相关模型
│   ├── story.py                # 故事生成相关模型
│   ├── world.py                # 世界管理模型
│   └── stored_story.py         # 故事持久化模型
├── services/                    # 核心服务
│   ├── vector_store.py         # 向量数据库管理
│   ├── lorebook_manager.py     # 世界设定管理
│   ├── story_generator.py      # 故事生成引擎
│   ├── world_manager.py        # 世界管理服务
│   └── story_manager.py        # 故事持久化服务
├── api/                         # API 路由
│   ├── service_context.py      # 服务容器与依赖注入上下文
│   └── v2/                     # v2 路由定义
└── data/                        # 数据存储
    ├── chroma_db/              # ChromaDB 持久化目录
    ├── worlds.json             # 世界数据
    └── stories.json            # 故事数据
```

## 测试

### 运行故事持久化测试

```bash
python test_story_persistence.py
```

测试内容包括:
- ✅ 创建世界
- ✅ 创建故事
- ✅ 添加故事片段
- ✅ 获取故事列表
- ✅ 获取单个故事
- ✅ 更新故事标题
- ✅ 按世界过滤故事
- ✅ 删除故事

## 核心概念

### RAG 工作流程

1. **用户输入**: 用户提供行动或对话
2. **上下文检索**: 系统从 Lorebook 中检索相关的世界设定
3. **Prompt 构建**: 将检索到的设定和对话历史组合成完整的 Prompt
4. **故事生成**: LLM 基于完整上下文生成故事续写
5. **上下文更新**: 更新对话历史和世界状态

### Lorebook (世界设定书)

Lorebook 是故事的"记忆库",包含:
- 所有角色的详细信息
- 地点的描述和特色
- 重要事件的记录
- 其他世界设定

系统会自动检索与当前情境最相关的设定,确保故事的连贯性。

## 配置说明

### LLM 配置

在 `.env` 中配置:

```env
# 使用 OpenAI
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-3.5-turbo  # 或 gpt-4

# 使用 Anthropic Claude
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-opus-20240229

# 使用 DeepSeek (推荐用于中文故事生成)
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat
```

**推荐**: DeepSeek 在中文故事生成方面表现优秀且价格实惠，特别适合中文场景使用。详见 [DEEPSEEK_GUIDE.md](DEEPSEEK_GUIDE.md)

### 生成参数

```env
DEFAULT_TEMPERATURE=0.8      # 创造性 (0-2)
DEFAULT_MAX_TOKENS=2000      # 最大输出长度
```

### RAG 参数

```env
TOP_K_RESULTS=5              # 检索条目数量
SIMILARITY_THRESHOLD=0.7     # 相似度阈值
```

## 进阶使用

### 批量生成示例

```python
import requests

# 准备多轮输入
inputs = [
    {
        "session_id": "batch-story-001",
        "thread_id": "batch-thread-001",
        "user_input": "我走进森林"
    },
    # ... 更多请求
]

responses = []
for payload in inputs:
    response = requests.post(
        "http://localhost:8000/api/v2/story/generate",
        json=payload
    )
    responses.append(response.json())
```

### 持续对话

```python
import requests

session_id = "my-story-001"
thread_id = "my-thread-001"

# 第一轮
response1 = requests.post(
  "http://localhost:8000/api/v2/story/generate",
    json={
        "session_id": session_id,
    "thread_id": thread_id,
    "user_input": "我走进森林"
    }
).json()

# 第二轮 - 使用同一个 thread_id 继续会话
response2 = requests.post(
  "http://localhost:8000/api/v2/story/generate",
    json={
        "session_id": session_id,
    "thread_id": thread_id,
    "user_input": "我看到了什么?"
    }
).json()
```

## 与前端集成

可以在你的 Vue.js 前端中调用这个服务:

```typescript
// frontend/src/services/storyService.ts
export async function generateStory(input: string, sessionId: string) {
  const response = await fetch('http://localhost:8000/api/v2/story/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      thread_id: sessionId,
      user_input: input,
      use_rag: true
    })
  })
  return response.json()
}
```

## 性能优化建议

1. **使用本地 Embedding 模型**: 安装 `sentence-transformers` 避免 API 调用
2. **缓存机制**: 实现 LRU 缓存减少重复检索
3. **批量处理**: 使用批量 API 处理多个请求
4. **异步处理**: 使用 FastAPI 的异步特性

## 支持的 LLM 模型

| 模型 | 配置 | 优势 | 适用场景 |
|------|------|------|----------|
| **DeepSeek** | `deepseek-chat` | 高性价比，中文优秀 | 中文故事，日常使用 |
| **GPT-3.5** | `gpt-3.5-turbo` | 快速，平衡 | 快速生成，实时对话 |
| **GPT-4** | `gpt-4` | 质量最高 | 复杂故事，高质量需求 |
| **Claude** | `claude-3-opus` | 长文本处理 | 长篇故事，深度分析 |

## 常见问题

### Q: 推荐使用哪个模型?
A: 
- **中文故事**: 推荐 **DeepSeek** (性价比高，中文优秀)
- **英文故事**: GPT-3.5-Turbo 或 GPT-4
- **长篇故事**: Claude-3-Opus (支持更长上下文)
- **高质量**: GPT-4 (质量最好但成本较高)

### Q: 如何使用 DeepSeek?
A: 详见 [DEEPSEEK_GUIDE.md](DEEPSEEK_GUIDE.md)，简单来说:
1. 在 `.env` 添加 `DEEPSEEK_API_KEY`
2. 设置 `DEFAULT_MODEL=deepseek-chat`
3. 或在请求中指定 `"model": "deepseek-chat"`

### Q: 如何切换到本地 LLM?
A: 安装 `langchain-community` 并使用 `Ollama` 或其他本地 LLM:

```python
from langchain_community.llms import Ollama
llm = Ollama(model="llama2")
```

### Q: 如何保存和恢复会话?
A: `StoryContext` 对象可以序列化为 JSON,存储到数据库或文件中。

### Q: 如何提高生成质量?
A: 
- 丰富 Lorebook 内容
- 调整 `temperature` 参数
- 优化 System Prompt
- 使用更强大的模型 (GPT-4)

## 开发路线图

### 🎯 高优先级功能 (计划中)

#### 1. 角色一致性追踪系统
当前角色信息是静态的，需要添加动态追踪能力：

- **动态角色状态**
  - 追踪角色的情绪变化（开心→愤怒→平静）
  - 健康/体力/魔力等数值状态
  - 实时位置追踪
  
- **角色弧线管理**
  - 记录角色成长轨迹
  - 性格演变日志
  - 关键转折点标记
  
- **角色关系图谱**
  - 动态更新角色之间的关系变化
  - 好感度/敌意度数值化
  - 关系事件触发器

```python
# 示例数据结构
character_state = {
    "name": "艾莉亚",
    "emotion": "警惕",
    "health": 85,
    "location": "黑森林入口",
    "relationships": {
        "托马斯": {"type": "好友", "trust": 90, "history": ["共同冒险", "救命之恩"]}
    }
}
```

#### 2. 故事结构引擎
为故事提供结构化的叙事框架：

- **情节节拍（Beat）系统**
  - 开场（Hook）→ 铺垫（Setup）→ 冲突（Conflict）→ 高潮（Climax）→ 结局（Resolution）
  - 自动检测当前处于哪个阶段
  - 节拍转换提示
  
- **张力曲线追踪**
  - 实时分析故事张力值（0-100）
  - 张力过低时自动注入冲突元素
  - 张力过高时适当舒缓
  
- **分支剧情管理**
  - 关键决策点标记
  - 多结局路径追踪
  - "如果当时..."回溯功能

```python
# 示例：故事结构定义
story_structure = {
    "current_beat": "rising_action",
    "tension_level": 72,
    "decision_points": [
        {"turn": 15, "choice": "救人", "consequence": "获得盟友"},
        {"turn": 23, "choice": "揭露真相", "consequence": "触发BOSS战"}
    ],
    "available_endings": ["英雄结局", "悲剧结局", "隐藏结局"]
}
```

#### 3. 伏笔与回收系统
让故事更加精巧和有深度：

- **伏笔埋设标记**
  - 生成时自动识别潜在伏笔元素
  - 手动标记重要细节
  - 伏笔优先级分级（主线/支线/彩蛋）
  
- **智能回收提示**
  - 当上下文适合回收伏笔时主动提醒
  - 伏笔"保质期"管理（避免遗忘太久）
  - 回收时机评分
  
- **未解决悬念追踪**
  - 列出所有待解决的情节线
  - 悬念紧迫度排序
  - 自动生成"待回收"清单

```python
# 示例：伏笔追踪
foreshadowing_tracker = {
    "planted": [
        {
            "id": "fs_001",
            "content": "老者临终前提到的'北方的秘密'",
            "planted_at_turn": 5,
            "priority": "主线",
            "status": "未回收",
            "suggested_payoff_turns": [20, 25, 30]
        }
    ],
    "unresolved_mysteries": [
        "黑雾的来源",
        "失踪的王子下落",
        "神秘符文的含义"
    ]
}
```

### 🔧 中优先级功能

- [x] **风格模板系统**: 预设风格（黑色电影/武侠/恐怖/浪漫等）✅ 已完成
- [x] **场景氛围增强**: 自动补充天气、时间、五感描写 ✅ 已完成
- [x] **对话增强系统**: 角色语音特征、潜台词、对话节奏 ✅ 已完成
- [ ] **故事质量评估器**: AI 自动评分（连贯性/角色一致性/张力/原创性）

### 💡 创新功能

- [ ] **智能重写建议**: 检测重复用词，提供替代表达
- [ ] **多视角切换**: 从不同角色视角讲述同一事件
- [ ] **故事导出**: 导出为 Markdown/EPUB/PDF，生成故事摘要

### ✅ 已完成功能

- [x] 多世界管理
- [x] Lorebook 世界设定管理
- [x] RAG 智能检索
- [x] 故事生成与流式输出
- [x] 故事持久化
- [x] 长期记忆（对话历史 RAG）
- [x] 多 LLM 提供商支持（OpenAI/Anthropic/DeepSeek）
- [x] 用户 API Key 管理
- [x] 风格模板系统（10种预设风格：奇幻/武侠/黑色电影/恐怖/浪漫等）
- [x] 场景氛围增强（时间/天气/光线/五感描写）
- [x] 对话增强系统（角色语言风格/口音/口头禅/词汇水平/情感表达）
- [x] **会话管理**（SQLite 持久化 + LRU 缓存，支持跨重启恢复）
- [x] **SSE 流式生成**（Server-Sent Events 逐字符推送，首字延迟 < 200ms）
- [x] **消息回滚**（DELETE /session/{id}/messages/last 撤销最后一轮对话）
- [x] **重新生成**（POST /session/{id}/regenerate 对同一输入重新生成结果）
- [x] **Lorebook 双写持久化**（SQLite + ChromaDB 双轨写入，关机不丢设定数据）
- [x] **Lorebook 触发条件过滤**（enabled 开关 + 概率采样 + insertion_position 注入定位）
- [x] **LLM 摘要记忆**（asyncio.create_task 异步调用 LLM 压缩对话历史，降低 Token 消耗）
- [x] **作者旁白 (Author's Note)**（任意触发时注入到系统提示）
- [x] **多模式故事生成**（narrative / choices / instruction 三种模式切换）

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!
