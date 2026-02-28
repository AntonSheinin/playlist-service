import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";

export function LoginPage() {
  const { admin, loading, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login({ username, password });
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Connection error. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // If already authenticated, redirect to dashboard
  if (!loading && admin) {
    return <Navigate to="/" replace />;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-8">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_15%_10%,#dbeafe,transparent_40%),radial-gradient(circle_at_85%_15%,#cffafe,transparent_35%),linear-gradient(#f8fafc,#f8fafc)]" />
      <Card className="w-full max-w-md p-8 shadow-panel">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100">
            <img src="/media/rutv-logo.png" alt="" className="h-8 w-8 object-contain" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Playlist Service</h1>
          <p className="mt-2 text-slate-600">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            id="username"
            label="Username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <Input
            id="password"
            label="Password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          )}

          <Button
            type="submit"
            disabled={submitting}
            loading={submitting}
            className="w-full"
          >
            {submitting ? "Signing in..." : "Sign In"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
