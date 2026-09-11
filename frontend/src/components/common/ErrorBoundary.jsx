import React from 'react';

/**
 * ErrorBoundary — catches render/lifecycle errors in its subtree so a single
 * component throwing does not unmount the whole React tree (which left the
 * app on a blank page after signin). Renders a fallback UI and logs the error.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary] Render error caught:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const message = this.state.error?.message || 'Something went wrong while rendering.';
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-4">
          <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
            <h1 className="text-lg font-semibold mb-2 text-rose-400">Something went wrong</h1>
            <p className="text-sm text-slate-400 mb-4">{message}</p>
            {process.env.NODE_ENV !== 'production' && this.state.errorInfo && (
              <pre className="text-left text-xs text-slate-500 bg-slate-950 border border-slate-800 rounded p-3 mb-4 overflow-x-auto whitespace-pre-wrap">
                {this.state.error?.stack}
              </pre>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium"
              >
                Reload
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                className="px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}