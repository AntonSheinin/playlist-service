import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center px-4 py-8">
          <Card className="w-full max-w-2xl p-8">
            <h1 className="mb-4 text-xl font-semibold text-rose-600">Something went wrong</h1>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm text-slate-800">
              {this.state.error.message}
              {"\n\n"}
              {this.state.error.stack}
            </pre>
            <Button
              onClick={() => { this.setState({ error: null }); window.location.href = "/"; }}
              className="mt-4"
            >
              Go to Dashboard
            </Button>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}
