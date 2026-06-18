"use strict";
/**
 * WIDDX API Client — communicates with the WIDDX Cortex API server.
 * Handles chat streaming, provider management, and tool execution.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.WiddxClient = void 0;
/**
 * HTTP client for the WIDDX Cortex API.
 */
class WiddxClient {
    baseUrl;
    sessionId = null;
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }
    /** Check if the API server is reachable */
    async healthCheck() {
        try {
            const res = await fetch(`${this.baseUrl}/api/health`);
            return res.ok;
        }
        catch {
            return false;
        }
    }
    /** Get available AI providers */
    async getProviders() {
        const res = await fetch(`${this.baseUrl}/api/providers`);
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
    /** Get available tools */
    async getTools() {
        const res = await fetch(`${this.baseUrl}/api/tools`);
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        return data.tools?.map((t) => t.name) || [];
    }
    /** List sessions */
    async listSessions() {
        const res = await fetch(`${this.baseUrl}/api/sessions`);
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
    /** Create a new session */
    async newSession(name) {
        const res = await fetch(`${this.baseUrl}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
    /**
     * Stream a chat conversation.
     * Yields events as they arrive from the server.
     */
    async *streamChat(userMessage, context) {
        const body = { message: userMessage };
        if (context?.filePath)
            body.file_path = context.filePath;
        if (context?.fileContent)
            body.file_content = context.fileContent;
        if (context?.selection)
            body.selection = context.selection;
        if (this.sessionId)
            body.session_id = this.sessionId;
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
        if (!reader)
            throw new Error('No response body');
        const decoder = new TextDecoder();
        let buffer = '';
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done)
                    break;
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
                            const event = JSON.parse(data);
                            yield event;
                        }
                        catch {
                            // Skip malformed JSON
                        }
                    }
                }
            }
        }
        finally {
            reader.releaseLock();
        }
    }
    /**
     * Send a simple (non-streaming) chat message.
     */
    async sendMessage(message, context) {
        const body = { message };
        if (context)
            Object.assign(body, context);
        if (this.sessionId)
            body.session_id = this.sessionId;
        const res = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.session_id)
            this.sessionId = data.session_id;
        return data.response;
    }
    /** Set the active session */
    setSessionId(id) {
        this.sessionId = id;
    }
}
exports.WiddxClient = WiddxClient;
//# sourceMappingURL=client.js.map