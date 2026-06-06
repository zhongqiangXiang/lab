import { useEffect, useState } from 'react';

type HelloResponse = {
  message: string;
};

type RequestState =
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; error: string };

async function fetchHello(signal: AbortSignal): Promise<HelloResponse> {
  const response = await fetch('/api/hello', { signal });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }

  return response.json() as Promise<HelloResponse>;
}

export default function App() {
  const [requestState, setRequestState] = useState<RequestState>({ status: 'loading' });

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

  return (
    <main className="page-shell">
      <section className="hello-panel" aria-live="polite">
        <p className="eyebrow">React + Spring Boot</p>
        <h1>Hello Demo</h1>

        {requestState.status === 'loading' && (
          <p className="status-message">Loading hello message from the backend...</p>
        )}

        {requestState.status === 'success' && (
          <p className="hello-message" data-testid="hello-message">
            {requestState.message}
          </p>
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
