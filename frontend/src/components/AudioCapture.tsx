import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';

export function AudioCapture({ onTranscript, onBusy, disabled }: { onTranscript: (text: string) => void; onBusy: (busy: boolean) => void; disabled: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<number>();
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => {
    alive.current = false;
    window.clearInterval(timer.current);
    if (recorder.current?.state === 'recording') recorder.current.stop();
    stream.current?.getTracks().forEach(track => track.stop());
    onBusy(false);
  }; }, []);
  useEffect(() => {
    if (!file) { setUrl(''); return; }
    const next = URL.createObjectURL(file); setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  function choose(next?: File) {
    if (!next) return;
    if (next.size > 25_000_000) { setError('Choose audio smaller than 25 MB.'); return; }
    setFile(next); setError('');
  }
  async function start() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('Recording is not supported in this browser. Upload an audio file instead.'); return;
    }
    setBusy(true); onBusy(true); setError('');
    try {
      const audio = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!alive.current) { audio.getTracks().forEach(track => track.stop()); return; }
      stream.current = audio;
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
      const next = new MediaRecorder(audio, mimeType ? { mimeType } : undefined);
      const chunks: BlobPart[] = [];
      recorder.current = next;
      next.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      next.onstop = () => {
        window.clearInterval(timer.current);
        audio.getTracks().forEach(track => track.stop());
        if (!alive.current) return;
        const type = next.mimeType || 'audio/webm';
        const extension = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
        choose(new File(chunks, `expert-interview.${extension}`, { type }));
        setRecording(false); setBusy(false); onBusy(false);
      };
      next.onerror = () => { setError('The recording failed. Try again or upload audio.'); if (next.state === 'recording') next.stop(); };
      setSeconds(0); setRecording(true); next.start(1000);
      const started = Date.now();
      timer.current = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - started) / 1000); setSeconds(elapsed);
        if (elapsed >= 300 && next.state === 'recording') next.stop();
      }, 1000);
    } catch {
      stream.current?.getTracks().forEach(track => track.stop());
      setError('Microphone access was unavailable. Allow microphone access or upload an audio file instead.');
      setBusy(false); onBusy(false);
    }
  }
  async function transcribe() {
    if (!file) return;
    setBusy(true); onBusy(true); setError('');
    try {
      const response = await api.transcribe(file);
      if (alive.current) onTranscript(response.text);
    } catch (error) { if (alive.current) setError(error instanceof Error ? error.message : 'Could not transcribe audio.'); }
    finally { if (alive.current) { setBusy(false); onBusy(false); } }
  }
  return <section className="audio-capture" aria-label="Audio interview">
    <div className="capture-actions"><button type="button" className={recording ? 'record-button recording' : 'record-button'} disabled={disabled || (busy && !recording)} onClick={() => recording ? recorder.current?.stop() : void start()}>{recording ? `Stop recording (${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')})` : 'Record interview'}</button>
      <label className="upload-label">Or upload audio<input aria-label="Upload interview audio" type="file" accept=".wav,.mp3,.m4a,.webm,.ogg,.mp4" disabled={disabled || busy} onChange={event => choose(event.target.files?.[0])}/></label>
    </div>
    <p className="field-hint">Up to five minutes, 25 MB. WAV, MP3, M4A, WebM or Ogg. Audio is transcribed locally and the temporary upload is removed.</p>
    {url && <><audio controls src={url} aria-label="Interview recording preview"/><p className="field-hint">{file?.name}</p></>}
    {file && !recording && <button type="button" className="secondary" disabled={disabled || busy} onClick={transcribe}>{busy ? 'Transcribing audio…' : 'Transcribe recording'}</button>}
    {busy && !recording && <p role="status" className="field-hint">Preparing audio. The first transcription may need to download the local speech model.</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
