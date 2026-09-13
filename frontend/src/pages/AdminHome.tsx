import { Link, Navigate } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";
import { homePath } from "../api";
import { startHostedUiLogout } from "../auth";
import AdminDesk from "../components/AdminDesk";
import NewsCards from "../components/NewsCards";
import SiteFooter from "../components/SiteFooter";
import { useSpa } from "../spa";

export default function AdminHome() {
  const { config, me, signedIn } = useSpa();

  if (!signedIn) {
    return <Navigate to="/" replace />;
  }
  if (!me?.roleChosen) {
    return <Navigate to="/choose-role" replace />;
  }
  if (me.role !== "Admin") {
    return <Navigate to={homePath(me)} replace />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-2xl px-6 py-12">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Admin</p>
            <h1 className="mt-1 text-2xl font-semibold">Verification desk</h1>
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
          Basic listing checks only — not a bar lookup and not legal advice. Applicant packets stay
          hidden. Publishing a card does not assign counsel.
        </p>
        <div className="mt-8">
          <AdminDesk config={config} />
        </div>
        <NewsCards config={config} />
        <SiteFooter />
      </div>
    </main>
  );
}
