"use strict";
/**
 * WIDDX Cortex Chat Panel — webview-based sidebar chat interface.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatPanelProvider = void 0;
const vscode = __importStar(require("vscode"));
const client_1 = require("./client");
class ChatPanelProvider {
    _extensionUri;
    static viewType = 'widdx-cortex.chatView';
    _view;
    client;
    chatMessages = [];
    constructor(_extensionUri, client) {
        this._extensionUri = _extensionUri;
        this.client = client || new client_1.WiddxClient();
    }
    setClient(client) {
        this.client = client;
    }
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this._extensionUri, 'media'),
                vscode.Uri.joinPath(this._extensionUri, 'out')
            ]
        };
        webviewView.webview.html = this._getHtml(webviewView.webview);
        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'sendMessage':
                    await this._handleUserMessage(message.text);
                    break;
                case 'newSession':
                    await this._handleNewSession();
                    break;
                case 'clearChat':
                    this.chatMessages = [];
                    this._postMessage({ type: 'clearChat' });
                    break;
                case 'getContext':
                    await this._sendContext();
                    break;
            }
        });
        // Send initial context
        this._sendContext();
    }
    /** Send a message back to the webview */
    _postMessage(message) {
        this._view?.webview.postMessage(message);
    }
    /** Handle user chat message — stream response from API */
    async _handleUserMessage(text) {
        // Show user message
        this._postMessage({ type: 'userMessage', text });
        this.chatMessages.push(`user: ${text}`);
        // Get editor context
        const editor = vscode.window.activeTextEditor;
        const context = {};
        if (editor) {
            context.filePath = editor.document.uri.fsPath;
            context.fileContent = editor.document.getText();
            context.selection = editor.document.getText(editor.selection);
        }
        this._postMessage({ type: 'thinking', text: 'Thinking...' });
        try {
            for await (const event of this.client.streamChat(text, context)) {
                switch (event.type) {
                    case 'content':
                        this._postMessage({ type: 'content', text: event.data });
                        break;
                    case 'reasoning':
                        this._postMessage({ type: 'reasoning', text: event.data });
                        break;
                    case 'tool_call':
                        this._postMessage({ type: 'toolCall', text: event.data });
                        break;
                    case 'tool_result':
                        this._postMessage({ type: 'toolResult', text: event.data });
                        break;
                    case 'done':
                        this._postMessage({ type: 'done' });
                        break;
                    case 'error':
                        this._postMessage({ type: 'error', text: event.data });
                        break;
                }
            }
        }
        catch (error) {
            this._postMessage({
                type: 'error',
                text: `Failed to connect to WIDDX API. Make sure the server is running: widdx-api`
            });
        }
    }
    /** Create a new chat session */
    async _handleNewSession() {
        try {
            const session = await this.client.newSession(`VS Code ${new Date().toLocaleDateString()}`);
            this.client.setSessionId(session.id);
            this.chatMessages = [];
            this._postMessage({ type: 'systemMessage', text: `New session: ${session.name}` });
            this._postMessage({ type: 'clearChat' });
        }
        catch (error) {
            this._postMessage({ type: 'error', text: 'Failed to create new session' });
        }
    }
    /** Send editor context info to the webview */
    async _sendContext() {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const selection = editor.selection;
            const file = editor.document;
            this._postMessage({
                type: 'contextUpdate',
                context: {
                    file: file.uri.fsPath.split(/[/\\]/).pop(),
                    language: file.languageId,
                    lines: file.lineCount,
                    hasSelection: !selection.isEmpty,
                    selectedLines: selection.isEmpty ? 0 : selection.end.line - selection.start.line + 1
                }
            });
        }
    }
    /** Post a message to the chat (called from extension) */
    sendMessage(text) {
        this._postMessage({ type: 'userMessage', text });
        this._handleUserMessage(text);
    }
    /** HTML for the webview */
    _getHtml(webview) {
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'style.css'));
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${styleUri}">
    <title>WIDDX Cortex Chat</title>
