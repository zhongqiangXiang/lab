import { useEffect, useState } from 'react';
import { fetchHello } from './helloApi';

type RequestState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; error: string };

export default function App() {
  const [requestState, setRequestState] = useState<RequestState>({ status: 'idle' });

  useEffect(() => {
    const controller = new AbortController();

    setRequestState({ status: 'loading' });

    fetchHello(controller.signal)
      .then((data) => {
        setRequestState({ status: 'success', message: data.message });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        const message = error instanceof Error ? error.message : 'Unknown request failure';
        setRequestState({ status: 'error', error: message });
      });

    return () => {
      controller.abort();
    };
  }, []);

  const retry = () => {
    const controller = new AbortController();

    setRequestState({ status: 'loading' });

    fetchHello(controller.signal)
      .then((data) => {
        setRequestState({ status: 'success', message: data.message });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : 'Unknown request failure';
        setRequestState({ status: 'error', error: message });
      });
  };

  return (
    <main className="page-shell">
      <section className="hello-panel" aria-live="polite">
        <div className="panel-header">
          <p className="eyebrow">React + Spring Boot</p>
          <h1>Hello World Demo</h1>
          <p className="intro">
            Frontend page at <code>/hello-world</code>, backend API at <code>/api/hello</code>.
          </p>
        </div>

        <div className="api-card">
          <div>
            <span className="label">GET</span>
            <code>/api/hello</code>
          </div>

          <button type="button" onClick={retry} disabled={requestState.status === 'loading'}>
            Retry
          </button>
        </div>

        {requestState.status === 'loading' && (
          <p className="status-message">Loading hello message from the backend...</p>
        )}

        {requestState.status === 'success' && (
          <p className="hello-message" data-testid="hello-message">
            {requestState.message}
          </p>
        )}

        {requestState.status === 'idle' && (
          <p className="status-message">Ready to load the backend hello message.</p>
        )}

        {requestState.status === 'error' && (
          <div className="error-box" role="alert">
            <strong>Could not load the backend message.</strong>
            <span>{requestState.error}</span>
          </div>
        )}
      </section>
    </main>
  );
}
