import React, { useState, type FormEvent } from 'react';
import { sampleAnswer } from './data/knowledge';
import { api, type ChatResponse } from './api';

function CarWatermark() {
  return <svg className="car-watermark" viewBox="0 0 1100 320" aria-hidden="true"><path className="car-body" d="M30 232 76 177q21-25 68-37l171-39 130-77q39-23 87-23h174q55 0 98 31l105 76 127 35q38 11 65 41l35 43 22 20v49H30z"/><path className="car-window" d="m356 111 111-66q15-9 37-9h68v75zm235-75h49q48 0 83 28l84 47H591z"/><path className="car-line" d="M75 225h910M43 254h66m831 0h82"/><circle className="car-wheel" cx="246" cy="263" r="57"/><circle className="car-hub" cx="246" cy="263" r="22"/><circle className="car-wheel" cx="857" cy="263" r="57"/><circle className="car-hub" cx="857" cy="263" r="22"/></svg>;
}
function App() {
  const [question, setQuestion] = useState('');
  const [submitted, setSubmitted] = useState('');
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState<'gap' | 'expert' | null>(null);
  const [sent, setSent] = useState(false);
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const answer = sampleAnswer;
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || loading) return;
    const text = question.trim();
    setSubmitted(text); setResult(null); setError(''); setLoading(true); setHelpful(null);
    try {
      setResult(await api.ask(text));
      setQuestion('');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Could not answer the question. Please try again.');
    } finally {
      setLoading(false);
    }
  }
  function send(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSent(true); }
  function openFeedback(kind: 'gap' | 'expert') { setFeedback(kind); setSent(false); }
  return <div className="app-shell">
    <CarWatermark />
    <header className="topbar">
      <a className="brand" href="#home" aria-label="AutoLegacy home"><img src="/autolegacy-logo.png" alt="AutoLegacy"/></a>
      <nav className={menuOpen ? 'open' : ''} aria-label="Main navigation"><a href="#home" onClick={() => setMenuOpen(false)}>Explore</a><a href="#questions" onClick={() => setMenuOpen(false)}>Questions</a><a href="#experts" onClick={() => setMenuOpen(false)}>Experts</a><a href="#about" onClick={() => setMenuOpen(false)}>About</a></nav>
      <button className="menu-toggle" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><span/><span/><span/></button>
    </header>
    <main id="home" className="page-content">
      <section className="hero">
        <p className="eyebrow">The Garage Handbook</p>
        <h1>Decades of know-how,<br/>ready when you need it.</h1>
        <form className="search-form" onSubmit={ask}>
          <label className="sr-only" htmlFor="question">Search a car question, part, or repair</label>
          <input id="question" value={question} onChange={e => setQuestion(e.target.value)} disabled={loading} maxLength={20000} placeholder="Search a car question, part, or repair..."/>
          <button aria-label="Ask question" disabled={loading}><svg viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg></button>
        </form>
      </section>
      {(loading || error) && <div className="notice" role={error ? 'alert' : 'status'}><span>{loading ? 'Searching knowledge and preparing your answer…' : error}</span>{error && <button onClick={() => setError('')} aria-label="Dismiss">×</button>}</div>}
      <div className="content-grid">
        <article className="panel answer-card" id="questions">
          <div className="section-label">Question &amp; Answer</div>
          <h2>{submitted || answer.question}</h2>{!submitted && <p className="answer-meta">{answer.summary} · {answer.readTime}</p>}<div className="divider"/>
          {result ? <div aria-live="polite"><p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, color: '#687a84' }}>{result.answer}</p></div>
            : submitted ? <p className="answer-meta" role="status">{loading ? 'Searching knowledge…' : 'Your question is still in the search box. Please try again.'}</p>
            : <ol className="steps-list">{answer.steps.map((step, i) => <li key={step.title}><span className="step-number">{i + 1}</span><div><h3>{step.title}</h3><p>{step.detail}</p></div></li>)}</ol>}
          <div className="helpful-row"><span>{helpful === null ? 'Was this helpful?' : helpful ? 'Thanks for your feedback.' : 'Thanks — tell us what was missing.'}</span><div><button className={helpful === true ? 'selected' : ''} onClick={() => setHelpful(true)}>Yes</button><button className={helpful === false ? 'selected' : ''} onClick={() => {setHelpful(false);openFeedback('gap');}}>Not quite</button></div></div>
        </article>
        <aside className="side-column">
          <section className="panel expert-card" id="experts"><div className="section-label">Contributed by</div>{answer.experts.map(expert => <div className="expert-entry" key={expert.name}><div className="avatar">{expert.name.split(' ').map(n => n[0]).join('')}</div><div><h3>{expert.name}</h3><p>{expert.specialty} · {expert.experience}</p><p className="added">Added {expert.added}</p></div><span className="verified">✓ Expert</span></div>)}</section>
          <section className="panel documents-card"><div className="section-label">Related documents</div><ul>{answer.documents.map(doc => <li key={doc.title}><a href="#documents" onClick={e => e.preventDefault()}><span className="doc-arrow">↗</span><span>{doc.title}</span><small>{doc.type}</small></a></li>)}</ul><div className="feedback-links" id="about"><button onClick={() => openFeedback('gap')}>Report a knowledge gap <span>→</span></button><button onClick={() => openFeedback('expert')}>Ask an expert to update <span>→</span></button></div></section>
        </aside>
      </div>
    </main>
    {feedback && <div className="backdrop" onMouseDown={e => {if (e.target === e.currentTarget) setFeedback(null);}}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="feedback-title"><button className="close" onClick={() => setFeedback(null)} aria-label="Close">×</button>{sent ? <div className="success"><span>✓</span><h2>Thanks for helping keep AutoLegacy current.</h2><p>Your note is saved in this demo and can be connected to your backend.</p><button className="primary" onClick={() => setFeedback(null)}>Done</button></div> : <><p className="eyebrow">{feedback === 'gap' ? 'Help improve this answer' : 'Expert update request'}</p><h2 id="feedback-title">{feedback === 'gap' ? 'What knowledge is missing?' : 'What should the expert review?'}</h2><p className="modal-intro">Your feedback helps keep automotive knowledge useful and up to date.</p><form onSubmit={send}><label>Topic<select defaultValue={feedback === 'gap' ? 'Missing step or detail' : 'Updated information'}><option>Missing step or detail</option><option>Vehicle-specific question</option><option>Possible correction</option><option>Updated information</option></select></label><label>Details<textarea required rows={4} placeholder="Describe the gap or update you’d like to see..."/></label><label>Email (optional)<input type="email" placeholder="you@example.com"/></label><button className="primary">Send feedback</button></form></>}</section></div>}
  </div>;
}
export default App;
