import React from 'react';

type Props = { children: React.ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', background: '#0a0a0f',
          color: '#ff6b6b', fontFamily: 'monospace', padding: 32, gap: 16,
        }}>
          <h2 style={{ color: '#ff6b6b', margin: 0 }}>React Render Error</h2>
          <pre style={{
            background: '#1a0a0a', padding: 20, borderRadius: 8, maxWidth: 800,
            whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13,
            border: '1px solid #ff3333', color: '#ffaaaa',
          }}>
            {this.state.error.message}{'\n\n'}{this.state.error.stack}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ padding: '8px 24px', background: '#333', color: '#fff', border: '1px solid #555', borderRadius: 6, cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
