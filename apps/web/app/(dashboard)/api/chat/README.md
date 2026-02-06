# AI Chat API - AI SDK 集成

本 API 路由将 Python Agent 后端的 SSE 流式响应转换为 Vercel AI SDK 的 `UIMessageStream` 格式，使前端可以直接使用 `@ai-sdk/react` 的 `useChat` Hook。

## 架构

```
┌─────────────┐     UIMessage      ┌──────────────┐     AgentMessage    ┌─────────────────┐
│   Frontend  │ ──────────────────▶│  Next.js API │ ──────────────────▶│  Python Agent   │
│  (useChat)  │                    │   (route.ts) │                    │   (FastAPI)     │
└─────────────┘                    └──────────────┘                    └─────────────────┘
       ▲                                  │                                   │
       │      UIMessageStream             │         SSE Stream                │
       └──────────────────────────────────┴◀──────────────────────────────────┘
```

## 消息格式转换

### 请求转换 (Frontend → Backend)

AI SDK 的 `UIMessage` 格式:
```typescript
interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  parts: MessagePart[];
  // ...
}
```

转换为 Python Agent 格式:
```typescript
interface AgentMessage {
  role: string;
  content: string;
  name?: string;
  tool_call_id?: string;
}
```

### 响应转换 (Backend → Frontend)

Python Agent SSE 块类型:
- `text` - 文本增量
- `tool_call` - 工具调用开始
- `tool_result` - 工具执行结果
- `error` - 错误
- `done` - 完成

转换为 AI SDK `UIMessageChunk` 类型:
- `text-start` / `text-delta` / `text-end` - 文本流
- `tool-input-available` - 工具调用
- `tool-output-available` / `tool-output-error` - 工具结果
- `error` - 错误
- `finish` - 完成

## 前端使用示例

```tsx
'use client';

import { useChat } from '@ai-sdk/react';

export default function ChatPage() {
  const { messages, sendMessage, status, error } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="flex flex-col h-full">
      {/* 消息列表 */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.role === 'user' ? 'text-right' : 'text-left'}
          >
            {message.parts.map((part, index) => {
              if (part.type === 'text') {
                return <p key={index}>{part.text}</p>;
              }
              if (part.type === 'tool-invocation') {
                return (
                  <div key={index} className="text-sm text-muted-foreground">
                    工具调用: {part.toolInvocation.toolName}
                  </div>
                );
              }
              return null;
            })}
          </div>
        ))}
      </div>

      {/* 输入框 */}
      <form
        className="p-4 border-t"
        onSubmit={(e) => {
          e.preventDefault();
          const input = e.currentTarget.elements.namedItem('message') as HTMLInputElement;
          if (input.value.trim()) {
            sendMessage({ text: input.value });
            input.value = '';
          }
        }}
      >
        <div className="flex gap-2">
          <input
            name="message"
            className="flex-1 px-4 py-2 border rounded-lg"
            placeholder="输入消息..."
            disabled={status === 'streaming'}
          />
          <button
            type="submit"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg"
            disabled={status === 'streaming'}
          >
            {status === 'streaming' ? '发送中...' : '发送'}
          </button>
        </div>
        {error && (
          <p className="mt-2 text-sm text-destructive">{error.message}</p>
        )}
      </form>
    </div>
  );
}
```

## 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `AGENT_API_URL` | Python Agent 服务地址 | `http://localhost:8000/api/agent/chat/stream` |

## 后端 SSE 格式参考

Python Agent 返回的 SSE 格式:

```
data: {"type": "text", "content": "你好"}

data: {"type": "tool_call", "tool_call": {"id": "call_123", "name": "search", "arguments": {"query": "test"}}}

data: {"type": "tool_result", "tool_call": {"id": "call_123", "name": "search", "result": "{\"results\": []}"}}

data: {"type": "done", "metadata": {"session_id": "xxx"}}
```

## 扩展

### 添加自定义数据

如果需要在流中发送自定义数据（如进度更新），可以在 Python Agent 中添加新的 chunk 类型，然后在 `route.ts` 中处理:

```typescript
// 在 processAgentStream 函数中添加
case "progress":
    writer.write({
        type: "data-progress",
        id: `progress-${Date.now()}`,
        data: chunk.metadata,
    });
    break;
```

### 处理文件上传

AI SDK 支持文件上传，可以扩展 `convertUIMessageToAgentMessage` 函数来处理 `FileUIPart`:

```typescript
function convertUIMessageToAgentMessage(message: UIMessage) {
  let content = "";
  const files: string[] = [];

  for (const part of message.parts) {
    if (part.type === "text") {
      content += part.text;
    } else if (part.type === "file") {
      files.push(part.url);
    }
  }

  return {
    role: message.role,
    content,
    files: files.length > 0 ? files : undefined,
  };
}
```

## 相关链接

- [Vercel AI SDK 文档](https://sdk.vercel.ai/docs)
- [AI SDK useChat Hook](https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot)
- [Python Agent API 文档](../../../services/agent/README.md)