import { useEffect, useState } from 'react';
import { isWorkspaceReady } from './health';

type Connection = 'checking' | 'ready' | 'unavailable';

const messages = {
  checking: { title: 'Verificando conexão', detail: 'Conectando ao ambiente local…' },
  ready: { title: 'Ambiente conectado', detail: 'A API e o banco de dados estão respondendo.' },
  unavailable: { title: 'Conexão indisponível', detail: 'Confira os serviços locais e tente novamente.' },
};

export default function App() {
  const [connection, setConnection] = useState<Connection>('checking');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setConnection('unavailable');
    }, 8000);

    isWorkspaceReady(controller.signal)
      .then((ready) => {
        if (!controller.signal.aborted) setConnection(ready ? 'ready' : 'unavailable');
      })
      .catch(() => {
        if (!controller.signal.aborted) setConnection('unavailable');
      })
      .finally(() => window.clearTimeout(timeout));

    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [attempt]);

  return (
    <div className="workspace">
      <header className="topbar">
        <a className="brand" href="/" aria-label="JobHunter AI, início">
          <span className="brand-mark" aria-hidden="true">jh</span>
          <span>JobHunter <span className="brand-ai">AI</span></span>
        </a>
        <span className="local-label"><span aria-hidden="true" /> Ambiente local</span>
      </header>

      <main id="main-content">
        <div className="intro">
          <p className="eyebrow">SEU ESPAÇO DE TRABALHO</p>
          <h1>Uma busca de emprego<br />baseada em evidências.</h1>
          <p className="lead">Organize seu perfil, entenda as oportunidades e prepare
            candidaturas com decisões sob seu controle.</p>
        </div>

        <section className="connection-panel" aria-labelledby="connection-heading">
          <div className={`connection-icon ${connection}`} aria-hidden="true">
            {connection === 'ready' ? '✓' : connection === 'checking' ? '·' : '!'}
          </div>
          <div className="connection-copy" role="status" aria-live="polite">
            <h2 id="connection-heading">{messages[connection].title}</h2>
            <p>{messages[connection].detail}</p>
          </div>
          <button disabled={connection === 'checking'} onClick={() => {
            setConnection('checking');
            setAttempt((value) => value + 1);
          }}>Verificar conexão <span aria-hidden="true">↗</span></button>
        </section>

        <section className="foundation" aria-labelledby="foundation-heading">
          <div className="section-heading">
            <h2 id="foundation-heading">A base está tomando forma</h2>
            <span className="phase-label">P1-01</span>
          </div>
          <ol className="steps">
            <li><span className="step-number current">01</span><div><h3>Ambiente local</h3>
              <p>Interface, API e banco conectados em um único espaço.</p>
              <span className="step-tag">Etapa atual</span></div></li>
            <li><span className="step-number">02</span><div><h3>Acesso e perfil</h3>
              <p>Sessão autenticada e fatos ligados às suas evidências.</p>
              <span className="step-tag muted">Próximas entregas</span></div></li>
            <li><span className="step-number">03</span><div><h3>Primeira oportunidade</h3>
              <p>Importação de vaga, análise de compatibilidade e lacunas.</p>
              <span className="step-tag muted">Planejado</span></div></li>
          </ol>
        </section>

        <aside className="notice">
          <span aria-hidden="true">↳</span>
          <p>Esta é a estrutura inicial do projeto. Seu perfil privado ainda não está
            disponível na aplicação e nenhuma candidatura é enviada.</p>
        </aside>
      </main>
      <footer><span>JobHunter AI <span className="footer-separator">/</span> Desenvolvimento local</span>
        <a href="/api/docs">Documentação da API <span aria-hidden="true">↗</span></a></footer>
    </div>
  );
}
