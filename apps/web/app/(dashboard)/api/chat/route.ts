/**
 * AI Chat API Route
 *
 * 连接到 Python Agent 服务，将其 SSE 响应转换为 AI SDK UIMessageStream 格式
 */

import {
    createUIMessageStream,
    createUIMessageStreamResponse,
    UIMessage,
    UIMessageStreamWriter,
} from "ai";
import { NextRequest } from "next/server";

// Python Agent 服务地址
const AGENT_API_URL =
    process.env.AGENT_API_URL || "http://localhost:8000/api/agent/chat/stream";

export const runtime = "edge";
export const maxDuration = 60;

/**
 * Python Agent 后端的流式响应块类型
 */
interface AgentStreamChunk {
    type: "text" | "tool_call" | "tool_result" | "error" | "done";
    content?: string;
    tool_call?: {
        id: string;
        name: string;
        arguments: Record<string, unknown>;
        result?: string;
        error?: string;
        duration_ms?: number;
    };
    metadata?: Record<string, unknown>;
}

/**
 * 将 AI SDK UIMessage 转换为 Python Agent 消息格式
 */
function convertUIMessageToAgentMessage(message: UIMessage): {
    role: string;
    content: string;
    name?: string;
    tool_call_id?: string;
} {
    // 从 parts 中提取文本内容
    let content = "";
    for (const part of message.parts) {
        if (part.type === "text") {
            content += part.text;
        }
    }

    return {
        role: message.role,
        content,
    };
}

/**
 * 解析 SSE 事件数据
 */
function parseSSEEvent(eventText: string): AgentStreamChunk | null {
    const lines = eventText.split("\n");
    for (const line of lines) {
        if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") {
                return { type: "done" };
            }
            try {
                return JSON.parse(data) as AgentStreamChunk;
            } catch {
                console.error("Failed to parse SSE data:", data);
                return null;
            }
        }
    }
    return null;
}

/**
 * 处理 Python Agent 的流式响应并转换为 AI SDK 格式
 */
async function processAgentStream(
    response: Response,
    writer: UIMessageStreamWriter,
): Promise<void> {
    const reader = response.body?.getReader();
    if (!reader) {
        throw new Error("Response body is not readable");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let textPartId: string | null = null;

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 处理 SSE 事件（以双换行符分隔）
            const events = buffer.split("\n\n");
            buffer = events.pop() || ""; // 保留未完成的部分

            for (const eventText of events) {
                if (!eventText.trim()) continue;

                const chunk = parseSSEEvent(eventText);
                if (!chunk) continue;

                switch (chunk.type) {
                    case "text":
                        // 文本增量 - 使用 text-delta 格式
                        if (chunk.content) {
                            // 如果还没有开始文本部分，先发送 text-start
                            if (!textPartId) {
                                textPartId = `text-${Date.now()}`;
                                writer.write({
                                    type: "text-start",
                                    id: textPartId,
                                });
                            }
                            writer.write({
                                type: "text-delta",
                                id: textPartId,
                                delta: chunk.content,
                            });
                        }
                        break;

                    case "tool_call":
                        // 工具调用开始
                        if (chunk.tool_call) {
                            const {
                                id,
                                name,
                                arguments: args,
                            } = chunk.tool_call;

                            // 结束之前的文本部分
                            if (textPartId) {
                                writer.write({
                                    type: "text-end",
                                    id: textPartId,
                                });
                                textPartId = null;
                            }

                            // 写入工具调用（使用 tool-input-available）
                            writer.write({
                                type: "tool-input-available",
                                toolCallId: id,
                                toolName: name,
                                input: args,
                            });
                        }
                        break;

                    case "tool_result":
                        // 工具执行结果
                        if (chunk.tool_call) {
                            const { id, result, error } = chunk.tool_call;

                            if (error) {
                                // 工具执行出错
                                writer.write({
                                    type: "tool-output-error",
                                    toolCallId: id,
                                    errorText: error,
                                });
                            } else {
                                // 工具执行成功
                                let output: unknown = result;
                                // 尝试解析 JSON 结果
                                if (result) {
                                    try {
                                        output = JSON.parse(result);
                                    } catch {
                                        // 保持原始字符串
                                        output = result;
                                    }
                                }
                                writer.write({
                                    type: "tool-output-available",
                                    toolCallId: id,
                                    output,
                                });
                            }
                        }
                        break;

                    case "error":
                        // 错误
                        if (chunk.content) {
                            writer.write({
                                type: "error",
                                errorText: chunk.content,
                            });
                        }
                        break;

                    case "done":
                        // 结束之前的文本部分
                        if (textPartId) {
                            writer.write({
                                type: "text-end",
                                id: textPartId,
                            });
                            textPartId = null;
                        }
                        // 完成
                        writer.write({
                            type: "finish",
                            finishReason: "stop",
                        });
                        break;
                }
            }
        }

        // 处理剩余的 buffer
        if (buffer.trim()) {
            const chunk = parseSSEEvent(buffer);
            if (chunk) {
                if (chunk.type === "done") {
                    if (textPartId) {
                        writer.write({
                            type: "text-end",
                            id: textPartId,
                        });
                    }
                    writer.write({
                        type: "finish",
                        finishReason: "stop",
                    });
                } else if (chunk.type === "text" && chunk.content) {
                    if (!textPartId) {
                        textPartId = `text-${Date.now()}`;
                        writer.write({
                            type: "text-start",
                            id: textPartId,
                        });
                    }
                    writer.write({
                        type: "text-delta",
                        id: textPartId,
                        delta: chunk.content,
                    });
                }
            }
        }

        // 确保文本部分被正确关闭
        if (textPartId) {
            writer.write({
                type: "text-end",
                id: textPartId,
            });
        }
    } finally {
        reader.releaseLock();
    }
}

