# Agent 系统集成与部署指南

本文档介绍如何将 U0 Agent 系统与前端 AI SDK 集成，以及完整的部署流程。

## 目录

- [架构概览](#架构概览)
- [前端集成](#前端集成)
- [后端部署](#后端部署)
- [MCP v0.2 状态](#mcp-v02-状态)
- [环境配置](#环境配置)
- [开发指南](#开发指南)
- [故障排查](#故障排查)

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                       Next.js Frontend                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  useChat Hook (AI SDK 6.x)                          │   │
│  │  - 流式对话界面                                      │   │
│  │  - 工具调用展示                                      │   │
│  │  - 消息持久化                                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓ HTTP/SSE                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  /api/chat/route.ts (API Route)                     │   │
│  │  - 认证转发                                          │   │
│  │  - 请求代理                                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Python Agent Service                      │
│                    (FastAPI on port 8000)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Agent API Router                                    │   │
│  │  POST /api/agent/chat/stream                        │   │
│  │  GET  /api/agent/tools                              │   │
│  │  GET  /api/agent/status                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Agent Core Engine                                   │   │
│  │  - LLM Provider (OpenAI/Anthropic/DeepSeek)        │   │
│  │  - Tool Registry (30+ tools)                        │   │
│  │  - State Management                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │ System Tools │  Web Tools   │   Skills     │ SubAgent │ │
│  │ - 持仓查询   │ - 网络搜索   │ - 持仓分析   │ - 研究员 │ │
│  │ - 基金净值   │ - 网页抓取   │ - 风险评估   │ - 分析师 │ │
│  │ - 新闻获取   │ - 内容提取   │ - 投资建议   │ - 顾问   │ │
│  └──────────────┴──────────────┴──────────────┴──────────┘ │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MCP Protocol v0.2 (Optional)                       │   │
│  │  - 标准化资源访问                                    │   │
│  │  - 工具定义和调用                                    │   │
│  │  - 与外部系统互操作                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      External Services                       │
│  - PostgreSQL (用户数据、持仓、新闻)                        │
│  - Redis (缓存、会话)                                        │
│  - AkShare / External APIs (市场数据)                        │
│  - Search Providers (Tavily/Serper/DuckDuckGo)             │
└─────────────────────────────────────────────────────────────┘
```

## 前端集成

### 1. 安装依赖

```bash
cd apps/web
pnpm add ai @ai-sdk/react
```

### 2. 配置环境变量

创建 `apps/web/.env.local`:

```bash
# Python Agent 服务地址
AGENT_API_URL=http://localhost:8000/api/agent/chat/stream

# 可选：直接使用 AI SDK (如果不通过 Python Agent)
OPENAI_API_KEY=sk-xxx
```

### 3. API Route 已创建

文件路径: `apps/web/app/(dashboard)/api/chat/route.ts`

这个 API Route 已经实现了：
- ✅ 用户认证转发
- ✅ 请求代理到 Python Agent
- ✅ 流式响应处理
- ✅ 错误处理

### 4. 创建聊天界面

创建 `apps/web/app/(dashboard)/chat/page.tsx`:

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { useState } from 'react';

export default function ChatPage() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status } = useChat({
    api: '/api/chat',
    onError: (error) => {
      console.error('Chat error:', error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    sendMessage({ text: input });
    setInput('');
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-orange-500 text-white'
                  : 'bg-zinc-100 dark:bg-zinc-800'
              }`}
            >
              {message.parts.map((part, i) => {
                switch (part.type) {
                  case 'text':
                    return (
                      <div key={i} className="whitespace-pre-wrap">
                        {part.text}
                      </div>
                    );
                  case 'tool-call':
                    return (
                      <div key={i} className="text-xs opacity-70 mt-2">
                        🔧 调用工具: {part.toolName}
                      </div>
                    );
                  default:
                    return null;
                }
              })}
            </div>
          </div>
        ))}
        
        {status === 'streaming' && (
          <div className="flex justify-start">
            <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg p-4">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="问我关于你的投资组合..."
          className="flex-1 px-4 py-2 border border-zinc-300 dark:border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
          disabled={status === 'streaming'}
        />
        <button
          type="submit"
          disabled={status === 'streaming' || !input.trim()}
          className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          发送
        </button>
      </form>
    </div>
  );
}
```

### 5. 添加路由

在 `apps/web/components/navigation.tsx` 中已经定义了导航项，确保添加聊天页面：

```typescript
const items = [
  { id: "dashboard", label: "仪表盘", icon: LayoutDashboard, href: "/" },
  { id: "chat", label: "AI助手", icon: MessageSquare, href: "/chat" }, // 新增
  { id: "search", label: "自选", icon: Search, href: "/search" },
  { id: "valuation", label: "估值", icon: Activity, href: "/valuation" },
  { id: "account", label: "账户", icon: CircleUser, href: "/profile" },
];
```

## 后端部署

### 1. 安装 Python 依赖

创建 `services/agent/requirements.txt`:

```txt
# AI SDK
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0
openai>=1.0.0
anthropic>=0.25.0

# HTTP
httpx>=0.27.0
sse-starlette>=2.0.0

# 搜索
tavily-python>=0.3.0
duckduckgo-search>=5.0.0

# 解析
beautifulsoup4>=4.12.0
lxml>=5.0.0

# FastAPI (如果主服务没有)
fastapi>=0.110.0
uvicorn>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

安装依赖:

```bash
cd services
pip install -r agent/requirements.txt
```

### 2. 环境变量配置

创建 `.env` 文件（或添加到现有的 `.env`）:

```bash
# ============================================================================
# Agent Configuration
# ============================================================================

# LLM Provider
AGENT_LLM_PROVIDER=openai          # openai / anthropic / deepseek / ollama
AGENT_LLM_MODEL=gpt-4o-mini        # 模型名称
AGENT_LLM_TEMPERATURE=0.7
AGENT_LLM_MAX_TOKENS=4096

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_BASE_URL=                   # 可选，用于代理

# Anthropic (可选)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# DeepSeek (可选)
DEEPSEEK_API_KEY=sk-xxxxx

# ============================================================================
# Search Configuration
# ============================================================================

AGENT_SEARCH_PROVIDER=duckduckgo   # tavily / serper / duckduckgo / bing
AGENT_SEARCH_MAX_RESULTS=10

# Tavily (推荐，需要付费)
TAVILY_API_KEY=tvly-xxxxx

# Serper (需要付费)
SERPER_API_KEY=xxxxx

# DuckDuckGo (免费，无需 API Key)
# 不需要额外配置

# ============================================================================
# Agent Features
# ============================================================================

AGENT_ENABLE_WEB_SEARCH=true
AGENT_ENABLE_TOOLS=true
AGENT_ENABLE_SUB_AGENTS=false      # v0.3
AGENT_ENABLE_MEMORY=false          # v0.3

AGENT_MAX_ITERATIONS=10
AGENT_MAX_TOOL_CALLS=20

# ============================================================================
# MCP Configuration (v0.2)
# ============================================================================

AGENT_MCP_ENABLED=false            # MCP 服务端（v0.3 完全实现）
AGENT_MCP_TRANSPORT=http
AGENT_MCP_PORT=3001

# ============================================================================
# Database (已存在的配置)
# ============================================================================

DATABASE_URL=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/u0

# ============================================================================
# Memory Configuration (v0.3)
# ============================================================================

AGENT_MEMORY_TYPE=memory           # memory / redis / postgres
AGENT_MEMORY_TTL_SEC=3600
```

### 3. 注册 Agent 路由

在 `services/server/app.py` 中添加 Agent 路由:

```python
from services.agent.api.router import setup_agent_routes

# 在创建 FastAPI app 后
setup_agent_routes(app)
```

完整示例:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 其他导入...
from services.agent.api.router import setup_agent_routes

app = FastAPI(
    title="U0 Platform API",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册现有模块路由
# ...

# 注册 Agent 路由
setup_agent_routes(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4. 启动服务

```bash
# 开发模式
python -m services.server.app

# 或使用 uvicorn
uvicorn services.server.app:app --reload --host 0.0.0.0 --port 8000
```

### 5. 验证部署

测试 Agent API:

```bash
# 检查状态
curl http://localhost:8000/api/agent/status

# 测试聊天 (需要认证 token)
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "查看我的持仓"}
    ],
    "stream": false
  }'

# 列出工具
curl http://localhost:8000/api/agent/tools
```

## MCP v0.2 状态

### 已完成 ✅

**MCP 协议核心实现** (`services/agent/mcp/protocol.py`):

- ✅ 完整的 JSON-RPC 2.0 消息格式
- ✅ MCPRequest / MCPResponse / MCPNotification
- ✅ MCPResource - 资源定义
- ✅ MCPTool - 工具定义
- ✅ MCPPrompt - 提示模板
- ✅ MCPSamplingRequest - 采样请求
- ✅ 错误处理 (MCPError, MCPErrorCode)
- ✅ 能力协商 (MCPServerCapabilities, MCPClientCapabilities)
- ✅ 初始化协议 (MCPInitializeParams, MCPInitializeResult)

### 进行中 🚧

**待实现组件** (计划 v0.3):

1. **MCPServer** (`services/agent/mcp/server.py`):
   - 服务端实现
   - 资源管理和订阅
   - 工具注册和执行
   - 提示模板管理
   - 请求路由

2. **MCPClient** (`services/agent/mcp/client.py`):
   - 客户端实现
   - 连接管理
   - 请求/响应处理
   - 流式通信

3. **ResourceProvider** (`services/agent/mcp/resources/`):
   - PositionResourceProvider - 持仓资源
   - FundResourceProvider - 基金资源
   - NewsResourceProvider - 新闻资源

4. **Transport Layer** (`services/agent/mcp/transports/`):
   - StdioTransport - 标准 I/O (Claude Desktop)
   - HttpTransport - HTTP/SSE
   - WebSocketTransport - WebSocket

### 使用 MCP 协议定义

虽然服务端/客户端尚未完成，但协议定义已经可以使用:

```python
from services.agent.mcp import (
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPResource,
    create_request,
    create_response,
)

# 创建工具定义
tool = MCPTool(
    name="get_positions",
    description="获取用户持仓",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "用户ID"}
        },
        "required": ["user_id"]
    }
)

# 创建请求
request = create_request(
    method="tools/call",
    params={
        "name": "get_positions",
        "arguments": {"user_id": "xxx"}
    }
)

# 创建响应
response = create_response(
    request_id=request.id,
    result={"positions": [...]}
)
```

## 环境配置

### 开发环境

```bash
# 1. 启动 PostgreSQL
docker run -d \
  --name u0-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=u0 \
  -p 5432:5432 \
  postgres:15

# 2. 启动 Python 服务
cd services
python -m server.app

# 3. 启动 Next.js
cd apps/web
pnpm dev
```

### 生产环境

使用 Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: u0
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - u0-network

  redis:
    image: redis:7-alpine
    networks:
      - u0-network

  python-api:
    build: ./services
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:${POSTGRES_PASSWORD}@postgres:5432/u0
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      TAVILY_API_KEY: ${TAVILY_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - u0-network

  nextjs:
    build: ./apps/web
    environment:
      AGENT_API_URL: http://python-api:8000/api/agent/chat/stream
    ports:
      - "3000:3000"
    depends_on:
      - python-api
    networks:
      - u0-network

volumes:
  postgres_data:

networks:
  u0-network:
```

## 开发指南

### 添加新工具

```python
# services/agent/tools/custom/my_tool.py
from services.agent.tools.base import tool, ToolCategory

@tool(
    name="my_custom_tool",
    description="工具描述",
    category=ToolCategory.SYSTEM,
    tags=["custom"],
)
async def my_custom_tool(ctx: ToolContext, param: str) -> str:
    """
    工具详细说明
    
    Args:
        ctx: 工具执行上下文
        param: 参数说明
        
    Returns:
        结果
    """
    # 实现逻辑
    return f"Result: {param}"
```

工具会自动注册到全局注册表。

### 添加新技能

```python
# services/agent/skills/custom/my_skill.py
from services.agent.skills.base import Skill, SkillContext

class MySkill(Skill):
    name = "my_skill"
    description = "技能描述"
    required_tools = ["tool1", "tool2"]
    
    async def execute(self, ctx: SkillContext, **kwargs) -> Any:
        # 调用工具
        result1 = await self.use_tool("tool1", param="value")
        result2 = await self.use_tool("tool2", data=result1)
        
        # 返回结果
        return {"result": result2}
```

### 测试 Agent

```python
import asyncio
from services.agent import Agent

async def test_agent():
    agent = Agent()
    
    response = await agent.chat(
        messages=[
            {"role": "user", "content": "查看我的持仓"}
        ],
        user_id="test-user-id",
    )
    
    print(response.content)
    print(f"Used {len(response.tool_calls)} tools")
    print(f"Duration: {response.duration_ms}ms")

asyncio.run(test_agent())
```

## 故障排查

### 问题 1: Agent API 返回 500 错误

**原因**: LLM API Key 未配置或无效

**解决**:
```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 测试 API Key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 问题 2: 工具调用失败

**原因**: 数据库连接失败或工具未正确导入

**解决**:
```python
# 检查工具注册
from services.agent.tools.registry import get_default_registry

registry = get_default_registry()
print(f"Registered tools: {registry.list_tool_names()}")

# 测试工具调用
from services.agent.tools.base import ToolContext

ctx = ToolContext(user_id="test-user")
result = await registry.call("get_positions", ctx)
print(result.to_dict())
```

### 问题 3: 前端无法连接到 Agent

**原因**: CORS 配置或 URL 不正确

**解决**:
```typescript
// 检查环境变量
console.log('AGENT_API_URL:', process.env.AGENT_API_URL);

// 测试连接
fetch('http://localhost:8000/api/agent/status')
  .then(r => r.json())
  .then(console.log);
```

### 问题 4: 流式响应中断

**原因**: 超时或连接断开

**解决**:
```python
# 增加超时时间
# services/agent/config.py
class AgentConfig(BaseSettings):
    llm: LLMConfig = Field(default_factory=lambda: LLMConfig(timeout=120))
```

```typescript
// 前端 API route
export const maxDuration = 120; // 增加到 120 秒
```

### 问题 5: MCP 功能不可用

**说明**: MCP v0.2 只实现了协议定义，服务端/客户端在 v0.3 实现

**当前状态**:
```python
from services.agent.mcp import get_implementation_status
print(get_implementation_status())
```

## 监控和日志

### 启用详细日志

```python
# 在启动脚本中添加
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 或者针对 Agent 模块
logging.getLogger('services.agent').setLevel(logging.DEBUG)
```

### 性能监控

```python
# 使用 Agent 的回调系统
agent = Agent()

agent.on_tool_start(lambda name, args: 
    print(f"Tool started: {name}")
)

agent.on_tool_end(lambda result: 
    print(f"Tool completed: {result.tool_name} in {result.duration_ms}ms")
)
```

## 下一步

- [ ] 完成 MCP Server/Client 实现 (v0.3)
- [ ] 实现资源提供者 (v0.3)
- [ ] 添加 Agent Evals 评估系统 (v0.3)
- [ ] 实现长期记忆系统 (v0.3)
- [ ] 添加更多预定义技能
- [ ] 优化工具调用性能
- [ ] 完善错误处理和重试机制

## 相关文档

- [Agent README](./README.md) - Agent 模块总览
- [MCP Module](.mcp/__init__.py) - MCP 协议文档
- [Tools Documentation](./tools/README.md) - 工具开发指南
- [Skills Documentation](./skills/README.md) - 技能开发指南

## 支持

遇到问题？查看以上故障排查部分，或参考代码中的注释和文档字符串。