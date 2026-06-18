/**
 * WIDDX API Client — communicates with the WIDDX Cortex API server.
 * Handles chat streaming, provider management, and tool execution.
 */

import * as vscode from 'vscode';

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    tool_calls?: ToolCall[];
}

export interface ToolCall {
    name: string;
    arguments: Record<string, unknown>;
    id?: string;
}

export interface ProviderInfo {
    name: string;
    model: string;
    available: boolean;
}

export interface SessionInfo {
    id: string;
    name: string;
    branch: string;
    created_at: number;
}

export interface StreamEvent {
    type: 'content' | 'reasoning' | 'tool_call' | 'tool_result' | 'done' | 'error';
    data: string;
}

/**
 * HTTP client for the WIDDX Cortex API.
 */
export class WiddxClient {
    private baseUrl: string;
    private sessionId: string | null = null;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    /** Check if the API server is reachable */
    async healthCheck(): Promise<boolean> {
        try {
            const res = await fetch(`${this.baseUrl}/api/health`);
            return res.ok;
        } catch {
            return false;
        }
    }

    /** Get available AI providers */
    async getProviders(): Promise<ProviderInfo[]> {
        const res = await fetch(`${this.baseUrl}/api/providers`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ProviderInfo[]>;
    }

    /** Get available tools */
    async getTools(): Promise<string[]> {
        const res = await fetch(`${this.baseUrl}/api/tools`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json() as { tools: { name: string }[] };
        return data.tools?.map((t) => t.name) || [];
    }

    /** List sessions */
    async listSessions(): Promise<SessionInfo[]> {
        const res = await fetch(`${this.baseUrl}/api/sessions`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<SessionInfo[]>;
    }

    /** Create a new session */
    async newSession(name: string): Promise<SessionInfo> {
        const res = await fetch(`${this.baseUrl}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<SessionInfo>;
    }

    /**
     * Stream a chat conversation.
     * Yields events as they arrive from the server.
     */
    async *streamChat(
        userMessage: string,
        context?: { filePath?: string; fileContent?: string; selection?: string }
    ): AsyncGenerator<StreamEvent> {
        const body: Record<string, unknown> = { message: userMessage };
        if (context?.filePath) body.file_path = context.filePath;
        if (context?.fileContent) body.file_content = context.fileContent;
        if (context?.selection) body.selection = context.selection;
        if (this.sessionId) body.session_id = this.sessionId;

        const res = await fetch(`${this.baseUrl}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`API error ${res.status}: ${errText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') {
                            yield { type: 'done', data: '' };
                            return;
                        }
                        try {
                            const event = JSON.parse(data) as StreamEvent;
                            yield event;
                        } catch {
                            // Skip malformed JSON
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Send a simple (non-streaming) chat message.
     */
    async sendMessage(message: string, context?: Record<string, string>): Promise<string> {
        const body: Record<string, unknown> = { message };
        if (context) Object.assign(body, context);
        if (this.sessionId) body.session_id = this.sessionId;

        const res = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json() as { response: string; session_id?: string };
        if (data.session_id) this.sessionId = data.session_id;
        return data.response;
    }

    /** Set the active session */
    setSessionId(id: string | null) {
        this.sessionId = id;
    }
}
