/**
 * WIDDX Cortex Chat Panel — webview-based sidebar chat interface.
 */
import * as vscode from 'vscode';
import { WiddxClient } from './client';
export declare class ChatPanelProvider implements vscode.WebviewViewProvider {
    private readonly _extensionUri;
    static readonly viewType = "widdx-cortex.chatView";
    private _view?;
    private client;
    private chatMessages;
    constructor(_extensionUri: vscode.Uri, client?: WiddxClient);
    setClient(client: WiddxClient): void;
    resolveWebviewView(webviewView: vscode.WebviewView, _context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    /** Send a message back to the webview */
    private _postMessage;
    /** Handle user chat message — stream response from API */
    private _handleUserMessage;
    /** Create a new chat session */
    private _handleNewSession;
    /** Send editor context info to the webview */
    private _sendContext;
    /** Post a message to the chat (called from extension) */
    sendMessage(text: string): void;
    /** HTML for the webview */
    private _getHtml;
}
//# sourceMappingURL=panel.d.ts.map