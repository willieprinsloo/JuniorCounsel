'use client';

/**
 * Draft Detail Page
 *
 * View and manage a draft session with intake, generation, and citations.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { draftSessionsAPI, authAPI } from '@/lib/api/services';
import type { DraftSession, Citation, IntakeQuestion, User } from '@/types/api';
import LegalDocumentEditor from '@/components/editor/LegalDocumentEditor';
import { ChatBox, ChatMessage } from '@/components/chat/ChatBox';
import { marked } from 'marked';

// Helper function to convert plain text/markdown to HTML for the editor
const plainTextToHtml = (text: string): string => {
  if (!text) return '';

  // Check if the content is already HTML
  if (text.trim().startsWith('<')) {
    return text;
  }

  // Check if content contains markdown syntax
  const hasMarkdown = /(\*\*|__|\*|_|##|#{1,6}\s|```|\[.*\]\(.*\))/.test(text);

  if (hasMarkdown) {
    // Parse markdown to HTML
    try {
      const html = marked.parse(text, {
        breaks: true, // Convert \n to <br>
        gfm: true,    // GitHub Flavored Markdown
      });
      return html as string;
    } catch (error) {
      console.error('Markdown parsing error:', error);
      // Fall back to simple parsing
    }
  }

  // Fallback: Convert plain text to HTML paragraphs
  const paragraphs = text.split('\n\n').filter(p => p.trim());
  return paragraphs.map(p => {
    // Check if it looks like a heading (all caps, short line)
    if (p === p.toUpperCase() && p.length < 100 && !p.includes('.')) {
      return `<h2>${p.trim()}</h2>`;
    }
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
};

// Helper function to convert HTML to plain text for the backend
const htmlToPlainText = (html: string): string => {
  if (!html) return '';

  // Create a temporary div to parse HTML
  const temp = document.createElement('div');
  temp.innerHTML = html;

  // Get text content, preserving some structure
  let text = temp.innerText || temp.textContent || '';
  return text;
};

export default function DraftDetailPage() {
  const params = useParams();
  const router = useRouter();
  const draftId = params.id as string;

  const [draft, setDraft] = useState<DraftSession | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [intakeQuestions, setIntakeQuestions] = useState<IntakeQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'draft' | 'citations'>('draft');

  const [intakeResponses, setIntakeResponses] = useState<Record<string, any>>({});
  const [submittingIntake, setSubmittingIntake] = useState(false);
  const [startingGeneration, setStartingGeneration] = useState(false);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [sendingChat, setSendingChat] = useState(false);

  // Template customization state (admin-only)
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');

  // Use ref to track if we've initialized responses to prevent clearing on poll
  const responsesInitialized = useRef(false);
  const editModeInitialized = useRef(false);

  // Track scroll position to prevent unwanted scrolling
  const editorScrollRef = useRef<HTMLDivElement>(null);
  const lastScrollPosition = useRef(0);

  const loadDraftData = useCallback(async () => {
    try {
      const draftData = await draftSessionsAPI.get(draftId);
      console.log('Draft data loaded:', { status: draftData.status, research_summary: draftData.research_summary });
      setDraft(draftData);

      // Load intake questions if draft is awaiting intake (only once)
      if (draftData.status === 'awaiting_intake' && intakeQuestions.length === 0) {
        try {
          const questionsData = await draftSessionsAPI.getIntakeQuestions(draftId);
          setIntakeQuestions(questionsData.questions);

          // Initialize responses with existing data or empty strings (only if not already initialized)
          if (!responsesInitialized.current) {
            const initialResponses: Record<string, any> = {};
            questionsData.questions.forEach((q) => {
              initialResponses[q.field] = draftData.intake_responses?.[q.field] || '';
            });
            setIntakeResponses(initialResponses);
            responsesInitialized.current = true;
          }
        } catch (err) {
          console.error('Failed to load intake questions:', err);
        }
      }

      // Load citations if draft is ready
      if (draftData.status === 'ready' || draftData.status === 'review') {
        try {
          const citationsData = await draftSessionsAPI.getCitations(draftId);
          setCitations(citationsData.citations);
        } catch (err) {
          console.error('Failed to load citations:', err);
        }
      }

      setLoading(false);
    } catch (err) {
      setError('Failed to load draft');
      setLoading(false);
      console.error(err);
    }
  }, [draftId, intakeQuestions.length]);

  useEffect(() => {
    loadDraftData();
    const interval = setInterval(loadDraftData, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [loadDraftData]);

  // Load current user to check if admin
  useEffect(() => {
    const loadUser = async () => {
      try {
        const user = await authAPI.getCurrentUser();
        setCurrentUser(user);

        // Load custom prompt from localStorage
        const saved = localStorage.getItem('draft_chat_prompt');
        if (saved) {
          setCustomPrompt(saved);
        }
      } catch (error) {
        console.error('Failed to load user:', error);
      }
    };
    loadUser();
  }, []);

  const handleSubmitIntake = async () => {
    if (!draft) {
      console.error('No draft available');
      return;
    }

    console.log('Submitting intake responses:', intakeResponses);
    setSubmittingIntake(true);

    try {
      const updated = await draftSessionsAPI.submitIntake(draftId, {
        intake_responses: intakeResponses,
      });
      console.log('Intake submitted successfully:', updated);
      setDraft(updated);

      // Automatically start generation after successful submission
      try {
        await draftSessionsAPI.startGeneration(draftId);

        // Navigate back to case detail page with success message
        router.push(`/cases/${draft.case_id}?success=true&message=${encodeURIComponent('✓ Your answers have been submitted! We are now generating your draft document. This may take a few minutes.')}`);
      } catch (genErr) {
        console.error('Failed to start generation:', genErr);
        // Even if auto-start fails, navigate back
        router.push(`/cases/${draft.case_id}?success=true&message=${encodeURIComponent('✓ Your answers have been submitted successfully!')}`);
      }
    } catch (err: any) {
      console.error('Failed to submit intake:', err);
      alert(`Failed to submit answers: ${err?.message || 'Unknown error'}`);
      setSubmittingIntake(false);
    }
  };

  const handleStartGeneration = async () => {
    setStartingGeneration(true);
    try {
      const updated = await draftSessionsAPI.startGeneration(draftId);
      setDraft(updated);
    } catch (err) {
      console.error('Failed to start generation:', err);
    } finally {
      setStartingGeneration(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editedContent.trim()) {
      alert('Content cannot be empty');
      return;
    }

    setSavingEdit(true);
    try {
      // Convert HTML to plain text for backend storage
      const plainContent = htmlToPlainText(editedContent);
      const updated = await draftSessionsAPI.updateContent(draftId, plainContent);
      setDraft(updated);
      setIsEditing(false);

      // Navigate back to case with success message
      router.push(`/cases/${updated.case_id}?success=true&message=${encodeURIComponent('✓ Draft saved successfully!')}`);
    } catch (err: any) {
      console.error('Failed to save edit:', err);
      alert(`Failed to save: ${err?.message || 'Unknown error'}`);
      setSavingEdit(false);
    }
  };

  const handleCancelEdit = () => {
    // Navigate back to case without saving
    if (!draft) return;
    router.push(`/cases/${draft.case_id}`);
  };

  const handleExport = async (format: 'pdf' | 'docx' | 'markdown') => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        alert('Please log in to export documents');
        return;
      }

      if (!draft) {
        alert('Draft not loaded');
        return;
      }

      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = format === 'markdown' ? 'markdown' : format === 'docx' ? 'docx' : 'pdf';
      const url = `${baseURL}/api/v1/draft-sessions/${draftId}/export/${endpoint}?citation_format=endnotes`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `${draft.title}.${format === 'docx' ? 'docx' : format === 'markdown' ? 'md' : 'pdf'}`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Download file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message}`);
    }
  };

  const handleSaveTemplate = () => {
    localStorage.setItem('draft_chat_prompt', customPrompt);
    setShowTemplateModal(false);
    alert('Prompt template saved! It will be used in future draft conversations.');
  };

  const handleResetTemplate = () => {
    localStorage.removeItem('draft_chat_prompt');
    setCustomPrompt('');
    alert('Prompt template reset to default.');
  };

  const handleSendChat = async (message: string) => {
    setSendingChat(true);

    // Check if this is the first message (no existing messages)
    const isFirstMessage = chatMessages.length === 0;

    // Add user message immediately (unless it's the first message which is auto-triggered)
    if (message) {
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, userMessage]);
    }

    try {
      const response = await draftSessionsAPI.chat(draftId, message || '', isFirstMessage);

      // Add AI response to history with tool information
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.ai_response,
        timestamp: new Date(),
        toolsUsed: response.tools_used || [],
        toolResults: response.tool_results || [],
      };
      setChatMessages(prev => [...prev, assistantMessage]);

      // Refresh draft to get updated content (if document was modified)
      if (response.document_modified) {
        const updated = await draftSessionsAPI.get(draftId);
        setDraft(updated);

        // If in edit mode, update edited content (convert to HTML)
        if (isEditing) {
          setEditedContent(plainTextToHtml(updated.draft_doc?.content || ''));
        }
      }
    } catch (err: any) {
      console.error('Failed to send chat:', err);
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Chat failed: ${err?.message || 'Unknown error'}. Please try again.`,
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setSendingChat(false);
    }
  };

  // Auto-trigger welcome message on first load when in review mode (disabled to prevent scrolling)
  // Users can manually start chatting when ready
  // useEffect(() => {
  //   if (draft?.status === 'review' && chatMessages.length === 0 && !sendingChat) {
  //     // Trigger welcome message
  //     handleSendChat('');
  //   }
  // }, [draft?.status]);

  // Initialize edited content and auto-enable edit mode for ready/review drafts
  useEffect(() => {
    if (draft?.draft_doc?.content) {
      // Save current scroll position
      if (editorScrollRef.current) {
        lastScrollPosition.current = editorScrollRef.current.scrollTop;
      }

      // Convert plain text to HTML for the editor
      const htmlContent = plainTextToHtml(draft.draft_doc.content);

      // Only update content if we're not in edit mode to prevent scroll jumping
      // When user is editing, we don't want polling to overwrite their work
      if (!isEditing) {
        setEditedContent(htmlContent);
      }

      // Auto-enable edit mode for ready/review drafts (only once)
      if ((draft.status === 'ready' || draft.status === 'review') && !editModeInitialized.current) {
        setIsEditing(true);
        setEditedContent(htmlContent); // Set content when first entering edit mode
        editModeInitialized.current = true;
      }

      // Restore scroll position after content update
      setTimeout(() => {
        if (editorScrollRef.current && lastScrollPosition.current > 0) {
          editorScrollRef.current.scrollTop = lastScrollPosition.current;
        }
      }, 0);
    }
  }, [draft?.draft_doc?.content, draft?.status, isEditing]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      initializing: 'bg-secondary/10 text-secondary border border-secondary/20',
      awaiting_intake: 'bg-secondary/10 text-secondary border border-secondary/20',
      research: 'bg-secondary/10 text-secondary border border-secondary/20',
      drafting: 'bg-secondary/10 text-secondary border border-secondary/20',
      review: 'bg-secondary/10 text-secondary border border-secondary/20',
      ready: 'bg-success/10 text-success border border-success/20',
      failed: 'bg-destructive/10 text-destructive border border-destructive/20',
    };
    return colors[status] || 'bg-muted text-card-foreground border border-border';
  };

  // Check if user is admin
  const isAdmin = currentUser?.role === 'admin' || currentUser?.role === 'system_admin';

  if (loading) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading draft...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !draft) {
    return (
      <AppLayout>
        <div className="rounded-md bg-destructive/10 p-4 border border-destructive/20">
          <p className="text-sm text-destructive">{error || 'Draft not found'}</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="h-full flex flex-col overflow-hidden">
        {/* Error Message (if any) */}
        {draft.error_message && (
          <div className="rounded-md bg-destructive/10 p-4 border border-destructive/20 flex-shrink-0 mb-3">
            <p className="text-sm text-destructive">{draft.error_message}</p>
          </div>
        )}

        {/* Awaiting Intake */}
        {draft.status === 'awaiting_intake' && (
          <div className="bg-card shadow rounded-lg p-6 border border-border flex-1 overflow-y-auto">
            <h2 className="text-lg font-medium text-foreground mb-4">
              Answer a Few Questions
            </h2>
            <p className="text-sm text-muted-foreground mb-6">
              To help generate your draft, please answer the following questions about your case.
            </p>

            {intakeQuestions.length === 0 ? (
              <p className="text-sm text-muted-foreground">Loading questions...</p>
            ) : (
              <div className="space-y-4">
                {intakeQuestions.map((question) => {
                  const fieldType = question.type || 'text';

                  return (
                    <div key={question.field}>
                      <label className="block text-sm font-medium text-card-foreground">
                        {question.prompt}
                        {question.required && <span className="text-destructive ml-1">*</span>}
                      </label>

                      {/* Text input */}
                      {fieldType === 'text' && (
                        <input
                          type="text"
                          className="mt-1 block w-full rounded-md border-input shadow-sm focus:border-primary focus:ring-primary sm:text-sm px-3 py-2 border bg-background text-foreground transition-colors"
                          value={intakeResponses[question.field] || ''}
                          onChange={(e) =>
                            setIntakeResponses((prev) => ({
                              ...prev,
                              [question.field]: e.target.value,
                            }))
                          }
                          placeholder={`Enter ${question.prompt.toLowerCase()}...`}
                          required={question.required}
                        />
                      )}

                      {/* Textarea */}
                      {fieldType === 'textarea' && (
                        <textarea
                          className="mt-1 block w-full rounded-md border-input shadow-sm focus:border-primary focus:ring-primary sm:text-sm px-3 py-2 border bg-background text-foreground transition-colors"
                          rows={4}
                          value={intakeResponses[question.field] || ''}
                          onChange={(e) =>
                            setIntakeResponses((prev) => ({
                              ...prev,
                              [question.field]: e.target.value,
                            }))
                          }
                          placeholder={`Enter ${question.prompt.toLowerCase()}...`}
                          required={question.required}
                        />
                      )}

                      {/* Select dropdown */}
                      {fieldType === 'select' && (
                        <select
                          className="mt-1 block w-full rounded-md border-input shadow-sm focus:border-primary focus:ring-primary sm:text-sm px-3 py-2 border bg-background text-foreground transition-colors"
                          value={intakeResponses[question.field] || ''}
                          onChange={(e) =>
                            setIntakeResponses((prev) => ({
                              ...prev,
                              [question.field]: e.target.value,
                            }))
                          }
                          required={question.required}
                        >
                          <option value="">-- Select --</option>
                          {question.options?.map((option: string) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      )}

                      {/* Boolean (Yes/No) */}
                      {fieldType === 'boolean' && (
                        <div className="mt-1 flex items-center space-x-4">
                          <label className="inline-flex items-center">
                            <input
                              type="radio"
                              className="form-radio text-primary"
                              name={question.field}
                              value="true"
                              checked={intakeResponses[question.field] === 'true' || intakeResponses[question.field] === true}
                              onChange={(e) =>
                                setIntakeResponses((prev) => ({
                                  ...prev,
                                  [question.field]: 'true',
                                }))
                              }
                              required={question.required}
                            />
                            <span className="ml-2 text-sm text-foreground">Yes</span>
                          </label>
                          <label className="inline-flex items-center">
                            <input
                              type="radio"
                              className="form-radio text-primary"
                              name={question.field}
                              value="false"
                              checked={intakeResponses[question.field] === 'false' || intakeResponses[question.field] === false}
                              onChange={(e) =>
                                setIntakeResponses((prev) => ({
                                  ...prev,
                                  [question.field]: 'false',
                                }))
                              }
                              required={question.required}
                            />
                            <span className="ml-2 text-sm text-foreground">No</span>
                          </label>
                        </div>
                      )}

                      {/* Help text */}
                      {(question as any).help_text && (
                        <p className="mt-1 text-xs text-muted-foreground">{(question as any).help_text}</p>
                      )}
                    </div>
                  );
                })}

                <div className="pt-4">
                  <button
                    onClick={handleSubmitIntake}
                    disabled={submittingIntake}
                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 disabled:opacity-50 transition-colors"
                  >
                    {submittingIntake ? 'Submitting...' : 'Submit Answers'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Research Status */}
        {draft.status === 'research' && (
          <div className="bg-card shadow rounded-lg p-6 border border-border flex-shrink-0">
            {draft.research_summary ? (
              <>
                <h2 className="text-lg font-medium text-foreground mb-4">
                  Research Complete
                </h2>
                <p className="text-sm text-muted-foreground mb-6">
                  We've analyzed your case documents and are ready to generate the draft.
                </p>

                <button
                  onClick={handleStartGeneration}
                  disabled={startingGeneration}
                  className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {startingGeneration ? 'Starting...' : 'Start Drafting'}
                </button>
              </>
            ) : (
              <>
                <div className="flex items-center mb-4">
                  <div className="flex-shrink-0">
                    <svg
                      className="animate-spin h-8 w-8 text-primary"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-lg font-medium text-foreground">
                      Researching case documents...
                    </p>
                    <p className="text-sm text-muted-foreground">
                      This may take a few minutes. The page will update automatically.
                    </p>
                  </div>
                </div>
                <div className="mt-6 pt-6 border-t border-border">
                  <p className="text-sm text-muted-foreground mb-4">
                    If research is taking too long, you can skip to drafting:
                  </p>
                  <button
                    onClick={handleStartGeneration}
                    disabled={startingGeneration}
                    className="inline-flex justify-center py-2 px-4 border border-border shadow-sm text-sm font-medium rounded-md text-foreground bg-background hover:bg-muted disabled:opacity-50 transition-colors"
                  >
                    {startingGeneration ? 'Starting...' : 'Skip Research & Start Drafting'}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Processing Status */}
        {(draft.status === 'initializing' || draft.status === 'drafting') && (
          <div className="bg-card shadow rounded-lg p-6 border border-border flex-shrink-0">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="animate-spin h-8 w-8 text-primary"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-lg font-medium text-foreground">
                  {draft.status === 'initializing' ? 'Initializing...' : 'Drafting document...'}
                </p>
                <p className="text-sm text-muted-foreground">
                  This may take a few minutes. The page will update automatically.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Draft Ready */}
        {(draft.status === 'ready' || draft.status === 'review') && draft.draft_doc && (
          <>
            {/* Tabs */}
            <div className="border-b border-border flex-shrink-0">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('draft')}
                  className={`${
                    activeTab === 'draft'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
                >
                  Draft Document
                </button>
                <button
                  onClick={() => setActiveTab('citations')}
                  className={`${
                    activeTab === 'citations'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
                >
                  Citations ({citations.length})
                </button>
              </nav>
            </div>

            {/* Draft Content */}
            {activeTab === 'draft' && (
              <div className={`flex-1 grid grid-cols-1 gap-3 min-h-0 mt-3 ${draft.status === 'review' ? 'lg:grid-cols-[2fr_1fr]' : 'lg:grid-cols-1'}`}>
                {/* Main Content Area - Left Side */}
                <div className="bg-card shadow rounded-lg border border-border overflow-hidden h-full min-h-0">
                  {isEditing ? (
                    /* Edit Mode */
                    <div className="flex flex-col h-full">
                      {/* Header with Title and Actions */}
                      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
                        <h2 className="text-lg font-semibold text-foreground">
                          {draft.title} - {draft.document_type}
                        </h2>
                        <div className="flex items-center gap-3">
                          {/* Export Buttons */}
                          <div className="flex items-center gap-2 mr-2">
                            <button
                              onClick={() => handleExport('pdf')}
                              className="inline-flex items-center px-3 py-2 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted transition-all"
                              title="Export to PDF"
                            >
                              📄 PDF
                            </button>
                            <button
                              onClick={() => handleExport('docx')}
                              className="inline-flex items-center px-3 py-2 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted transition-all"
                              title="Export to Word"
                            >
                              📝 Word
                            </button>
                            <button
                              onClick={() => handleExport('markdown')}
                              className="inline-flex items-center px-3 py-2 border border-border text-xs font-medium rounded-md text-foreground bg-background hover:bg-muted transition-all"
                              title="Export to Markdown"
                            >
                              📋 MD
                            </button>
                          </div>
                          <button
                            onClick={handleCancelEdit}
                            disabled={savingEdit}
                            className="inline-flex items-center px-4 py-2 border border-border text-sm font-medium rounded-lg text-foreground bg-background hover:bg-muted disabled:opacity-50 transition-all"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSaveEdit}
                            disabled={savingEdit}
                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-primary-foreground bg-primary hover:bg-primary/90 disabled:opacity-50 transition-all"
                          >
                            {savingEdit ? 'Saving...' : 'Save'}
                          </button>
                        </div>
                      </div>
                      {/* Editor Content */}
                      <div ref={editorScrollRef} className="flex-1 overflow-y-auto p-6">
                        <LegalDocumentEditor
                          content={editedContent}
                          onChange={setEditedContent}
                          editable={!savingEdit}
                          placeholder="Start typing your legal document..."
                        />
                      </div>
                    </div>
                  ) : (
                    /* View Mode */
                    <div className="h-full overflow-y-auto">
                      <div className="prose max-w-none p-6">
                        {draft.draft_doc.content ? (
                          <pre className="whitespace-pre-wrap font-serif text-foreground">
                            {draft.draft_doc.content}
                          </pre>
                        ) : (
                          <p className="text-muted-foreground">No content available</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Chat Interface on Right (Review Mode Only) */}
                {draft.status === 'review' && (
                  <div className="h-full min-h-0 flex flex-col bg-card border border-border rounded-lg shadow overflow-hidden">
                    {/* Chat Header with Template Icon */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/50">
                      <div className="flex items-center gap-2">
                        <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        <h3 className="text-sm font-semibold text-foreground">Draft Assistant</h3>
                      </div>
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
                    </div>
                    {/* Chat Content */}
                    <div className="flex-1 min-h-0">
                      <ChatBox
                        messages={chatMessages}
                        onSendMessage={handleSendChat}
                        isLoading={sendingChat}
                        placeholder="e.g., Make the introduction more concise..."
                        welcomeMessage="Hi! I'm your draft assistant. I can help you improve your draft with specific requests like:\n\n• Make sections shorter or more detailed\n• Strengthen legal arguments\n• Improve clarity and readability\n• Adjust tone and style\n\nWhat would you like me to help with?"
                        enableMarkdown={true}
                        showTimestamps={false}
                        maxHeight="100%"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Citations Tab */}
            {activeTab === 'citations' && (
              <div className="flex-1 bg-card shadow rounded-lg border border-border overflow-y-auto mt-3">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg font-medium text-foreground mb-4">
                    Citations ({citations.length})
                  </h3>

                  {citations.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No citations found.</p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {citations.map((citation, index) => (
                        <li key={index} className="py-4">
                          <div className="flex items-start">
                            <span className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-primary/10 text-primary text-sm font-medium flex-shrink-0 border border-primary/20">
                              {citation.marker}
                            </span>
                            <div className="ml-4 flex-1">
                              <p className="text-sm font-medium text-foreground">
                                {citation.document_name}
                                {citation.page && ` - Page ${citation.page}`}
                              </p>
                              <p className="mt-1 text-sm text-muted-foreground">
                                {citation.content}
                              </p>
                              {citation.similarity && (
                                <p className="mt-1 text-xs text-muted-foreground">
                                  Relevance: {(citation.similarity * 100).toFixed(1)}%
                                </p>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Template Editor Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">Edit Draft Assistant Prompt Template</h2>
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
                Customize the system prompt for the Draft Assistant. This prompt guides how the AI helps improve drafts.
                Leave empty to use the default prompt. Use variables: {'{draft_id}'}, {'{draft_title}'}, {'{document_type}'}.
              </p>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                className="w-full h-64 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono"
                placeholder="Enter custom system prompt here...&#10;&#10;Example:&#10;You are a skilled legal editor for South African litigation.&#10;&#10;Context: Draft {draft_id} - {draft_title} ({document_type})&#10;&#10;Your role is to help practitioners refine their drafts with precision and clarity while maintaining proper legal formatting."
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
    </AppLayout>
  );
}
