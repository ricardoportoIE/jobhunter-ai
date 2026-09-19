import { useTask } from './useTask';
import { lines, optional, value } from './forms';
import { useState } from 'react';
import { api } from './api';
import type { Evidence, Fact, Profile } from './types';
import { Field } from './ui';

type Props = { profile: Profile; facts: Fact[]; evidence: Evidence[]; refresh: () => Promise<void> };
export default function ProfilePage({ profile, facts, evidence, refresh }: Props) {
  const task = useTask();
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [editingEvidence, setEditingEvidence] = useState<Evidence | null>(null);
  const [tab, setTab] = useState<'profile' | 'facts' | 'evidence'>('profile');
  return <>
    <div className="page-heading"><div><p className="eyebrow">SUA BASE FACTUAL</p><h1>Perfil e evidências</h1><p>Versão {profile.version} · {profile.status === 'reviewed' ? 'Revisado' : 'Revisão pendente'}</p></div></div>
    <nav className="tabs" aria-label="Seções do perfil">{(['profile', 'facts', 'evidence'] as const).map((key) => <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{{ profile: 'Perfil', facts: `Fatos (${facts.length})`, evidence: `Evidências (${evidence.length})` }[key]}</button>)}</nav>
    {task.feedback}
    {tab === 'profile' && <section className="panel"><h2>Direção da procura</h2><form key={profile.version} onSubmit={(event) => {
      event.preventDefault(); const data = new FormData(event.currentTarget);
      void task.run(async () => { await api('/candidate/profile', 'PATCH', { expected_version: profile.version, display_name: optional(data, 'display_name'), target_roles: lines(data, 'target_roles'), locations: lines(data, 'locations'), markets: data.getAll('markets'), work_modes: data.getAll('work_modes') }); await refresh(); });
    }}>
      <Field label="Nome de apresentação"><input name="display_name" defaultValue={profile.display_name ?? ''} maxLength={200} /></Field>
      <Field label="Funções pretendidas (separadas por vírgula)"><input name="target_roles" defaultValue={profile.target_roles.join(', ')} /></Field>
      <Field label="Localidades (separadas por vírgula)"><input name="locations" defaultValue={profile.locations.join(', ')} /></Field>
      <fieldset><legend>Mercados</legend>{['IE', 'GB'].map((market) => <label className="check" key={market}><input type="checkbox" name="markets" value={market} defaultChecked={profile.markets.includes(market)} />{market === 'IE' ? 'Irlanda' : 'Reino Unido'}</label>)}</fieldset>
      <fieldset><legend>Modalidades</legend>{['hybrid', 'remote', 'onsite'].map((mode) => <label className="check" key={mode}><input type="checkbox" name="work_modes" value={mode} defaultChecked={profile.work_modes.includes(mode)} />{{ hybrid: 'Híbrido', remote: 'Remoto', onsite: 'Presencial' }[mode]}</label>)}</fieldset>
      <button className="primary" disabled={task.busy}>Salvar perfil</button>
    </form><div className="review-callout"><p>Revise os fatos e suas fontes antes de publicar uma versão. Qualquer edição invalida análises anteriores.</p><button disabled={task.busy} onClick={() => { void task.run(async () => { await api('/candidate/profile/review', 'POST', { expected_version: profile.version }); await refresh(); }, 'Versão do perfil revisada e preservada.'); }}>Confirmar revisão e publicar versão</button></div></section>}
    {tab === 'evidence' && <div className="split"><section className="panel"><h2>{editingEvidence ? 'Editar evidência' : 'Nova evidência'}</h2><form key={editingEvidence?.id ?? 'new'} onSubmit={(event) => {
      event.preventDefault(); const data = new FormData(event.currentTarget);
      void task.run(async () => { await api(`/candidate/evidence${editingEvidence ? '/' + editingEvidence.id : ''}`, editingEvidence ? 'PATCH' : 'POST', { ...(editingEvidence ? { expected_version: editingEvidence.version } : {}), source_type: value(data, 'source_type'), source_ref: value(data, 'source_ref'), locator: value(data, 'locator'), content: value(data, 'content'), sensitivity: value(data, 'sensitivity'), review_confirmed: data.has('review_confirmed') }); setEditingEvidence(null); await refresh(); });
    }}>
      <Field label="Tipo de fonte"><select name="source_type" defaultValue={editingEvidence?.source_type ?? 'candidate_attestation'}>{Object.entries({ candidate_attestation: 'Declaração do candidato', cv: 'CV', repository: 'Repositório', certificate: 'Certificado', employment_record: 'Registro profissional', other: 'Outra' }).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
      <Field label="Referência da fonte"><input name="source_ref" required defaultValue={editingEvidence?.source_ref} placeholder="URL ou identificação do documento" /></Field>
      <Field label="Localizador"><input name="locator" required defaultValue={editingEvidence?.locator} placeholder="Página, seção ou arquivo" /></Field>
      <Field label="Trecho ou declaração"><textarea name="content" required rows={5} maxLength={10000} defaultValue={editingEvidence?.content} /></Field>
      <Sensitivity current={editingEvidence?.sensitivity} />
      <label className="check"><input type="checkbox" name="review_confirmed" />Revisei a fonte e o trecho registrado.</label>
      <button className="primary" disabled={task.busy}>Salvar evidência</button>{editingEvidence && <button type="button" onClick={() => setEditingEvidence(null)}>Cancelar edição</button>}
    </form></section><section className="panel"><h2>Evidências registradas</h2>{!evidence.length && <p>Comece registrando a fonte que sustenta um fato.</p>}{evidence.map((item) => <article className="record" key={item.id} id={`evidence-${item.id}`}><h3>{item.source_ref}</h3><p>{item.locator} · {item.reviewed_at ? 'Revisada' : 'Pendente'}</p><details><summary>Ver conteúdo e referência</summary><p className="preserve">{item.content}</p><p className="muted">Hash do trecho: {item.content_sha256}</p></details><div className="actions"><button onClick={() => setEditingEvidence(item)}>Editar evidência</button><button onClick={() => { void task.run(async () => { await api(`/candidate/evidence/${item.id}?expected_version=${item.version}`, 'DELETE'); await refresh(); }); }}>Remover evidência</button></div></article>)}</section></div>}
    {tab === 'facts' && <div className="split"><section className="panel"><h2>{editingFact ? 'Editar fato' : 'Novo fato'}</h2><form key={editingFact?.id ?? 'new'} onSubmit={(event) => {
      event.preventDefault(); const data = new FormData(event.currentTarget);
      void task.run(async () => { await api(`/candidate/facts${editingFact ? '/' + editingFact.id : ''}`, editingFact ? 'PATCH' : 'POST', { ...(editingFact ? { expected_version: editingFact.version } : {}), claim: value(data, 'claim'), category: value(data, 'category'), status: value(data, 'status'), sensitivity: value(data, 'sensitivity'), evidence_ids: data.getAll('evidence_ids'), allowed_uses: data.getAll('allowed_uses'), valid_from: optional(data, 'valid_from') ? new Date(value(data, 'valid_from')).toISOString() : null, valid_until: optional(data, 'valid_until') ? new Date(value(data, 'valid_until')).toISOString() : null, review_confirmed: data.has('review_confirmed') }); setEditingFact(null); await refresh(); });
    }}>
      <Field label="Afirmação factual"><textarea required name="claim" rows={4} maxLength={3000} defaultValue={editingFact?.claim} /></Field>
      <Field label="Categoria"><select name="category" defaultValue={editingFact?.category ?? 'skill'}>{Object.entries({ skill: 'Competência', experience: 'Experiência', education: 'Formação', project: 'Projeto', certification: 'Certificação', achievement: 'Realização', preference: 'Preferência', constraint: 'Restrição' }).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
      <Field label="Estado do fato"><select name="status" defaultValue={editingFact?.status ?? 'unverified'}><option value="unverified">Não verificado</option><option value="verified">Verificado</option><option value="expired">Expirado</option><option value="revoked">Revogado</option></select></Field>
      <fieldset><legend>Evidências de suporte</legend>{!evidence.length && <p>Registre uma evidência primeiro.</p>}{evidence.map((item) => <label className="check" key={item.id}><input name="evidence_ids" type="checkbox" value={item.id} defaultChecked={editingFact?.evidence_ids.includes(item.id)} />{item.source_ref} · {item.reviewed_at ? 'Revisada' : 'Pendente'}</label>)}</fieldset>
      <fieldset><legend>Usos permitidos</legend>{Object.entries({ matching: 'Matching', cv: 'CV', cover_letter: 'Carta', application_form: 'Formulário' }).map(([key, label]) => <label className="check" key={key}><input name="allowed_uses" type="checkbox" value={key} defaultChecked={editingFact?.allowed_uses.includes(key)} />{label}</label>)}</fieldset>
      <div className="form-grid"><Field label="Válido desde (UTC)"><input type="date" name="valid_from" defaultValue={editingFact?.valid_from?.slice(0, 10)} /></Field><Field label="Válido até (UTC, exclusivo)"><input type="date" name="valid_until" defaultValue={editingFact?.valid_until?.slice(0, 10)} /></Field></div>
      <Sensitivity current={editingFact?.sensitivity} /><label className="check"><input type="checkbox" name="review_confirmed" />Confirmo a revisão deste fato e suas evidências.</label>
      <button className="primary" disabled={task.busy}>Salvar fato</button>{editingFact && <button type="button" onClick={() => setEditingFact(null)}>Cancelar edição</button>}
    </form></section><section className="panel"><h2>Fatos registrados</h2>{!facts.length && <p>Nenhum fato cadastrado.</p>}{facts.map((item) => <article className="record" key={item.id}><h3>{item.claim}</h3><p>{item.status} · {item.allowed_uses.join(', ') || 'Sem usos autorizados'}</p><p>{item.evidence_ids.length} evidência(s)</p><div className="actions"><button onClick={() => setEditingFact(item)}>Editar fato</button><button onClick={() => { void task.run(async () => { await api(`/candidate/facts/${item.id}?expected_version=${item.version}`, 'DELETE'); await refresh(); }); }}>Remover fato</button></div></article>)}</section></div>}
  </>;
}
function Sensitivity({ current }: { current?: string }) { return <Field label="Sensibilidade"><select name="sensitivity" defaultValue={current ?? 'private'}><option value="public">Público</option><option value="private">Privado</option><option value="sensitive">Sensível</option></select></Field>; }
