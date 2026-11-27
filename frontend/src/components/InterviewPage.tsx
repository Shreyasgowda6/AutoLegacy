import React, { useEffect, useState, type FormEvent } from 'react';
import { api, type Expert, type Knowledge, type KnowledgeDraft } from '../api';
import { AudioCapture } from './AudioCapture';

const listFields = [
  ['symptoms', 'Symptoms'], ['operating_conditions', 'Operating conditions'], ['possible_causes', 'Possible causes'],
  ['diagnostic_steps', 'Diagnostic steps'], ['common_mistakes', 'Common mistakes'], ['safety_precautions', 'Safety precautions'],
] as const;

function content(record: Knowledge): KnowledgeDraft {
  const { problem, vehicle_make, vehicle_model, engine_type, symptoms, operating_conditions, possible_causes,
    diagnostic_steps, confirmed_cause, solution, expert_insight, common_mistakes, safety_precautions } = record;
  return { problem, vehicle_make, vehicle_model, engine_type, symptoms, operating_conditions, possible_causes,
    diagnostic_steps, confirmed_cause, solution, expert_insight, common_mistakes, safety_precautions };
}

export function InterviewPage({ experts, selectedExpert, navigate }: { experts: Expert[]; selectedExpert: string; navigate: (target: string) => void }) {
  const [expertId, setExpertId] = useState(selectedExpert || experts[0]?.id || '');
  const [transcript, setTranscript] = useState('');
  const [mode, setMode] = useState<'text' | 'audio'>('text');
  const [draft, setDraft] = useState<KnowledgeDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [audioBusy, setAudioBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState<Knowledge | null>(null);
  useEffect(() => { if (!expertId && experts.length) setExpertId(experts[0].id); }, [experts, expertId]);
  function updateTranscript(text: string) { setTranscript(text); setDraft(null); setSaved(null); setError(''); }
  async function extract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setSaved(null);
    try { setDraft(content(await api.extract(expertId, transcript))); }
    catch (error) { setError(error instanceof Error ? error.message : 'Could not extract knowledge.'); }
    finally { setBusy(false); }
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError('');
    try { setSaved(await api.save(expertId, transcript, draft)); }
    catch (error) { setError(error instanceof Error ? error.message : 'Could not save knowledge.'); }
    finally { setBusy(false); }
  }
  return <main className="page-content interview-page" id="interview">
    <section className="hero"><p className="eyebrow">Expert Interview</p><h1>Capture the experience<br/>behind the diagnosis.</h1><p>Write an interview or record a conversation, extract the useful knowledge, then review and save it.</p></section>
    <div className="interview-grid">
      <section className="panel capture-panel"><div className="section-label">Capture knowledge</div>
        <form onSubmit={extract}>
          <label>Expert<select required value={expertId} disabled={busy || audioBusy} onChange={event => { setExpertId(event.target.value); setDraft(null); setSaved(null); }}>{!experts.length && <option value="">Loading experts…</option>}{experts.map(expert => <option key={expert.id} value={expert.id}>{expert.name} — {expert.specialty}</option>)}</select></label>
          <div className="capture-tabs" role="group" aria-label="Interview input method"><button type="button" className={mode === 'text' ? 'active' : ''} disabled={busy || audioBusy} onClick={() => setMode('text')}>Write interview</button><button type="button" className={mode === 'audio' ? 'active' : ''} disabled={busy || audioBusy} onClick={() => setMode('audio')}>Record or upload audio</button></div>
          {mode === 'audio' && <AudioCapture disabled={busy} onBusy={setAudioBusy} onTranscript={text => updateTranscript(transcript ? transcript + '\n\n' + text : text)}/>}
          <label>{mode === 'audio' ? 'Review the transcript' : 'Interview notes or transcript'}<textarea required rows={12} maxLength={20000} value={transcript} disabled={busy || audioBusy} onChange={event => updateTranscript(event.target.value)} placeholder="Describe the vehicle, the symptoms, what you checked, what you confirmed, and the practical lesson. You can paste a full conversation here."/></label>
          <p className="field-hint">{transcript.length.toLocaleString()} / 20,000 characters. Only information in the transcript will be extracted.</p>
          <button className="primary" disabled={busy || audioBusy || !expertId || !transcript.trim()}>{busy && !draft ? 'Extracting knowledge…' : 'Extract knowledge'}</button>
        </form>
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>
      <aside className="panel interview-guide"><div className="section-label">Questions to ask</div><h2>Find the practical lesson.</h2><ul><li>Which vehicle and engine were involved?</li><li>What symptoms appeared, and under which conditions?</li><li>Which checks helped you narrow down the cause?</li><li>What was actually confirmed, and what fixed it?</li><li>What would a younger mechanic miss?</li><li>What mistakes or safety precautions matter?</li></ul><p>All expert profiles are synthetic characters for this demonstration.</p></aside>
    </div>
    {draft && <section className="panel review-panel" id="review"><div className="section-label">Review extracted knowledge</div><h2>Check the details before saving.</h2><p className="field-hint">Edit anything that needs correcting. Empty fields mean the interview did not provide that information.</p>
      <form onSubmit={save}><fieldset disabled={busy || !!saved}>
        <label>Problem<input required value={draft.problem} maxLength={20000} onChange={event => setDraft({ ...draft, problem: event.target.value })}/></label>
        <div className="vehicle-fields">{([['vehicle_make', 'Vehicle make'], ['vehicle_model', 'Vehicle model'], ['engine_type', 'Engine type']] as const).map(([key, label]) => <label key={key}>{label}<input value={draft[key] || ''} onChange={event => setDraft({ ...draft, [key]: event.target.value || null })}/></label>)}</div>
        <div className="review-fields">{listFields.map(([key, label]) => <label key={key}>{label}<textarea rows={4} value={draft[key].join('\n')} onChange={event => setDraft({ ...draft, [key]: event.target.value.split('\n') })}/><small>One item per line</small></label>)}
          {([['confirmed_cause', 'Confirmed cause'], ['solution', 'Solution'], ['expert_insight', 'Practical expert insight']] as const).map(([key, label]) => <label key={key}>{label}<textarea rows={4} value={draft[key] || ''} onChange={event => setDraft({ ...draft, [key]: event.target.value || null })}/></label>)}
        </div>
        <button className="primary" disabled={busy || !!saved}>{busy ? 'Saving…' : saved ? 'Saved to knowledge base' : 'Add to knowledge base'}</button>
      </fieldset></form>
      {saved && <div className="saved-state" role="status"><h3>Knowledge saved.</h3><p>This interview is now stored in the JSON knowledge base and will be indexed on the next search.</p><button className="secondary" onClick={() => navigate('home')}>Ask a question</button><button className="text-button" onClick={() => { updateTranscript(''); setDraft(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>Capture another interview</button></div>}
    </section>}
  </main>;
}
