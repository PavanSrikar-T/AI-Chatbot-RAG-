import { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  Paperclip, 
  AlertTriangle, 
  Sparkles, 
  BookOpen, 
  FileText, 
  Plus, 
  MessageSquare, 
  Trash2, 
  ChevronLeft, 
  ChevronRight,
  Clock,
  Search,
  Edit2,
  Check,
  X,
  Pin,
  PinOff,
  Play
} from 'lucide-react';
import { 
  getConversations, 
  getConversation, 
  createConversation, 
  updateConversation,
  deleteConversation,
  getModuleState,
  saveModuleState,
  type PersistentConversation
} from '../api/persistence';

interface Source {
  document: string;
  filename: string;
  page: number;
  chunk_id: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  intent?: string;
}

interface HealthStatus {
  status: string;
  api: string;
  database: string;
  qdrant: string;
  embeddings: string;
  llm: string;
}

type KnowledgeMode = 'auto' | 'document' | 'education' | 'interview';

const DEFAULT_WELCOME: Message = { 
  role: 'assistant', 
  content: 'Hello! I am CareerMind AI — your personal interview coach, technical tutor, and resume copilot.\n\nAsk me anything: conceptual explanations, coding challenges, interview preparation, or questions directly about your uploaded documents.', 
  sources: [],
  intent: 'GENERAL_EDUCATION'
};

