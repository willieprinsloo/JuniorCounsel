'use client';

/**
 * Document Assistant Sidebar
 *
 * AI-powered chat assistant for analyzing case documents and initiating drafts.
 * Only appears when documents exist in the case.
 *
 * Features:
 * - Document analysis (extract parties, dates, facts)
 * - Draft initiation from chat
 * - Collapsible sidebar
 * - Welcome message
 */

import { useState, useEffect } from 'react';
import { ChatBox, ChatMessage } from './ChatBox';
import type { Document, User } from '@/types/api';
import { documentAssistantAPI, authAPI } from '@/lib/api/services';

interface DocumentAssistantSidebarProps {
  caseId: string;
  documents: Document[];
  onDraftCreated?: (draftId: string) => void;
}

export function DocumentAssistantSidebar({
  caseId,
  documents,
  onDraftCreated
}: DocumentAssistantSidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');

  // Only show if there are documents
  const hasDocuments = documents.length > 0;
  const completedDocs = documents.filter(d => d.overall_status === 'completed');

  // Load current user to check if admin
  useEffect(() => {
    const loadUser = async () => {
      try {
        const user = await authAPI.getCurrentUser();
        setCurrentUser(user);

        // Load custom prompt from localStorage
        const saved = localStorage.getItem('document_assistant_prompt');
        if (saved) {
          setCustomPrompt(saved);
        }
      } catch (error) {
        console.error('Failed to load user:', error);
      }
    };
    loadUser();
  }, []);

  // Auto-show welcome message when first expanded
  useEffect(() => {
    if (isExpanded && messages.length === 0 && hasDocuments) {
      const welcomeMsg = `👋 Hi! I'm your Document Assistant.

I can help you:
• 📄 Analyze your case documents to find key facts, dates, and parties
• ⚡ Start drafting affidavits, pleadings, or heads of argument
• ❓ Answer questions about your documents

Would you like me to scan your ${completedDocs.length} completed document(s) now? Just say "analyze documents" or ask me anything!

⚠️ Note: I analyze facts from uploaded documents. Always verify critical information yourself.`;

      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: welcomeMsg,
        timestamp: new Date()
      }]);
    }
  }, [isExpanded, messages.length, hasDocuments, completedDocs.length]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim() && messages.length > 0) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Use the API client which handles auth tokens properly
      const conversationHistory = messages
        .filter(m => m.role !== 'system') // Exclude system messages from history
        .map(m => ({
          role: m.role,
          content: m.content
        }));

      const data = await documentAssistantAPI.chat(caseId, message, conversationHistory);

      // Add AI response
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.ai_response,
        timestamp: new Date(),
        toolsUsed: data.tools_used,
        toolResults: data.tool_results?.map((tr: any) => ({
          tool: tr.tool,
          result: tr.result
        }))
      };

      setMessages(prev => [...prev, aiMessage]);

      // If draft was created, trigger callback
      if (data.draft_session_id && onDraftCreated) {
        onDraftCreated(data.draft_session_id);
      }

    } catch (error: any) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: error?.message || 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveTemplate = () => {
    localStorage.setItem('document_assistant_prompt', customPrompt);
    setShowTemplateModal(false);
    alert('Prompt template saved! It will be used in future conversations.');
  };

  const handleResetTemplate = () => {
    localStorage.removeItem('document_assistant_prompt');
    setCustomPrompt('');
    alert('Prompt template reset to default.');
  };

  // Check if user is admin
  const isAdmin = currentUser?.role === 'admin' || currentUser?.role === 'system_admin';

  // Don't render if no documents
  if (!hasDocuments) {
    return null;
  }

  // Collapsed view
  if (!isExpanded) {
    return (
      <button
        onClick={() => {
          setIsExpanded(true);
          setUnreadCount(0);
        }}
        className="fixed right-4 bottom-4 bg-primary text-primary-foreground rounded-full shadow-lg px-4 py-3 flex items-center gap-2 hover:bg-primary/90 transition-all z-50"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        <span className="font-medium">Assistant</span>
        {unreadCount > 0 && (
          <span className="bg-destructive text-destructive-foreground rounded-full h-5 w-5 flex items-center justify-center text-xs font-bold">
            {unreadCount}
          </span>
        )}
      </button>
    );
  }

  // Expanded view
  return (
    <div className="flex flex-col h-full bg-card border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/50">
        <div className="flex items-center gap-2">
          <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <h3 className="text-sm font-semibold text-foreground">Document Assistant</h3>
        </div>
        <div className="flex items-center gap-2">
          {/* Template Icon (Admin Only) */}
          {isAdmin && (
            <button
              onClick={() => setShowTemplateModal(true)}
              className="text-muted-foreground hover:text-primary transition-colors"
              title="Edit Prompt Template (Admin)"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h4a1 1 0 010 2H6v2a1 1 0 01-2 0V5zM4 13a1 1 0 011-1h2a1 1 0 010 2H5a1 1 0 01-1-1zm6-8a1 1 0 011-1h2a1 1 0 110 2h-2a1 1 0 01-1-1zm6 0a1 1 0 011-1h2a1 1 0 110 2h-2a1 1 0 01-1-1zM9 13a1 1 0 011-1h6a1 1 0 110 2h-6a1 1 0 01-1-1zm10-5a1 1 0 011 1v2a1 1 0 11-2 0V9a1 1 0 011-1zm-4 8a1 1 0 011 1v2a1 1 0 11-2 0v-2a1 1 0 011-1zm4 0a1 1 0 011 1v2a1 1 0 11-2 0v-2a1 1 0 011-1z" />
              </svg>
            </button>
          )}
          {/* Close Button */}
          <button
            onClick={() => setIsExpanded(false)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <ChatBox
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          placeholder="Ask about documents or start a draft..."
          enableMarkdown={true}
          maxHeight="100%"
        />
      </div>

      {/* Footer Info */}
      <div className="px-4 py-2 border-t border-border bg-muted/30">
        <p className="text-xs text-muted-foreground">
          {completedDocs.length} of {documents.length} documents ready for analysis
        </p>
      </div>

      {/* Template Editor Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Edit Document Assistant Prompt Template</h2>
              <button
                onClick={() => setShowTemplateModal(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <p className="text-sm text-muted-foreground mb-4">
                Customize the system prompt for the Document Assistant. This prompt guides how the AI responds to users.
                Leave empty to use the default prompt. Use variables: {'{case_id}'}, {'{document_count}'}, {'{completed_count}'}.
              </p>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="w-full h-64 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono"
                placeholder="Enter custom system prompt here...&#10;&#10;Example:&#10;You are a helpful legal assistant for South African law.&#10;&#10;Context: Case {case_id} has {document_count} documents.&#10;&#10;Your role is to help practitioners understand their case documents and start drafting efficiently."
              />
            </div>
            <div className="flex items-center justify-between p-4 border-t border-border bg-muted/30">
              <button
                onClick={handleResetTemplate}
                className="px-4 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 rounded-md transition-colors"
              >
                Reset to Default
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowTemplateModal(false)}
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveTemplate}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors"
                >
                  Save Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