</head>
<body>
    <div id="chat-container">
        <div id="chat-header">
            <span class="brand">🧠 WIDDX Cortex</span>
            <div class="header-actions">
                <button id="btn-new-session" title="New Session">+</button>
                <button id="btn-clear" title="Clear Chat">🗑</button>
            </div>
        </div>

        <div id="context-bar">
            <span id="ctx-file">No file open</span>
            <span id="ctx-model">Loading...</span>
        </div>

        <div id="messages"></div>

        <div id="input-area">
            <textarea id="chat-input" rows="2"
                placeholder="Ask WIDDX about your code... (Shift+Enter for new line)"
            ></textarea>
            <button id="btn-send">Send</button>
        </div>

        <div id="status-bar">
            <span id="status-text">⚪ Disconnected</span>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const messagesEl = document.getElementById('messages');
        const inputEl = document.getElementById('chat-input');
        const sendBtn = document.getElementById('btn-send');
        const statusEl = document.getElementById('status-text');
        const ctxFileEl = document.getElementById('ctx-file');
        let currentAiMsg = null;
        let isStreaming = false;

        // Send message
        function sendMessage() {
            const text = inputEl.value.trim();
            if (!text || isStreaming) return;
            inputEl.value = '';
            vscode.postMessage({ type: 'sendMessage', text });
            isStreaming = true;
            sendBtn.disabled = true;
        }

        sendBtn.addEventListener('click', sendMessage);
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.getElementById('btn-new-session').addEventListener('click', () => {
            vscode.postMessage({ type: 'newSession' });
        });

        document.getElementById('btn-clear').addEventListener('click', () => {
            vscode.postMessage({ type: 'clearChat' });
        });

        // Handle messages from extension
        window.addEventListener('message', (event) => {
            const msg = event.data;
            switch (msg.type) {
                case 'userMessage':
                    addMessage('user', msg.text);
                    break;

                case 'thinking':
                    showThinking(true);
                    break;

                case 'content':
                    showThinking(false);
                    appendToAi(msg.text);
                    break;

                case 'reasoning':
                    showThinking(false);
                    addMessage('reasoning', '🧠 ' + msg.text);
                    break;

                case 'toolCall':
                    addMessage('tool', '🔧 ' + msg.text);
                    break;

                case 'toolResult':
                    addMessage('tool-result', '└─ ' + msg.text);
                    break;

                case 'done':
                    showThinking(false);
                    currentAiMsg = null;
                    isStreaming = false;
                    sendBtn.disabled = false;
                    setStatus('🟢 Connected', 'connected');
                    break;

                case 'error':
                    showThinking(false);
                    addMessage('error', '❌ ' + msg.text);
                    currentAiMsg = null;
                    isStreaming = false;
                    sendBtn.disabled = false;
                    setStatus('🔴 Error', 'error');
                    break;

                case 'systemMessage':
                    addMessage('system', '⚙ ' + msg.text);
                    break;

                case 'clearChat':
                    messagesEl.innerHTML = '';
                    currentAiMsg = null;
                    break;

                case 'contextUpdate':
                    if (msg.context) {
                        const c = msg.context;
                        ctxFileEl.textContent = c.file
                            ? c.language.toUpperCase() + ' ' + c.file + ' (' + c.lines + ' lines)'
                            : 'No file open';
                    }
                    break;
            }
        });

        function addMessage(type, text) {
            const div = document.createElement('div');
            div.className = 'message msg-' + type;
            div.textContent = text;
            messagesEl.appendChild(div);
            scrollToBottom();
        }

        function appendToAi(text) {
            if (!currentAiMsg) {
                currentAiMsg = document.createElement('div');
                currentAiMsg.className = 'message msg-ai';
                messagesEl.appendChild(currentAiMsg);
            }
            currentAiMsg.textContent += text;
            scrollToBottom();
        }

        function showThinking(show) {
            let el = document.getElementById('thinking-indicator');
            if (show) {
                if (!el) {
                    el = document.createElement('div');
                    el.id = 'thinking-indicator';
                    el.className = 'message msg-thinking';
                    el.textContent = '🤔 Thinking...';
                    messagesEl.appendChild(el);
                }
            } else {
                if (el) el.remove();
            }
        }

        function setStatus(text, cls) {
            statusEl.textContent = text;
            statusEl.className = cls || '';
        }

        function scrollToBottom() {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        // Check server connection on load
        async function checkConnection() {
            setStatus('🟡 Connecting...', 'connecting');
            vscode.postMessage({ type: 'getContext' });
        }
        checkConnection();
    </script>
</body>
</html>`;
    }
}
exports.ChatPanelProvider = ChatPanelProvider;
//# sourceMappingURL=panel.js.map