export default function AIChat() {
  const [conversations, setConversations] = useState<PersistentConversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [loadingConv, setLoadingConv] = useState(true);

  const [messages, setMessages] = useState<Message[]>([DEFAULT_WELCOME]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [selectedMode, setSelectedMode] = useState<KnowledgeMode>('auto');
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Search & Edit States
  const [searchQuery, setSearchQuery] = useState('');
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // Delete Modal State
  const [deletingConvId, setDeletingConvId] = useState<string | null>(null);

  const endOfMessagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 1. Restore conversations & active state on mount
  useEffect(() => {
    async function initChat() {
      setLoadingConv(true);
      const [convList, savedChatState] = await Promise.all([
        getConversations('chat'),
        getModuleState('chat')
      ]);

      setConversations(convList);

      if (savedChatState && savedChatState.mode) {
        setSelectedMode(savedChatState.mode);
      }

      // Check saved active_conversation_id from module state OR localStorage
      let targetConvId = savedChatState?.active_conversation_id || localStorage.getItem('careermind_active_conv_id');

      // Verify if targetConvId actually exists in the conversations list
      const targetExists = convList.some(c => c.id === targetConvId);
      if (!targetExists) {
        // Pick conversation with messages first, or the newest one
        const convWithMessages = convList.find(c => (c.message_count || 0) > 0);
        targetConvId = convWithMessages ? convWithMessages.id : (convList.length > 0 ? convList[0].id : null);
      }

      if (targetConvId) {
        const fullConv = await getConversation(targetConvId);
        if (fullConv && fullConv.messages && fullConv.messages.length > 0) {
          setActiveConvId(fullConv.id);
          setMessages(fullConv.messages.map(m => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
            sources: m.sources,
            intent: m.metadata?.intent
          })));
          localStorage.setItem('careermind_active_conv_id', fullConv.id);
        } else if (fullConv) {
          // If this selected conversation has no messages, check if another conversation does
          const convWithMessages = convList.find(c => c.id !== targetConvId && (c.message_count || 0) > 0);
          if (convWithMessages) {
            const altConv = await getConversation(convWithMessages.id);
            if (altConv && altConv.messages && altConv.messages.length > 0) {
              setActiveConvId(altConv.id);
              setMessages(altConv.messages.map(m => ({
                role: m.role as 'user' | 'assistant',
                content: m.content,
                sources: m.sources,
                intent: m.metadata?.intent
              })));
              localStorage.setItem('careermind_active_conv_id', altConv.id);
            } else {
              setActiveConvId(fullConv.id);
              setMessages([DEFAULT_WELCOME]);
              localStorage.setItem('careermind_active_conv_id', fullConv.id);
            }
          } else {
            setActiveConvId(fullConv.id);
            setMessages([DEFAULT_WELCOME]);
            localStorage.setItem('careermind_active_conv_id', fullConv.id);
          }
        }
      } else {
        // Create initial default conversation
        const initial = await createConversation('chat', 'Career & Interview Prep');
        if (initial) {
          setActiveConvId(initial.id);
          setConversations([initial]);
          localStorage.setItem('careermind_active_conv_id', initial.id);
        }
      }
      setLoadingConv(false);
    }

    initChat();
  }, []);

  // Save module state whenever active conversation or mode changes, and on unmount/module switch
  useEffect(() => {
    if (activeConvId) {
      saveModuleState('chat', {
        active_conversation_id: activeConvId,
        mode: selectedMode
      });
      localStorage.setItem('careermind_active_conv_id', activeConvId);
    }
  }, [activeConvId, selectedMode]);

  // Health check polling
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (err) {
        setHealth(null);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const selectConversation = async (convId: string) => {
    if (convId === activeConvId) return;
    setLoadingConv(true);
    const fullConv = await getConversation(convId);
    if (fullConv) {
      setActiveConvId(fullConv.id);
      localStorage.setItem('careermind_active_conv_id', fullConv.id);
      if (fullConv.messages && fullConv.messages.length > 0) {
        setMessages(fullConv.messages.map(m => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          sources: m.sources,
          intent: m.metadata?.intent
        })));
      } else {
        setMessages([DEFAULT_WELCOME]);
      }
      await saveModuleState('chat', {
        active_conversation_id: fullConv.id,
        mode: selectedMode
      });
    }
    setLoadingConv(false);
  };

  const handleNewConversation = async () => {
    setLoadingConv(true);
    setInput('');
    setIsTyping(false);

    try {
      const newConv = await createConversation('chat', 'New Discussion');
      if (newConv) {
        setConversations(prev => [newConv, ...prev.filter(c => c.id !== newConv.id)]);
        setActiveConvId(newConv.id);
        setMessages([DEFAULT_WELCOME]);
        localStorage.setItem('careermind_active_conv_id', newConv.id);
        await saveModuleState('chat', {
          active_conversation_id: newConv.id,
          mode: selectedMode
        });
      }
    } catch (err) {
      console.error('Error creating new conversation:', err);
    } finally {
      setLoadingConv(false);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  };

  const handleStartRename = (e: React.MouseEvent, conv: PersistentConversation) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditingTitle(conv.title);
  };

  const handleSaveRename = async (convId: string) => {
    if (!editingTitle.trim()) {
      setEditingConvId(null);
      return;
    }
    const updated = await updateConversation(convId, { title: editingTitle.trim() });
    if (updated) {
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, title: updated.title } : c));
    }
    setEditingConvId(null);
  };

  const handleTogglePin = async (e: React.MouseEvent, conv: PersistentConversation) => {
    e.stopPropagation();
    const newPinState = !conv.is_pinned;
    const updated = await updateConversation(conv.id, { is_pinned: newPinState });
    if (updated) {
      setConversations(prev => {
        const next = prev.map(c => c.id === conv.id ? { ...c, is_pinned: updated.is_pinned } : c);
        return next.sort((a, b) => Number(Boolean(b.is_pinned)) - Number(Boolean(a.is_pinned)));
      });
    }
  };

  const confirmDeleteConv = async () => {
    if (!deletingConvId) return;
    const convId = deletingConvId;
    setDeletingConvId(null);
    const ok = await deleteConversation(convId);
    if (ok) {
      const remaining = conversations.filter(c => c.id !== convId);
      setConversations(remaining);
      if (activeConvId === convId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          handleNewConversation();
        }
      }
    }
  };

  const handleContinue = () => {
    if (isTyping) return;
    handleSend("Please continue from where you left off.");
  };

  const handleSend = async (queryOverride?: string) => {
    const userQuery = (typeof queryOverride === 'string' ? queryOverride : input).trim();
    if (!userQuery || isTyping) return;

    const userMessage: Message = { role: 'user', content: userQuery, sources: [] };
    
    // Prepare conversation history context (last 6 messages)
    const historyPayload = messages.slice(-6).map(m => ({
      role: m.role,
      content: m.content
    }));

    setMessages(prev => [...prev, userMessage]);
    if (!queryOverride) {
      setInput('');
    }
    setIsTyping(true);

    let currentConvId = activeConvId;
    if (!currentConvId) {
      const created = await createConversation('chat', userQuery.slice(0, 35));
      if (created) {
        currentConvId = created.id;
        setActiveConvId(created.id);
        setConversations(prev => [created, ...prev]);
      }
    }

    if (currentConvId) {
      saveModuleState('chat', {
        active_conversation_id: currentConvId,
        mode: selectedMode
      });
    }

    // Add placeholder assistant message for streaming
    setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [] }]);

    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 90000);

    try {
      const token = localStorage.getItem('access_token') || '';
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'x-user-email': 'dev@local.host'
        },
        body: JSON.stringify({ 
          query: userQuery, 
          conversation_id: currentConvId,
          stream: true,
          mode: selectedMode,
          history: historyPayload
        }),
        signal: abortController.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          // ignore
        }
        throw new Error((errorData && errorData.detail) || `Server error: ${response.status}`);
      }

      if (!response.body) throw new Error('ReadableStream not supported.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let buffer = '';
      let receivedAnyContent = false;
      let finalSources: Source[] = [];
      let finalIntent = 'GENERAL_EDUCATION';
      let fullAssistantContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n\n')) >= 0) {
          const chunk = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 2);
          
          if (chunk.startsWith('data: ')) {
            const data = chunk.slice(6);
            if (data === '[DONE]') {
              continue;
            } else if (data.startsWith('[INTENT] ')) {
              try {
                finalIntent = JSON.parse(data.slice(9));
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  newMsgs[lastIdx] = { ...newMsgs[lastIdx], intent: finalIntent };
                  return newMsgs;
                });
              } catch (e) {
                console.error('Failed to parse intent', e);
              }
            } else if (data.startsWith('[SOURCES] ')) {
              try {
                finalSources = JSON.parse(data.slice(10));
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  newMsgs[lastIdx] = { ...newMsgs[lastIdx], sources: finalSources };
                  return newMsgs;
                });
              } catch (e) {
                console.error('Failed to parse sources', e);
              }
            } else {
              let textToken = '';
              try {
                textToken = JSON.parse(data);
              } catch (e) {
                textToken = data;
              }
              if (textToken) {
                receivedAnyContent = true;
                fullAssistantContent += textToken;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIdx = newMsgs.length - 1;
                  newMsgs[lastIdx] = { 
                    ...newMsgs[lastIdx], 
                    content: (newMsgs[lastIdx].content || '') + textToken 
                  };
                  return newMsgs;
                });
              }
            }
          }
        }
      }

      if (!receivedAnyContent) {
        fullAssistantContent = "I couldn't process your request. Please try asking again.";
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          newMsgs[lastIdx] = { 
            ...newMsgs[lastIdx], 
            content: fullAssistantContent 
          };
          return newMsgs;
        });
      }

      // Refresh conversations list to pick up auto-generated titles
      const updatedList = await getConversations('chat');
      if (updatedList && updatedList.length > 0) {
        setConversations(updatedList);
      }
      if (currentConvId) {
        saveModuleState('chat', {
          active_conversation_id: currentConvId,
          mode: selectedMode
        });
        localStorage.setItem('careermind_active_conv_id', currentConvId);
      }

    } catch (error: any) {
      clearTimeout(timeoutId);
      console.error('Chat error:', error);
      const isTimeout = error.name === 'AbortError';
      const msg = isTimeout 
        ? "Request timed out. The local LLM is processing heavy context; please retry."
        : `Error: ${error.message || 'Failed to communicate with CareerMind backend.'}`;
      
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIdx = newMsgs.length - 1;
        newMsgs[lastIdx] = { 
          ...newMsgs[lastIdx], 
          content: msg
        };
        return newMsgs;
      });
    } finally {
      setIsTyping(false);
    }
  };

  const isRagHealthy = health && health.status === 'ok';

  const getIntentBadge = (intent?: string) => {
    switch (intent) {
      case 'DOCUMENT_QA':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20 mb-2">
            <FileText className="w-3 h-3" /> Grounded in Resume
          </span>
        );
      case 'GENERAL_EDUCATION':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 mb-2">
            <BookOpen className="w-3 h-3" /> General Technical Knowledge
          </span>
        );
      case 'INTERVIEW_PREPARATION':
      case 'PROJECT_INTERVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-purple-500/10 text-purple-500 border border-purple-500/20 mb-2">
            <Sparkles className="w-3 h-3" /> Personalized Interview Prep
          </span>
        );
      case 'CODING_PROBLEM':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20 mb-2">
            💻 Coding Practice
          </span>
        );
      default:
        return null;
    }
  };

  // Filter conversations by search term
  const filteredConvs = conversations.filter(c => 
    !searchQuery.trim() || c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedConvs = filteredConvs.filter(c => c.is_pinned);
  const recentConvs = filteredConvs.filter(c => !c.is_pinned);

  return (
    <div className="h-full flex rounded-3xl border border-border overflow-hidden bg-secondary/10 animate-in fade-in zoom-in-95 duration-500 relative">
      
      {/* Delete Confirmation Modal */}
      {deletingConvId && (
        <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 p-6 rounded-2xl max-w-sm w-full shadow-xl space-y-4 animate-in zoom-in-95 duration-200">
            <div className="flex items-center space-x-3 text-rose-600">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="font-semibold text-base text-slate-900">Delete Conversation?</h3>
            </div>
            <p className="text-sm text-slate-600">
              This will permanently remove this discussion and all its message history from the database.
            </p>
            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setDeletingConvId(null)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteConv}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition-colors shadow-sm"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ChatGPT/Gemini Style Left Sidebar */}
      <div className={`transition-all duration-300 border-r border-slate-200 bg-slate-50/70 flex flex-col ${
        showSidebar ? 'w-80' : 'w-0 overflow-hidden'
      }`}>
        {/* Header & New Chat Button */}
        <div className="p-4 border-b border-slate-200 space-y-3 bg-white">
          <button
            onClick={handleNewConversation}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold hover:opacity-95 text-xs flex items-center justify-center gap-2 shadow-sm transition-all hover:shadow active:scale-[0.99]"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 placeholder:text-slate-400"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {/* Pinned Chats */}
          {pinnedConvs.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider px-2 mb-1.5 flex items-center gap-1">
                <Pin className="w-3 h-3 text-amber-500" /> Pinned
              </div>
              <div className="space-y-1">
                {pinnedConvs.map((conv) => (
                  <ChatItem 
                    key={conv.id}
                    conv={conv}
                    activeConvId={activeConvId}
                    editingConvId={editingConvId}
                    editingTitle={editingTitle}
                    setEditingTitle={setEditingTitle}
                    selectConversation={selectConversation}
                    handleStartRename={handleStartRename}
                    handleSaveRename={handleSaveRename}
                    handleTogglePin={handleTogglePin}
                    setDeletingConvId={setDeletingConvId}
                    setEditingConvId={setEditingConvId}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Recent Chats */}
          <div>
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider px-2 mb-1.5 flex items-center gap-1">
              <Clock className="w-3 h-3 text-blue-600" /> Recent Chats
            </div>
            {recentConvs.length === 0 ? (
              <div className="px-3 py-6 text-center text-xs text-slate-400 bg-white/50 rounded-xl border border-slate-100">
                {searchQuery ? 'No matching conversations' : 'No recent chats'}
              </div>
            ) : (
              <div className="space-y-1">
                {recentConvs.map((conv) => (
                  <ChatItem 
                    key={conv.id}
                    conv={conv}
                    activeConvId={activeConvId}
                    editingConvId={editingConvId}
                    editingTitle={editingTitle}
                    setEditingTitle={setEditingTitle}
                    selectConversation={selectConversation}
                    handleStartRename={handleStartRename}
                    handleSaveRename={handleSaveRename}
                    handleTogglePin={handleTogglePin}
                    setDeletingConvId={setDeletingConvId}
                    setEditingConvId={setEditingConvId}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Header */}
        <div className="h-16 border-b border-slate-200 bg-white flex items-center px-4 sm:px-6 justify-between gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition-colors"
              title={showSidebar ? 'Collapse Sidebar' : 'Expand Sidebar'}
            >
              {showSidebar ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>

            <button
              onClick={handleNewConversation}
              className="p-2 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 transition-colors flex items-center gap-1.5 text-xs font-semibold"
              title="Start New Chat"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">New Chat</span>
            </button>

            <div className="flex items-center ml-2">
              <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center mr-2.5 shadow-xs">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="font-semibold text-xs md:text-sm text-slate-900 truncate max-w-[180px] sm:max-w-xs">
                  {conversations.find(c => c.id === activeConvId)?.title || 'Career Copilot'}
                </h2>
                <p className="text-[11px] text-slate-500 hidden sm:block">
                  Grounded in Career Digital Twin & Documents
                </p>
              </div>
            </div>
          </div>

          {/* Mode Selector */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
            <button
              onClick={() => {
                setSelectedMode('auto');
                saveModuleState('chat', { active_conversation_id: activeConvId, mode: 'auto' });
              }}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                selectedMode === 'auto'
                  ? 'bg-white text-blue-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Auto-detect resume vs general knowledge queries"
            >
              Auto
            </button>
            <button
              onClick={() => {
                setSelectedMode('document');
                saveModuleState('chat', { active_conversation_id: activeConvId, mode: 'document' });
              }}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                selectedMode === 'document'
                  ? 'bg-white text-blue-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Strictly grounded in your uploaded resume/documents"
            >
              📄 Resume
            </button>
            <button
              onClick={() => {
                setSelectedMode('education');
                saveModuleState('chat', { active_conversation_id: activeConvId, mode: 'education' });
              }}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                selectedMode === 'education'
                  ? 'bg-white text-blue-700 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Computer science, coding, and interview explanations"
            >
              💡 Learn & Prep
            </button>
          </div>

          {/* RAG Engine Status */}
          {isRagHealthy ? (
            <div className="hidden lg:flex text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full items-center shadow-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
              Engine Ready
            </div>
          ) : (
            <div 
              title={health ? `API: ${health.api} | DB: ${health.database} | Qdrant: ${health.qdrant} | Embeddings: ${health.embeddings} | LLM: ${health.llm}` : "Connecting to backend..."}
              className="text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full flex items-center cursor-help"
            >
              <AlertTriangle className="w-3 h-3 mr-1 text-amber-600" />
              Engine ⚠
            </div>
          )}
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-slate-50/50">
          {loadingConv ? (
            <div className="flex flex-col items-center justify-center h-64 space-y-2 text-xs text-slate-500">
              <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span>Restoring conversation history...</span>
            </div>
          ) : (
            <>
              {/* Quick suggestions when conversation is fresh */}
              {messages.length <= 1 && (
                <div className="max-w-xl mx-auto my-6 p-6 rounded-2xl bg-white border border-slate-200/80 shadow-xs space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <Sparkles className="w-4 h-4 text-blue-600" /> Suggested Prompts
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {[
                      { title: "Explain RAG", desc: "Retrieval-Augmented Generation breakdown", icon: "🧠" },
                      { title: "Analyze my resume", desc: "Identify gaps and key strengths", icon: "📄" },
                      { title: "Prepare me for AI/ML interview", desc: "Simulate top technical questions", icon: "🎯" },
                      { title: "Ask me about my projects", desc: "Defend architecture and scalability", icon: "💻" }
                    ].map((sug, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setInput(sug.title);
                          handleSend(sug.title);
                        }}
                        className="p-3 text-left rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50 hover:border-blue-300 transition-all text-xs group"
                      >
                        <div className="font-semibold text-slate-800 group-hover:text-blue-700 flex items-center gap-1.5">
                          <span>{sug.icon}</span>
                          <span>{sug.title}</span>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{sug.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                      msg.role === 'user' ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white ml-3 shadow-xs' : 'bg-white border border-slate-200 text-blue-600 mr-3 shadow-xs'
                    }`}>
                      {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={`p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user' 
                        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-xs shadow-xs' 
                        : 'bg-white border border-slate-200 text-slate-800 rounded-tl-xs shadow-xs'
                    }`}>
                      {msg.role === 'assistant' && getIntentBadge(msg.intent)}

                      <div>
                        {msg.content || (msg.role === 'assistant' && i === messages.length - 1 && (
                          <span className="inline-flex items-center text-slate-400 animate-pulse">
                            Generating response...
                          </span>
                        ))}
                      </div>
                      
                      {/* Source Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-slate-100 text-xs">
                          <div className="text-slate-500 font-semibold mb-2 flex items-center gap-1.5">
                            Sources:
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {msg.sources.map((src: Source, idx: number) => {
                              const isGeneral = src.chunk_id === 'general_knowledge' || src.document === 'General Technical Knowledge';
                              const isInterview = src.chunk_id === 'general_interview_knowledge' || src.document.includes('Interview Knowledge');
                              
                              if (isGeneral) {
                                return (
                                  <span 
                                    key={idx} 
                                    className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg font-medium flex items-center gap-1.5"
                                  >
                                    💡 General Technical Knowledge
                                  </span>
                                );
                              }

                              if (isInterview) {
                                return (
                                  <span 
                                    key={idx} 
                                    className="px-2.5 py-1 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg font-medium flex items-center gap-1.5"
                                  >
                                    🎯 Interview & Engineering Knowledge
                                  </span>
                                );
                              }

                              return (
                                <span 
                                  key={idx} 
                                  className="px-2.5 py-1 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 rounded-lg text-slate-700 font-medium transition-colors border border-slate-200 flex items-center gap-1.5"
                                >
                                  📄 {src.filename || src.document} — Page {src.page}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      {/* Quick Continue Button on Assistant Message */}
                      {msg.role === 'assistant' && i === messages.length - 1 && i > 0 && !isTyping && msg.content && (
                        <div className="mt-3 pt-2 border-t border-slate-100 flex justify-end">
                          <button
                            onClick={handleContinue}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium text-slate-500 hover:text-blue-700 hover:bg-blue-50 transition-colors"
                            title="Continue generating from this point"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            <span>Continue</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input Controls */}
        <div className="p-4 bg-white border-t border-slate-200 space-y-2">
          {/* Quick Action: Continue */}
          {messages.length > 1 && messages[messages.length - 1].role === 'assistant' && !isTyping && (
            <div className="flex items-center gap-2 px-1">
              <button
                onClick={handleContinue}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-slate-100 hover:bg-blue-600 hover:text-white border border-slate-200 text-slate-700 transition-all shadow-xs"
                title="Ask AI to continue generating"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Continue</span>
              </button>
            </div>
          )}

          <div className="relative flex items-center">
            <button 
              title="Upload Document"
              className="absolute left-4 text-slate-400 hover:text-slate-600 p-2 rounded-full hover:bg-slate-100 transition-colors"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask CareerMind anything..."
              className="w-full bg-slate-50 border border-slate-200 rounded-2xl pl-14 pr-16 py-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm text-slate-900 placeholder:text-slate-400 transition-all"
            />
            <button 
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className={`absolute right-3 w-9 h-9 flex items-center justify-center rounded-xl transition-all ${
                input.trim() && !isTyping ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-xs hover:opacity-95' : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Single Chat Sidebar Item Component
function ChatItem({
  conv,
  activeConvId,
  editingConvId,
  editingTitle,
  setEditingTitle,
  selectConversation,
  handleStartRename,
  handleSaveRename,
  handleTogglePin,
  setDeletingConvId,
  setEditingConvId
}: {
  conv: PersistentConversation;
  activeConvId: string | null;
  editingConvId: string | null;
  editingTitle: string;
  setEditingTitle: (val: string) => void;
  selectConversation: (id: string) => void;
  handleStartRename: (e: React.MouseEvent, conv: PersistentConversation) => void;
  handleSaveRename: (id: string) => void;
  handleTogglePin: (e: React.MouseEvent, conv: PersistentConversation) => void;
  setDeletingConvId: (id: string) => void;
  setEditingConvId: (id: string | null) => void;
}) {
  const isSelected = conv.id === activeConvId;
  const isEditing = conv.id === editingConvId;

  return (
    <div
      onClick={() => selectConversation(conv.id)}
      className={`group p-2.5 rounded-xl cursor-pointer text-xs transition-all flex items-center justify-between ${
        isSelected
          ? 'bg-blue-50 text-blue-700 font-semibold border border-blue-200/80 shadow-xs'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }`}
    >
      <div className="flex items-center gap-2 truncate mr-2 flex-1 min-w-0">
        <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-blue-600' : 'text-slate-400'}`} />
        {isEditing ? (
          <input
            type="text"
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveRename(conv.id);
              if (e.key === 'Escape') setEditingConvId(null);
            }}
            onClick={(e) => e.stopPropagation()}
            autoFocus
            className="w-full bg-white border border-blue-500 rounded px-2 py-0.5 text-xs text-slate-900 focus:outline-none"
          />
        ) : (
          <span className="truncate">{conv.title || 'Untitled Chat'}</span>
        )}
      </div>

      <div className="flex items-center space-x-1 shrink-0">
        {isEditing ? (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); handleSaveRename(conv.id); }}
              className="p-1 hover:text-green-500"
              title="Save Title"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setEditingConvId(null); }}
              className="p-1 hover:text-muted-foreground"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </>
        ) : (
          <>
            <button
              onClick={(e) => handleTogglePin(e, conv)}
              className={`p-1 hover:text-amber-500 transition-opacity ${
                conv.is_pinned ? 'text-amber-500 opacity-100' : 'opacity-0 group-hover:opacity-100'
              }`}
              title={conv.is_pinned ? 'Unpin Chat' : 'Pin Chat'}
            >
              {conv.is_pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={(e) => handleStartRename(e, conv)}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-primary transition-opacity"
              title="Rename Chat"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setDeletingConvId(conv.id); }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-opacity"
              title="Delete Conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
