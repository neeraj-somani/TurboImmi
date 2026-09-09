import { Link, Navigate } from "react-router-dom";
import { startHostedUiLogout } from "../auth";
import { useSpa } from "../spa";

export default function AttorneyHome() {
  const { config, me, signedIn } = useSpa();

  if (!signedIn) {
    return <Navigate to="/" replace />;
  }
  if (!me?.roleChosen) {
    return <Navigate to="/choose-role" replace />;
  }
  if (me.role !== "Attorney") {
    return <Navigate to="/app" replace />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-xl px-6 py-12">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Attorney</p>
            <h1 className="mt-1 text-2xl font-semibold">Attorney desk</h1>
          </div>
          <div className="flex gap-3 text-sm">
            <Link className="underline" to="/">
              Home
            </Link>
            <button type="button" className="underline" onClick={() => startHostedUiLogout(config)}>
              Sign out
            </button>
          </div>
        </div>
        <p className="mt-4 text-slate-700">
          This account is locked to the Attorney role. The directory and consult inbox ship on later
          days. Applicant case APIs stay blocked for this role.
        </p>
        <p className="mt-3 text-sm text-slate-600">
          Educational product. Not a law firm. Not legal advice. Directory listings will show
          Unverified until a later seed/review step.
        </p>
      </div>
    </main>
  );
}
