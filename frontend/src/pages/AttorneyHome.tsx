import { Link, Navigate } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";
import { startHostedUiLogout } from "../auth";
import SiteFooter from "../components/SiteFooter";
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
      <div className="mx-auto max-w-2xl px-6 py-12">
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
        <p className="mt-4 text-slate-700">{disclaimer.marketplace}</p>
        <p className="mt-2 text-sm text-slate-600">
          This account is locked to Attorney. Applicant case APIs stay blocked. Listings you create
          later stay unpublished and show an Unverified badge until a later review step.
        </p>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2">
          <li className="rounded-lg border border-dashed border-slate-300 p-4 text-sm">
            <p className="font-medium">Directory profile</p>
            <p className="mt-1 text-slate-600">Self-serve attorney card comes on a later day.</p>
          </li>
          <li className="rounded-lg border border-dashed border-slate-300 p-4 text-sm">
            <p className="font-medium">Consult inbox</p>
            <p className="mt-1 text-slate-600">In-app consult requests — no email blast.</p>
          </li>
        </ul>
        <SiteFooter />
      </div>
    </main>
  );
}
