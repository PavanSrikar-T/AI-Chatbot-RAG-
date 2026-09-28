const BASE_URL = 'http://localhost:8000';

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token') || '';
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    'x-user-email': 'dev@local.host'
  };
}

// -------------------------------------------------------------
// MODULE STATE PERSISTENCE API
// -------------------------------------------------------------
export async function getModuleState(module: string) {
  try {
    const res = await fetch(`${BASE_URL}/api/modules/${module}/state`, {
      headers: getHeaders()
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.state_json || {};
  } catch (err) {
    console.warn(`[Persistence] Error loading state for module ${module}:`, err);
    return null;
  }
}

export async function saveModuleState(module: string, state_json: Record<string, any>) {
  try {
    const res = await fetch(`${BASE_URL}/api/modules/${module}/state`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ state_json })
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.state_json;
  } catch (err) {
    console.warn(`[Persistence] Error saving state for module ${module}:`, err);
    return null;
  }
}

// -------------------------------------------------------------
// CONVERSATIONS PERSISTENCE API
// -------------------------------------------------------------
export interface PersistentMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: any[];
  metadata?: any;
  created_at?: string;
}

export interface PersistentConversation {
  id: string;
  user_id: number;
  module: string;
  title: string;
  summary?: string;
  is_pinned?: boolean;
  is_archived?: boolean;
  current_state?: Record<string, any>;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: PersistentMessage[];
}

export async function getConversations(module?: string, query?: string): Promise<PersistentConversation[]> {
  try {
    let url = `${BASE_URL}/api/conversations`;
    const params = new URLSearchParams();
    if (module) params.append('module', module);
    if (query && query.trim()) params.append('q', query.trim());
    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('[Persistence] Error loading conversations:', err);
    return [];
  }
}

export async function createConversation(module: string, title?: string, currentState?: any): Promise<PersistentConversation | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/conversations`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        module,
        title: title || 'New Conversation',
        current_state: currentState || {}
      })
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('[Persistence] Error creating conversation:', err);
    return null;
  }
}

export async function getConversation(conversationId: string): Promise<PersistentConversation | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/conversations/${conversationId}`, {
      headers: getHeaders()
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn(`[Persistence] Error loading conversation ${conversationId}:`, err);
    return null;
  }
}

export async function updateConversation(
  conversationId: string, 
  updates: { title?: string; is_pinned?: boolean; is_archived?: boolean; summary?: string }
): Promise<PersistentConversation | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify(updates)
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn(`[Persistence] Error updating conversation ${conversationId}:`, err);
    return null;
  }
}

export async function addMessageToConversation(
  conversationId: string,
  role: 'user' | 'assistant' | 'system',
  content: string,
  sources?: any[],
  metadata?: any
): Promise<PersistentMessage | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        role,
        content,
        sources,
        metadata
      })
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn(`[Persistence] Error adding message to ${conversationId}:`, err);
    return null;
  }
}

export async function deleteConversation(conversationId: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/api/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    return res.ok;
  } catch (err) {
    console.warn(`[Persistence] Error deleting conversation ${conversationId}:`, err);
    return false;
  }
}

// -------------------------------------------------------------
// USER PROFILE PERSISTENCE API
// -------------------------------------------------------------
export async function getUserProfile() {
  try {
    const res = await fetch(`${BASE_URL}/api/profile`, {
      headers: getHeaders()
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('[Persistence] Error getting profile:', err);
    return null;
  }
}

export async function updateUserProfile(profileData: Record<string, any>) {
  try {
    const res = await fetch(`${BASE_URL}/api/profile`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(profileData)
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('[Persistence] Error updating profile:', err);
    return null;
  }
}
