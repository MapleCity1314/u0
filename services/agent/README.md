# Agent 模块

U0 平台的智能代理系统，提供模块化、可扩展的 AI Agent 架构。

## 架构概览

```
services/agent/
├── README.md                 # 本文档
├── __init__.py
├── config.py                 # 配置管理
├── module.py                 # FastAPI 模块注册
├── router.py                 # API 路由
│
├── core/                     # 核心引擎
│   ├── __init__.py
│   ├── agent.py              # Agent 基类与主引擎
│   ├── state.py              # 状态管理
│   ├── memory.py             # 记忆系统（短期/长期）
│   ├── planner.py            # 任务规划器
│   └── executor.py           # 执行器
│
├── mcp/                      # Model Context Protocol
│   ├── __init__.py
│   ├── protocol.py           # MCP 协议实现
│   ├── client.py             # MCP 客户端
│   ├── server.py             # MCP 服务端
│   └── transports/           # 传输层
│       ├── __init__.py
│       ├── stdio.py          # 标准 I/O 传输
│       ├── http.py           # HTTP/SSE 传输
│       └── websocket.py      # WebSocket 传输
│
├── skills/                   # 技能模块
│   ├── __init__.py
│   ├── base.py               # 技能基类
│   ├── registry.py           # 技能注册表
│   ├── portfolio/            # 持仓分析技能
│   │   ├── __init__.py
│   │   ├── analyzer.py       # 持仓分析器
│   │   └── reporter.py       # 报告生成
│   ├── research/             # 研究分析技能
│   │   ├── __init__.py
│   │   ├── fund_analyst.py   # 基金分析
│   │   └── market_analyst.py # 市场分析
│   └── web/                  # 网络搜索技能
│       ├── __init__.py
│       ├── searcher.py       # 搜索引擎
│       └── crawler.py        # 网页抓取
│
├── sub_agents/               # 子代理
│   ├── __init__.py
│   ├── base.py               # 子代理基类
│   ├── registry.py           # 子代理注册表
│   ├── researcher.py         # 研究员代理
│   ├── analyst.py            # 分析师代理
│   └── advisor.py            # 顾问代理
│
├── tools/                    # 工具集
│   ├── __init__.py
│   ├── base.py               # 工具基类
│   ├── registry.py           # 工具注册表
│   ├── system/               # 系统集成工具
│   │   ├── __init__.py
│   │   ├── position.py       # 持仓查询
│   │   ├── fund_nav.py       # 基金净值
│   │   ├── news.py           # 新闻获取
│   │   └── watchlist.py      # 自选股
│   ├── web/                  # 网络工具
│   │   ├── __init__.py
│   │   ├── search.py         # 搜索引擎集成
│   │   ├── fetch.py          # 网页获取
│   │   └── extract.py        # 内容提取
│   └── analysis/             # 分析工具
│       ├── __init__.py
│       ├── calculator.py     # 计算器
│       └── chart.py          # 图表生成
│
├── evals/                    # 评估系统（待实现）
│   ├── __init__.py
│   ├── metrics.py            # 评估指标
│   ├── benchmarks.py         # 基准测试
│   └── reports.py            # 评估报告
│
├── llm/                      # LLM 提供商抽象
│   ├── __init__.py
│   ├── base.py               # LLM 基类
│   ├── openai.py             # OpenAI 适配器
│   ├── anthropic.py          # Anthropic 适配器
│   └── ollama.py             # Ollama 本地模型
│
└── api/                      # API 接口
    ├── __init__.py
    ├── chat.py               # 对话接口
    ├── stream.py             # 流式响应
    └── schemas.py            # 数据模型
```

## 核心概念

### 1. MCP (Model Context Protocol)

MCP 是 Agent 与外部资源交互的标准协议，支持：
- **Resources**: 获取上下文资源（用户持仓、基金数据等）
- **Tools**: 调用工具执行操作
- **Prompts**: 动态提示模板
- **Sampling**: 请求 LLM 完成任务

### 2. Skills（技能）

技能是 Agent 的核心能力单元，每个技能封装一组相关功能：
- `PortfolioSkill`: 持仓分析、收益计算、风险评估
- `ResearchSkill`: 基金研究、市场分析、行业追踪
- `WebSkill`: 网络搜索、信息聚合、实时资讯

### 3. SubAgents（子代理）

专门化的子代理处理特定领域任务：
- `ResearcherAgent`: 信息收集与整理
- `AnalystAgent`: 数据分析与洞察
- `AdvisorAgent`: 投资建议生成

### 4. Tools（工具）

原子化的工具函数，可被 Agent 或技能调用：
- 系统工具：集成 U0 平台现有服务
- 网络工具：搜索、抓取、提取
- 分析工具：计算、可视化

