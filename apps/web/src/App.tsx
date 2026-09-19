import { useEffect, useState, type FormEvent } from 'react';
import Foundation from './Foundation';
import { api, ApiError, setSession, type Session } from './api';

export default function App() {
  const [session, updateSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Session>('/session').then((value) => { setSession(value); updateSession(value); })
      .catch((reason: unknown) => {
        if (!(reason instanceof ApiError && reason.status === 401)) setError('Serviço indisponível. Tente entrar novamente.');
      }).finally(() => setLoading(false));
  }, []);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const value = await api<Session>('/session', 'POST', { username: form.get('username'), password: form.get('password') });
      setSession(value); updateSession(value);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Erro ao entrar.'); }
    finally { setBusy(false); }
  }
  if (loading) return <main className="login"><p role="status">Verificando sessão…</p></main>;
  if (!session) return <main className="login">
    <p className="eyebrow">JOBHUNTER AI · LOCAL</p><h1>Seu próximo passo<br />começa aqui.</h1>
    <p>Entre para organizar seu perfil e avaliar oportunidades com evidências.</p>
    <form onSubmit={(event) => { void login(event); }}>
      <label>Utilizador<input name="username" autoComplete="username" required defaultValue="local" /></label>
      <label>Senha<input name="password" type="password" autoComplete="current-password" required maxLength={256} /></label>
      {error && <p role="alert">{error}</p>}
      <button disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button>
    </form>
    <p className="muted">Use a credencial criada na configuração local.</p>
  </main>;
  return <><div className="session-bar"><span>Sessão local ativa</span><button onClick={() => {
    void api('/session', 'DELETE').then(() => { setSession(null); updateSession(null); }).catch(() => setError('Não foi possível sair. Tente novamente.'));
  }}>Sair</button>{error && <span role="alert">{error}</span>}</div><Foundation /></>;
}
