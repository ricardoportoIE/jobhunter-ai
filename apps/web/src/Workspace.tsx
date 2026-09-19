import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import { ImportJob, Inbox } from './Inbox';
import JobDetail from './JobDetail';
import ProfilePage from './ProfilePage';
import Tracker from './Tracker';
import type { Evidence, Fact, Profile } from './types';
import { ErrorState, Loading } from './ui';

async function loadProfile() {
  const [profile, facts, evidence] = await Promise.all([api<Profile>('/candidate/profile'), api<Fact[]>('/candidate/facts'), api<Evidence[]>('/candidate/evidence')]);
  return { profile, facts, evidence };
}

export default function Workspace() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || 'inbox');
  const [data, setData] = useState<{ profile: Profile; facts: Fact[]; evidence: Evidence[] } | null>(null);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setData(await loadProfile()); setError('');
  }, []);
  useEffect(() => { let active = true; loadProfile().then((value) => { if (active) setData(value); }).catch((reason: Error) => { if (active) setError(reason.message); }); return () => { active = false; }; }, []);
  useEffect(() => { const changed = () => { setRoute(window.location.hash.slice(1) || 'inbox'); }; window.addEventListener('hashchange', changed); return () => window.removeEventListener('hashchange', changed); }, []);
  useEffect(() => { document.getElementById('workspace-main')?.focus(); }, [route]);
  return <div className="app-layout"><a className="skip-link" href="#workspace-main">Ir para o conteúdo</a><aside className="sidebar"><a className="brand" href="#inbox"><span className="brand-mark" aria-hidden="true">jh</span><span>JobHunter <span className="brand-ai">AI</span></span></a><p className="eyebrow">ESPAÇO DE TRABALHO</p><nav aria-label="Navegação principal"><a href="#inbox" aria-current={route === 'inbox' ? 'page' : undefined}>Inbox de oportunidades</a><a href="#profile" aria-current={route === 'profile' ? 'page' : undefined}>Perfil e evidências</a><a href="#tracker" aria-current={route === 'tracker' ? 'page' : undefined}>Candidaturas</a><a href="#import" aria-current={route === 'import' ? 'page' : undefined}>Importar vaga</a></nav><p className="sidebar-note">Você decide cada passo.<br />Dados no ambiente local.</p></aside><main id="workspace-main" tabIndex={-1} className="app-main">{error ? <ErrorState error={error} retry={() => { void refresh().catch((reason: Error) => setError(reason.message)); }} /> : !data ? <Loading /> : route === 'profile' ? <ProfilePage {...data} refresh={refresh} /> : route === 'tracker' ? <Tracker /> : route === 'import' ? <ImportJob /> : route.startsWith('job/') ? <JobDetail key={route} id={route.slice(4)} profile={data.profile} facts={data.facts} /> : <Inbox />}</main></div>;
}
