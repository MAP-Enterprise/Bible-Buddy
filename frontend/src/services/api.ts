const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export interface ChatResponse {
  session_id: string;
  response: string;
  audio_url: string | null;
  bible_verses: string[];
  from_knowledge_base: boolean;
}

export interface UsageStats {
  child_id: string;
  child_name: string;
  total_conversations: number;
  total_messages: number;
  most_asked_topics: string[];
  last_active: string | null;
}

export interface Conversation {
  id: string;
  child_id: string;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    timestamp: string;
  }>;
  created_at: string;
  updated_at: string;
}

export const api = {
  async chat(childId: string, message: string, ageTier: string, sessionId?: string, includeAudio = true): Promise<ChatResponse> {
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        child_id: childId,
        message,
        age_tier: ageTier,
        session_id: sessionId,
        include_audio: includeAudio,
      }),
    });
    if (!response.ok) throw new Error('Chat failed');
    return response.json();
  },

  async voiceChat(audioBlob: Blob, childId: string, ageTier: string, sessionId?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.wav');
    formData.append('child_id', childId);
    formData.append('age_tier', ageTier);
    if (sessionId) formData.append('session_id', sessionId);

    const response = await fetch(`${BACKEND_URL}/api/voice/chat`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Voice chat failed');
    return response.json();
  },

  async getChildStats(childId: string): Promise<UsageStats> {
    const response = await fetch(`${BACKEND_URL}/api/dashboard/stats/${childId}`, {
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Failed to get stats');
    return response.json();
  },

  async getConversations(childId: string, limit = 20): Promise<Conversation[]> {
    const response = await fetch(`${BACKEND_URL}/api/dashboard/conversations/${childId}?limit=${limit}`, {
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Failed to get conversations');
    const data = await response.json();
    return data.conversations;
  },

  async getSessions(childId: string): Promise<any[]> {
    const response = await fetch(`${BACKEND_URL}/api/sessions/${childId}`);
    if (!response.ok) throw new Error('Failed to get sessions');
    const data = await response.json();
    return data.sessions;
  },

  async getKnowledgeBase(): Promise<{ questions: any[]; total: number }> {
    const response = await fetch(`${BACKEND_URL}/api/knowledge-base`);
    if (!response.ok) throw new Error('Failed to get knowledge base');
    return response.json();
  },

  async getTeachers(): Promise<any[]> {
    const response = await fetch(`${BACKEND_URL}/api/teachers`);
    if (!response.ok) throw new Error('Failed to get teachers');
    const data = await response.json();
    return data.teachers;
  },
};
