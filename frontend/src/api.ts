export type Knowledge = {
  id: string;
  problem: string;
  expert_id?: string | null;
  expert_name?: string | null;
  experience_years?: number | null;
  vehicle_make: string | null;
  vehicle_model: string | null;
  engine_type: string | null;
  original_transcript?: string | null;
  symptoms: string[];
  operating_conditions: string[];
  possible_causes: string[];
  diagnostic_steps: string[];
  confirmed_cause: string | null;
  solution: string | null;
  expert_insight: string | null;
  common_mistakes: string[];
  safety_precautions: string[];
  source_type: 'synthetic';
};

export type Source = Knowledge & { distance: number };
export type ChatResponse = { answer: string; sources: Source[]; insufficient_evidence: boolean };
export type Health = { status: string; chat_model: string; embedding_model: string };
export type Expert = { id: string; name: string; specialty: string; experience_years: number; bio: string; synthetic: boolean };
export type KnowledgeDraft = Pick<Knowledge, 'problem' | 'vehicle_make' | 'vehicle_model' | 'engine_type' | 'symptoms' | 'operating_conditions' | 'possible_causes' | 'diagnostic_steps' | 'confirmed_cause' | 'solution' | 'expert_insight' | 'common_mistakes' | 'safety_precautions'>;
export type FeedbackInput = { kind: 'gap' | 'expert'; question: string; topic: string; details: string; email: string };

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 240_000);
  try {
    const response = await fetch(`${baseUrl}${path}`, { ...options, signal: controller.signal });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = body?.detail;
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
        ? detail.map((item: { msg: string }) => item.msg).join('; ')
        : `Backend request failed (${response.status}). Check the FastAPI server on port 8000.`);
    }
    if (body === null) throw new Error('The backend returned an unexpected response. Check the API URL.');
    return body as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The model took too long to respond. Check Ollama and try again.');
    }
    if (error instanceof TypeError) {
      throw new Error('Cannot reach the backend. Start the FastAPI server on port 8000 and try again.');
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  health: () => request<Health>('/api/health'),
  knowledge: () => request<Knowledge[]>('/api/knowledge'),
  experts: () => request<Expert[]>('/api/experts'),
  feedback: (data: FeedbackInput) => request<{ id: string; status: 'saved' }>('/api/feedback', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }),
  extract: (expert_id: string, transcript: string) => request<Knowledge>('/api/interview/extract', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ expert_id, transcript }),
  }),
  save: (expert_id: string, transcript: string, knowledge: KnowledgeDraft) => request<Knowledge>('/api/knowledge', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ expert_id, transcript, knowledge }),
  }),
  transcribe: (file: File) => {
    const data = new FormData(); data.append('file', file);
    return request<{ text: string }>('/api/transcribe', { method: 'POST', body: data });
  },
  ask: (question: string) => request<ChatResponse>('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }),
  }),
};
