import { FormEvent, useEffect, useState } from "react";
import { apiJson, type AdminProfile, type AttorneyRecord, type SpaConfig } from "../api";

const FLAGS = [
  { value: "none", label: "No flag" },
  { value: "incomplete", label: "Incomplete" },
  { value: "mismatch", label: "Mismatch" },
  { value: "other", label: "Other" },
] as const;

type Props = {
  config: SpaConfig;
};

export default function AdminDesk({ config }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [attorneys, setAttorneys] = useState<AttorneyRecord[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const me = await apiJson<AdminProfile>(config, "/admin/me");
    setDisplayName(me.displayName);
    const listed = await apiJson<{ attorneys: AttorneyRecord[] }>(config, "/admin/attorneys");
    setAttorneys(listed.attorneys);
    setNotes(Object.fromEntries(listed.attorneys.map((item) => [item.attorneyId, item.flagNote ?? ""])));
  }

  useEffect(() => {
    void load().catch((err) => {
      setError(err instanceof Error ? err.message : "Could not load admin desk");
    });
  }, [config]);

  async function onSaveProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await apiJson<AdminProfile>(config, "/admin/me", {
        method: "PUT",
        body: JSON.stringify({ displayName }),
      });
      setDisplayName(saved.displayName);
      setMessage("Admin profile saved. This is not an applicant or attorney card.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save admin profile");
    } finally {
      setBusy(false);
    }
  }

  async function patchCard(attorneyId: string, body: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      const saved = await apiJson<AttorneyRecord>(config, `/admin/attorneys/${attorneyId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setAttorneys((current) => current.map((item) => (item.attorneyId === attorneyId ? saved : item)));
      setMessage("Listing updated. This does not assign counsel.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update listing");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Admin profile</p>
        <p className="mt-1 text-sm text-slate-600">Separate from applicant immigration fields and attorney listings.</p>
        <form className="mt-4 space-y-3" onSubmit={(event) => void onSaveProfile(event)}>
          <label className="block text-sm">
            Display name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
            />
          </label>
          <button type="submit" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white" disabled={busy}>
            Save admin profile
          </button>
        </form>
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Attorney queue</p>
        <p className="mt-1 text-sm text-slate-600">
          Basic checks: name, state, specialty, bio. Flag issues or publish after review.
        </p>
        <ul className="mt-4 space-y-4">
          {attorneys.map((item) => (
            <li key={item.attorneyId} className="rounded-md border border-slate-200 p-3 text-sm">
              <p className="font-medium">
                {item.displayName || item.attorneyId}
                {item.verified ? (
                  <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-900">Verified</span>
                ) : (
                  <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">Unverified</span>
                )}
                {item.published ? (
                  <span className="ml-2 rounded bg-slate-200 px-1.5 py-0.5 text-xs">Listed</span>
                ) : (
                  <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs">Unpublished</span>
                )}
              </p>
              <p className="mt-1 text-slate-600">
                {item.firmName} · {item.usState} · {item.specialties.join(", ")}
              </p>
              <p className="mt-1 text-slate-600">{item.bio || "No bio"}</p>
              <p className="mt-2 text-xs text-slate-500">
                Checks: {item.checks?.ok ? "pass" : `missing ${(item.checks?.missing || []).join(", ")}`}
                {item.flag && item.flag !== "none" ? ` · flag ${item.flag}` : ""}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md border border-slate-300 px-3 py-1.5 disabled:opacity-50"
                  disabled={busy}
                  onClick={() => void patchCard(item.attorneyId, { verified: !item.verified })}
                >
                  {item.verified ? "Clear verified" : "Mark verified"}
                </button>
                <button
                  type="button"
                  className="rounded-md border border-slate-300 px-3 py-1.5 disabled:opacity-50"
                  disabled={busy}
                  onClick={() => void patchCard(item.attorneyId, { published: !item.published })}
                >
                  {item.published ? "Unlist" : "Publish"}
                </button>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <select
                  className="rounded-md border border-slate-300 px-3 py-2"
                  value={item.flag ?? "none"}
                  onChange={(event) =>
                    void patchCard(item.attorneyId, {
                      flag: event.target.value,
                      flagNote: notes[item.attorneyId] || "",
                    })
                  }
                >
                  {FLAGS.map((flag) => (
                    <option key={flag.value} value={flag.value}>
                      {flag.label}
                    </option>
                  ))}
                </select>
                <input
                  className="rounded-md border border-slate-300 px-3 py-2"
                  placeholder="Flag note"
                  value={notes[item.attorneyId] ?? ""}
                  onChange={(event) =>
                    setNotes((current) => ({ ...current, [item.attorneyId]: event.target.value }))
                  }
                  onBlur={() => {
                    if ((item.flag ?? "none") !== "none") {
                      void patchCard(item.attorneyId, { flag: item.flag, flagNote: notes[item.attorneyId] || "" });
                    }
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>
      {message ? <p className="text-sm text-emerald-800">{message}</p> : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
