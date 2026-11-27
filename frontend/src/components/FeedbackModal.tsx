import React, { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../api';

export function FeedbackModal({ kind, question, close }: { kind: 'gap' | 'expert'; question: string; close: () => void }) {
  const [sent, setSent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus();
    return () => { document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSaving(true); setError('');
    try {
      await api.feedback({ kind, question, topic: String(data.get('topic')), details: String(data.get('details')), email: String(data.get('email') || '') });
      setSent(true);
    } catch (error) { setError(error instanceof Error ? error.message : 'Could not save your feedback.'); }
    finally { setSaving(false); }
  }
  return <div className="backdrop" onMouseDown={e => { if (e.target === e.currentTarget && !saving) close(); }}>
    <section ref={dialog} className="modal" role="dialog" aria-modal="true" aria-labelledby="feedback-title" onKeyDown={e => {
      if (e.key === 'Escape' && !saving) close();
      if (e.key === 'Tab') {
        const fields = dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input,textarea,select,a[href]');
        if (!fields?.length) return;
        const first = fields[0], last = fields[fields.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }}>
      <button className="close" disabled={saving} onClick={close} aria-label="Close">×</button>
      {sent ? <div className="success"><span>✓</span><h2 id="feedback-title">Thanks for helping keep AutoLegacy current.</h2><p>Your feedback has been saved for review.</p><button className="primary" onClick={close}>Done</button></div> : <>
        <p className="eyebrow">{kind === 'gap' ? 'Help improve this answer' : 'Expert update request'}</p>
        <h2 id="feedback-title">{kind === 'gap' ? 'What knowledge is missing?' : 'What should the expert review?'}</h2>
        <p className="modal-intro">Your feedback helps keep automotive knowledge useful and up to date.</p>
        {question && <p className="question-context">Question: {question}</p>}
        <form onSubmit={send}><label>Topic<select name="topic" defaultValue={kind === 'gap' ? 'Missing step or detail' : 'Updated information'}><option>Missing step or detail</option><option>Vehicle-specific question</option><option>Possible correction</option><option>Updated information</option></select></label>
          <label>Details<textarea name="details" required maxLength={20000} rows={4} defaultValue={kind === 'gap' && question ? `Please add knowledge about: ${question}` : ''} placeholder="Describe the gap or update you’d like to see..."/></label>
          <label>Email (optional)<input name="email" type="email" maxLength={320} placeholder="you@example.com"/></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Send feedback'}</button>
        </form>
      </>}
    </section>
  </div>;
}