export async function POST(req: NextRequest) {
    try {
        // 获取用户认证信息
        const authHeader = req.headers.get("authorization");

        // 从请求中提取消息
        const body = await req.json();
        const { messages } = body as { messages: UIMessage[] };

        if (!messages || !Array.isArray(messages)) {
            return new Response(
                JSON.stringify({
                    error: "Invalid request: messages array required",
                }),
                {
                    status: 400,
                    headers: { "Content-Type": "application/json" },
                },
            );
        }

        // 转换消息格式
        const agentMessages = messages.map(convertUIMessageToAgentMessage);

        // 调用 Python Agent 服务
        const response = await fetch(AGENT_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(authHeader ? { Authorization: authHeader } : {}),
            },
            body: JSON.stringify({
                messages: agentMessages,
                stream: true,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Agent API error:", errorText);

            return new Response(
                JSON.stringify({
                    error: `Agent service error: ${response.status}`,
                    details: errorText,
                }),
                {
                    status: response.status,
                    headers: { "Content-Type": "application/json" },
                },
            );
        }

        // 使用 createUIMessageStream 创建 AI SDK 兼容的流
        const stream = createUIMessageStream({
            execute: async ({ writer }) => {
                try {
                    await processAgentStream(response, writer);
                } catch (error) {
                    console.error("Stream processing error:", error);
                    writer.write({
                        type: "error",
                        errorText:
                            error instanceof Error
                                ? error.message
                                : "Unknown error",
                    });
                }
            },
            onError: (error) => {
                console.error("UI message stream error:", error);
                return error instanceof Error
                    ? error.message
                    : "Unknown stream error";
            },
        });

        // 返回 AI SDK 格式的流式响应
        return createUIMessageStreamResponse({
            stream,
        });
    } catch (error) {
        console.error("Chat API error:", error);

        return new Response(
            JSON.stringify({
                error: "Internal server error",
                message:
                    error instanceof Error ? error.message : "Unknown error",
            }),
            {
                status: 500,
                headers: { "Content-Type": "application/json" },
            },
        );
    }
}
