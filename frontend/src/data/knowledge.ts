export type KnowledgeStep = { title: string; detail: string };
export type Expert = { name: string; specialty: string; experience: string; added: string };
export type DocumentLink = { title: string; type: string };
export type KnowledgeAnswer = {
  question: string; summary: string; readTime: string; steps: KnowledgeStep[];
  experts: Expert[]; documents: DocumentLink[]; safetyNote?: string;
};

export const sampleAnswer: KnowledgeAnswer = {
  question: 'How do I diagnose a no-start issue?',
  summary: 'A sensible first check for older petrol cars.',
  readTime: '8 min read',
  steps: [
    { title: 'Check battery and connections', detail: 'Look for corrosion, loose terminals, or dim lights.' },
    { title: 'Listen for the starter', detail: 'A click can point to a weak battery or connection.' },
    { title: 'Confirm fuel and spark', detail: 'Use vehicle-specific guidance before deeper work.' },
  ],
  experts: [{ name: 'James Miller', specialty: 'Master mechanic', experience: '32 years', added: '12 Mar 2026' }],
  documents: [{ title: 'Battery testing checklist', type: 'PDF' }, { title: 'Classic ignition guide', type: 'PDF' }],
  safetyNote: 'If you are unsure, stop and have the vehicle checked by a qualified mechanic.',
};
