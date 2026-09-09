import { Navigate } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";
import { homePath } from "../api";
import { startHostedUiLogin, startHostedUiLogout } from "../auth";
import { useSpa } from "../spa";

export default function Landing() {
  const { config, signedIn, me } = useSpa();
  const canLogin = Boolean(config.userPoolClientId && config.cognitoDomain);

  if (signedIn && me) {
    return <Navigate to={homePath(me)} replace />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">TurboImmi</p>
        <h1 className="mt-2 text-3xl font-semibold">Educational H-1B helper</h1>
        <p className="mt-4 text-slate-700">{disclaimer.short}</p>
        <p className="mt-2 text-sm text-slate-600">{disclaimer.scoreNotOdds}</p>
        <p className="mt-6 text-sm">
          <a className="underline" href={disclaimer.tosPath}>
            Terms of Service
          </a>
          {" · "}
          <a className="underline" href={disclaimer.privacyPath}>
            Privacy Policy
          </a>
          <span className="text-slate-500"> (placeholder pages on Day 4)</span>
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          {canLogin && !signedIn ? (
            <button
              type="button"
              className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
              onClick={() => void startHostedUiLogin(config)}
            >
              Sign in
            </button>
          ) : null}
          {signedIn ? (
            <button
              type="button"
              className="rounded-md border border-slate-300 px-4 py-2 text-sm"
              onClick={() => startHostedUiLogout(config)}
            >
              Sign out
            </button>
          ) : null}
        </div>
        <p className="mt-4 text-sm text-slate-600">
          {signedIn
            ? "Loading your role…"
            : canLogin
              ? "Sign in to choose a role and save a profile. Role cannot be switched later."
              : "Cognito env not set yet (fill VITE_COGNITO_* after deploy for local login)."}
        </p>
      </div>
    </main>
  );
}
