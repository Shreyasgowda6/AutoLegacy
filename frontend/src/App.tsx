import React, { useEffect, useRef, useState, type FormEvent } from 'react';
import { sampleAnswer } from './data/knowledge';
import { api, type ChatResponse, type Expert } from './api';
import { FeedbackModal } from './components/FeedbackModal';
import { InterviewPage } from './components/InterviewPage';

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
  const [helpful, setHelpful] = useState<boolean | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [page, setPage] = useState(location.hash === '#interview' ? 'interview' : 'home');
  const pageRef = useRef(page);
  pageRef.current = page;
  const [experts, setExperts] = useState<Expert[]>([]);
  const [expertsError, setExpertsError] = useState('');
  const [selectedExpert, setSelectedExpert] = useState('');
  const answer = sampleAnswer;
  function scrollToSection(target: string) {
    if (target === 'home' || target === 'interview') { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    const element = document.getElementById(target);
    const header = document.querySelector('header')?.getBoundingClientRect().height || 76;
    if (element) window.scrollTo({ top: Math.max(0, element.getBoundingClientRect().top + window.scrollY - header - 20), behavior: 'smooth' });
  }
  function navigate(target: string) {
    history.pushState(null, '', `#${target}`);
    setPage(target === 'interview' ? 'interview' : 'home'); setMenuOpen(false);
    requestAnimationFrame(() => scrollToSection(target));
  }
  function loadExperts() {
    setExpertsError('');
    api.experts().then(setExperts).catch(error => setExpertsError(error instanceof Error ? error.message : 'Could not load experts.'));
  }
  useEffect(() => {
    loadExperts();
    const sync = () => { setPage(location.hash === '#interview' ? 'interview' : 'home'); setMenuOpen(false); requestAnimationFrame(() => scrollToSection(location.hash.slice(1) || 'home')); };
    window.addEventListener('hashchange', sync); window.addEventListener('popstate', sync);
    return () => { window.removeEventListener('hashchange', sync); window.removeEventListener('popstate', sync); };
  }, []);
  useEffect(() => { requestAnimationFrame(() => scrollToSection(location.hash.slice(1) || 'home')); }, [page]);
  function interview(expert: Expert) { setSelectedExpert(expert.id); navigate('interview'); }
  const contributors = result?.sources.map(source => experts.find(expert => expert.id === source.expert_id)).filter((expert): expert is Expert => !!expert) || [];
  const shownExperts = [...new Map(contributors.map(expert => [expert.id, expert])).values()];
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || loading) return;
    const text = question.trim();
    setSubmitted(text); setResult(null); setError(''); setLoading(true); setHelpful(null);
    try {
      const response = await api.ask(text);
      setResult(response.insufficient_evidence ? { ...response, answer: 'No information available.', sources: [] } : response);
      if (response.insufficient_evidence && pageRef.current === 'home') openFeedback('gap');
      setQuestion('');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Could not answer the question. Please try again.');
    } finally {
      setLoading(false);
    }
  }
  function openFeedback(kind: 'gap' | 'expert') { setFeedback(kind); }
  return <div className="app-shell">
    <CarWatermark />
    <header className="topbar">
      <a className="brand" href="#home" aria-label="AutoLegacy home" onClick={event => { event.preventDefault(); navigate('home'); }}><img src="/autolegacy-logo.png" alt="AutoLegacy"/></a>
      <nav className={menuOpen ? 'open' : ''} aria-label="Main navigation">{[['home', 'Explore'], ['questions', 'Questions'], ['experts', 'Experts'], ['interview', 'Expert Interview'], ['about', 'About']].map(([target, label]) => <a key={target} href={`#${target}`} onClick={event => { event.preventDefault(); navigate(target); }}>{label}</a>)}</nav>
      <button className="menu-toggle" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><span/><span/><span/></button>
    </header>
    {page === 'interview' ? <InterviewPage experts={experts} selectedExpert={selectedExpert} navigate={navigate}/> : <main id="home" className="page-content">
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
          <section className="panel expert-card"><div className="section-label">{result?.insufficient_evidence ? 'Expert network' : 'Contributed by'}</div>{shownExperts.length ? shownExperts.map(expert => <div className="expert-entry" key={expert.id}><div className="avatar">{expert.name.split(' ').map(n => n[0]).join('')}</div><div><h3>{expert.name}</h3><p>{expert.specialty} · {expert.experience_years} years</p></div><span className="verified">Demo expert</span></div>) : answer.experts.map(expert => <div className="expert-entry" key={expert.name}><div className="avatar">{expert.name.split(' ').map(n => n[0]).join('')}</div><div><h3>{expert.name}</h3><p>{expert.specialty} · {expert.experience}</p><p className="added">Added {expert.added}</p></div><span className="verified">✓ Expert</span></div>)}<a className="directory-link" href="#experts" onClick={event => { event.preventDefault(); navigate('experts'); }}>View all {experts.length || ''} experts</a></section>
          <section className="panel documents-card"><div className="section-label">Related documents</div><ul>{answer.documents.map(doc => <li key={doc.title}><a href="#documents" onClick={e => e.preventDefault()}><span className="doc-arrow">↗</span><span>{doc.title}</span><small>{doc.type}</small></a></li>)}</ul><div className="feedback-links" id="about"><button onClick={() => openFeedback('gap')}>Report a knowledge gap <span>→</span></button><button onClick={() => openFeedback('expert')}>Ask an expert to update <span>→</span></button></div></section>
        </aside>
      </div>
      <section id="experts" className="expert-directory"><div className="section-label">Our expert network</div><h2>Meet the people behind the know-how.</h2><p className="directory-intro">Explore all {experts.length || ''} synthetic expert profiles and capture their practical knowledge in an interview.</p>
        {expertsError && <p className="form-error" role="alert">{expertsError} <button className="text-button" onClick={loadExperts}>Retry</button></p>}
        {!experts.length && !expertsError && <p role="status">Loading experts…</p>}
        <div className="expert-grid">{experts.map(expert => <article className="panel directory-card" key={expert.id}><div className="expert-card-heading"><div className="avatar">{expert.name.split(' ').map(n => n[0]).join('')}</div><span className="synthetic-label">Synthetic profile</span></div><h3>{expert.name}</h3><p className="expert-specialty">{expert.specialty} · {expert.experience_years} years</p><p>{expert.bio}</p><button className="secondary" onClick={() => interview(expert)}>Interview this expert</button></article>)}</div>
      </section>
    </main>}
    {feedback && <FeedbackModal kind={feedback} question={submitted} close={() => setFeedback(null)}/>}
  </div>;
}
export default App;