### 5. Agent Evals（评估）[待实现]

评估系统用于衡量 Agent 性能：
- 响应质量评估
- 工具调用准确性
- 任务完成率

## 环境变量

```bash
# LLM 配置
AGENT_LLM_PROVIDER=openai          # openai / anthropic / ollama
AGENT_LLM_MODEL=gpt-4o-mini        # 模型名称
AGENT_LLM_TEMPERATURE=0.7          # 温度参数
AGENT_LLM_MAX_TOKENS=4096          # 最大 token 数

# API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# 搜索配置
AGENT_SEARCH_PROVIDER=tavily       # tavily / serper / bing
TAVILY_API_KEY=tvly-xxx
SERPER_API_KEY=xxx

# MCP 配置
AGENT_MCP_TRANSPORT=http           # stdio / http / websocket
AGENT_MCP_PORT=3001

# 内存配置
AGENT_MEMORY_TYPE=redis            # memory / redis / postgres
AGENT_MEMORY_TTL_SEC=3600
```

## API 接口

### POST /api/agent/chat
标准对话接口，返回完整响应。

```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "messages": [
      {"role": "user", "content": "分析我的持仓风险"}
    ]
  }'
```

### POST /api/agent/chat/stream
流式对话接口，返回 SSE 流。

```bash
curl -X POST http://localhost:8000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "messages": [
      {"role": "user", "content": "搜索最新的基金市场动态"}
    ]
  }'
```

### GET /api/agent/tools
获取可用工具列表。

### GET /api/agent/skills
获取可用技能列表。

## 快速开始

```python
from services.agent import Agent, AgentConfig

# 创建 Agent 实例
config = AgentConfig(
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    enable_web_search=True,
)

agent = Agent(config)

# 处理用户请求（带用户上下文）
response = await agent.chat(
    messages=[{"role": "user", "content": "查看我的持仓"}],
    user_id="xxx-xxx-xxx",
)

# 流式响应
async for chunk in agent.stream(
    messages=[{"role": "user", "content": "分析基金 000001"}],
    user_id="xxx-xxx-xxx",
):
    print(chunk)
```

## 与前端 AI SDK 集成

本模块设计兼容 Vercel AI SDK 的 `@ai-sdk/langchain` 适配器：

```typescript
// Next.js API Route
import { toUIMessageStream } from '@ai-sdk/langchain';
import { createUIMessageStreamResponse } from 'ai';

export async function POST(req: Request) {
  const { messages } = await req.json();
  
  // 调用 Python Agent 服务
  const response = await fetch('http://localhost:8000/api/agent/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });
  
  return new Response(response.body, {
    headers: { 'Content-Type': 'text/event-stream' },
  });
}
```

## 开发指南

### 添加新工具

```python
# tools/custom/my_tool.py
from services.agent.tools.base import Tool, tool

@tool(
    name="my_custom_tool",
    description="工具描述",
)
async def my_custom_tool(param1: str, param2: int = 10) -> str:
    """
    工具的详细说明。
    
    Args:
        param1: 参数1说明
        param2: 参数2说明，默认值为10
    
    Returns:
        返回值说明
    """
    # 实现逻辑
    return f"结果: {param1}, {param2}"
```

### 添加新技能

```python
# skills/custom/my_skill.py
from services.agent.skills.base import Skill

class MySkill(Skill):
    name = "my_skill"
    description = "技能描述"
    
    async def execute(self, context: dict) -> str:
        # 可以调用多个工具
        result1 = await self.use_tool("tool1", param="value")
        result2 = await self.use_tool("tool2", data=result1)
        return self.format_response(result2)
```

### 添加新子代理

```python
# sub_agents/custom_agent.py
from services.agent.sub_agents.base import SubAgent

class CustomAgent(SubAgent):
    name = "custom_agent"
    description = "自定义代理描述"
    skills = ["skill1", "skill2"]
    
    system_prompt = """
    你是一个专业的...
    """
    
    async def process(self, task: str, context: dict) -> str:
        # 子代理逻辑
        pass
```

## 依赖

```txt
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0
langgraph>=0.1.0
httpx>=0.27.0
tavily-python>=0.3.0
pydantic>=2.0.0
```

## 路线图

- [x] v0.1: 基础架构与核心引擎
- [x] v0.1: 系统工具集成（持仓、基金、新闻）
- [x] v0.1: 网络搜索能力
- [ ] v0.2: MCP 协议完整实现
- [ ] v0.2: 子代理协作机制
- [ ] v0.3: Agent Evals 评估系统
- [ ] v0.3: 长期记忆与学习