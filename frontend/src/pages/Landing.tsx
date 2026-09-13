import { Navigate } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";
import { homePath } from "../api";
import { startHostedUiLogin, startHostedUiLogout } from "../auth";
import SiteFooter from "../components/SiteFooter";
import { useSpa } from "../spa";

export default function Landing() {
  const { config, signedIn, me } = useSpa();
  const canLogin = Boolean(config.userPoolClientId && config.cognitoDomain);

  if (signedIn && me) {
    return <Navigate to={homePath(me)} replace />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">TurboImmi</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">Educational H-1B helper</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-700">
          Organize an H-1B packet the way TurboTax organizes a return: confirm what the documents
          say, answer a short intent interview, then ask a licensed attorney to review before anyone
          files.
        </p>
        <p className="mt-3 text-sm text-slate-600">{disclaimer.short}</p>
        <p className="mt-1 text-sm text-slate-600">{disclaimer.scoreNotOdds}</p>
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
              ? "Sign in, then choose Applicant or Attorney once. That role cannot be switched later."
              : "Cognito env not set yet (fill VITE_COGNITO_* after deploy for local login)."}
        </p>
        <ol className="mt-10 grid gap-4 sm:grid-cols-3">
          <li className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold">1. Confirm documents</p>
            <p className="mt-2 text-sm text-slate-600">
              Passport and offer letter can be typed by hand, or you can confirm AI suggestions.
              Nothing from a scan is saved until you say yes.
            </p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold">2. Short H-1B interview</p>
            <p className="mt-2 text-sm text-slate-600">
              Cap, transfer, or extension — and change of status vs consular. Completeness, not
              approval odds.
            </p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold">3. Attorney review</p>
            <p className="mt-2 text-sm text-slate-600">{disclaimer.marketplace}</p>
          </li>
        </ol>
        <SiteFooter />
      </div>
    </main>
  );
}
