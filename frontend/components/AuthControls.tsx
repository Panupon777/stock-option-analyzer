'use client';
import { useEffect, useState, FormEvent } from 'react';
import api from '@/lib/api';
export default function AuthControls() {
  const [signedIn, setSignedIn] = useState(false);
  const [open, setOpen] = useState(false);
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setSignedIn(!!localStorage.getItem('token')); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const response = await api.post(register ? '/api/auth/register' : '/api/auth/login', {
        email: form.get('email'), password: form.get('password'), ...(register ? { name: form.get('name') } : {})
      });
      localStorage.setItem('token', response.data.token);
      window.location.reload();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Login failed. Please check your details.');
    } finally { setBusy(false); }
  }
  if (signedIn) return <button className="btn btn-secondary" onClick={() => { localStorage.removeItem('token'); window.location.reload(); }}>Log out</button>;
  return <>
    <button className="btn btn-secondary" onClick={() => setOpen(true)}>Log in</button>
    {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section role="dialog" aria-modal="true" aria-label={register ? 'Sign up' : 'Log in'} className="card w-full max-w-sm">
        <h2 className="text-xl mb-4">{register ? 'Sign up' : 'Log in'}</h2>
        <form onSubmit={submit} className="flex flex-col gap-3">
          {register && <input name="name" aria-label="Name" placeholder="Name" required className="input-field" />}
          <input name="email" type="email" aria-label="Email" placeholder="Email" required autoComplete="email" className="input-field" />
          <input name="password" type="password" aria-label="Password" placeholder="Password" minLength={6} maxLength={72} required autoComplete={register ? 'new-password' : 'current-password'} className="input-field" />
          {error && <p role="alert" className="text-red-400">{error}</p>}
          <button disabled={busy} className="btn btn-primary">{busy ? 'Processing...' : register ? 'Sign up' : 'Log in'}</button>
        </form>
        <div className="flex justify-between mt-4">
          <button className="btn btn-secondary" onClick={() => { setRegister(!register); setError(''); }}>{register ? 'Log in' : 'Sign up'}</button>
          <button className="btn btn-secondary" onClick={() => setOpen(false)}>Close</button>
        </div>
      </section>
    </div>}
  </>;
}
