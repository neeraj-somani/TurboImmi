import { FormEvent, useEffect, useState } from "react";
import disclaimer from "../../../shared/disclaimer.json";
import { apiJson, type AttorneyRecord, type ConsultRecord, type SpaConfig } from "../api";

const SPECIALTIES = [
  { value: "h1b", label: "H-1B" },
  { value: "f1_opt", label: "F-1 / OPT" },
  { value: "h4", label: "H-4" },
  { value: "perm", label: "PERM / I-140" },
] as const;

type Props = {
  config: SpaConfig;
};

export default function AttorneyDesk({ config }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [usState, setUsState] = useState("CA");
  const [specialties, setSpecialties] = useState<string[]>(["h1b"]);
  const [bio, setBio] = useState("");
  const [card, setCard] = useState<AttorneyRecord | null>(null);
  const [consults, setConsults] = useState<ConsultRecord[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const listed = await apiJson<{ consults: ConsultRecord[]; attorney?: AttorneyRecord }>(
          config,
          "/consults",
        );
        setConsults(listed.consults);
        if (listed.attorney) {
          setCard(listed.attorney);
          setDisplayName(listed.attorney.displayName);
          setFirmName(listed.attorney.firmName);
          setUsState(listed.attorney.usState || "CA");
          setSpecialties(listed.attorney.specialties.length ? listed.attorney.specialties : ["h1b"]);
          setBio(listed.attorney.bio);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load inbox");
      }
    })();
  }, [config]);

  function toggleSpecialty(value: string) {
    setSpecialties((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await apiJson<AttorneyRecord>(config, "/attorneys/me", {
        method: "PUT",
        body: JSON.stringify({ displayName, firmName, usState, specialties, bio }),
      });
      setCard(saved);
      setMessage(
        saved.published
          ? "Profile saved. This listing is visible because an admin published it. TurboImmi does not assign counsel."
          : "Profile saved. It stays unpublished and Unverified until an admin reviews it.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Directory profile</p>
        <p className="mt-1 text-sm text-slate-600">{disclaimer.marketplace}</p>
        <form className="mt-4 space-y-3" onSubmit={(event) => void onSave(event)}>
          <label className="block text-sm">
            Display name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Firm name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={firmName}
              onChange={(event) => setFirmName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            US state
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 uppercase"
              maxLength={2}
              value={usState}
              onChange={(event) => setUsState(event.target.value)}
              required
            />
          </label>
          <fieldset className="text-sm">
            <legend>Specialties</legend>
            <div className="mt-2 flex flex-wrap gap-3">
              {SPECIALTIES.map((item) => (
                <label key={item.value} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={specialties.includes(item.value)}
                    onChange={() => toggleSpecialty(item.value)}
                  />
                  {item.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm">
            Short bio
            <textarea
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              rows={3}
              maxLength={400}
              value={bio}
              onChange={(event) => setBio(event.target.value)}
            />
          </label>
          <button type="submit" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white" disabled={busy}>
            Save profile
          </button>
        </form>
        {card ? (
          <p className="mt-3 text-sm text-slate-600">
            Status: {card.published ? "listed" : "unpublished"} · {card.verified ? "verified" : "Unverified"}.
            New cards stay hidden until an Admin publishes them. That does not assign counsel.
          </p>
        ) : null}
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Consult inbox</p>
        <p className="mt-1 text-sm text-slate-600">In-app only. No email. Opening this list marks new requests seen.</p>
        {consults.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">No consult requests yet.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {consults.map((item) => (
              <li key={item.consultId} className="rounded-md bg-slate-50 px-3 py-2">
                <p className="font-medium">
                  {item.applicantDisplayName || "Applicant"} · {item.status}
                </p>
                <p className="mt-1 text-slate-600">{item.message}</p>
                {item.caseId ? <p className="mt-1 text-xs text-slate-500">Case {item.caseId}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
      {message ? <p className="text-sm text-emerald-800">{message}</p> : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
