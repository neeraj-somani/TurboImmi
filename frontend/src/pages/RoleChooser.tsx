import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError, apiJson, homePath } from "../api";
import { refreshSession } from "../auth";
import SiteFooter from "../components/SiteFooter";
import { useSpa } from "../spa";

export default function RoleChooser() {
  const { config, me, reloadMe, signedIn } = useSpa();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<"Applicant" | "Attorney" | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!signedIn) {
    return <Navigate to="/" replace />;
  }
  if (me?.roleChosen) {
    return <Navigate to={homePath(me)} replace />;
  }

  async function choose(role: "Applicant" | "Attorney") {
    setBusy(role);
    setError(null);
    try {
      await apiJson(config, "/me/role", {
        method: "POST",
        body: JSON.stringify({ role }),
      });
      const refreshed = await refreshSession(config);
      await reloadMe();
      navigate(role === "Attorney" ? "/attorney" : "/app", { replace: true });
      if (!refreshed) {
        setError("Role saved. Sign out and sign in again if a page still looks like the old role.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "ROLE_LOCKED") {
        await reloadMe();
        setError("This account already has a role. It cannot be switched.");
      } else {
        setError(err instanceof Error ? err.message : "Could not save role");
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">TurboImmi</p>
        <h1 className="mt-2 text-3xl font-semibold">How will you use TurboImmi?</h1>
        <p className="mt-4 text-slate-700">
          Choose once. Applicants get a profile, H-1B case, and the attorney directory. Attorneys get
          a profile desk and consult inbox. You cannot switch later.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <button
            type="button"
            disabled={busy !== null}
            className="rounded-lg border border-slate-300 bg-white px-4 py-6 text-left hover:border-slate-900 disabled:opacity-60"
            onClick={() => void choose("Applicant")}
          >
            <p className="font-semibold">I am an Applicant</p>
            <p className="mt-2 text-sm text-slate-600">Save a profile and a draft H-1B case.</p>
            {busy === "Applicant" ? <p className="mt-3 text-sm">Saving…</p> : null}
          </button>
          <button
            type="button"
            disabled={busy !== null}
            className="rounded-lg border border-slate-300 bg-white px-4 py-6 text-left hover:border-slate-900 disabled:opacity-60"
            onClick={() => void choose("Attorney")}
          >
            <p className="font-semibold">I am an Attorney</p>
            <p className="mt-2 text-sm text-slate-600">Directory card and in-app consult inbox.</p>
            {busy === "Attorney" ? <p className="mt-3 text-sm">Saving…</p> : null}
          </button>
        </div>
        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
        <SiteFooter />
      </div>
    </main>
  );
}
