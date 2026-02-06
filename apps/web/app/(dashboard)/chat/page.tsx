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
