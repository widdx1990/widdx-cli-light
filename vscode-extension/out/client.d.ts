/**
 * WIDDX API Client — communicates with the WIDDX Cortex API server.
 * Handles chat streaming, provider management, and tool execution.
 */
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
export declare class WiddxClient {
    private baseUrl;
    private sessionId;
    constructor(baseUrl?: string);
    /** Check if the API server is reachable */
    healthCheck(): Promise<boolean>;
    /** Get available AI providers */
    getProviders(): Promise<ProviderInfo[]>;
    /** Get available tools */
    getTools(): Promise<string[]>;
    /** List sessions */
    listSessions(): Promise<SessionInfo[]>;
    /** Create a new session */
    newSession(name: string): Promise<SessionInfo>;
    /**
     * Stream a chat conversation.
     * Yields events as they arrive from the server.
     */
    streamChat(userMessage: string, context?: {
        filePath?: string;
        fileContent?: string;
        selection?: string;
    }): AsyncGenerator<StreamEvent>;
    /**
     * Send a simple (non-streaming) chat message.
     */
    sendMessage(message: string, context?: Record<string, string>): Promise<string>;
    /** Set the active session */
    setSessionId(id: string | null): void;
}
//# sourceMappingURL=client.d.ts.map