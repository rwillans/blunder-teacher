import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      error: null,
      stack: "",
    };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    this.setState({
      stack: info?.componentStack || "",
    });
  }

  render() {
    const { error, stack } = this.state;

    if (!error) {
      return this.props.children;
    }

    return (
      <main className="page-shell page-shell-single">
        <section className="empty-state error-state">
          <span className="eyebrow">Runtime Error</span>
          <h3>The React viewer crashed while rendering</h3>
          <p>{error.message || "Unknown error"}</p>
          {stack ? <pre className="error-stack">{stack.trim()}</pre> : null}
          <p>
            The page stays up so you can see the real error instead of landing on a blank screen.
          </p>
        </section>
      </main>
    );
  }
}
