import { FormEvent, useEffect, useState } from "react";
import disclaimer from "../../../shared/disclaimer.json";
import { apiJson, type AttorneyRecord, type CaseRecord, type ConsultRecord, type SpaConfig } from "../api";

const SPECIALTIES = [
  { value: "", label: "Any specialty" },
  { value: "h1b", label: "H-1B" },
  { value: "f1_opt", label: "F-1 / OPT" },
  { value: "h4", label: "H-4" },
  { value: "perm", label: "PERM / I-140" },
] as const;

const SPECIALTY_LABEL: Record<string, string> = {
  h1b: "H-1B",
  f1_opt: "F-1 / OPT",
  h4: "H-4",
  perm: "PERM / I-140",
};

type Props = {
  config: SpaConfig;
  cases: CaseRecord[];
  focusAttorneyId?: string;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

export default function AttorneyDirectory({ config, cases, focusAttorneyId, onMessage, onError }: Props) {
  const [state, setState] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [attorneys, setAttorneys] = useState<AttorneyRecord[]>([]);
  const [consults, setConsults] = useState<ConsultRecord[]>([]);
  const [selected, setSelected] = useState(focusAttorneyId ?? "");
  const [caseId, setCaseId] = useState(cases[0]?.caseId ?? "");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (cases.length && !cases.some((item) => item.caseId === caseId)) {
      setCaseId(cases[0].caseId);
    }
  }, [caseId, cases]);

  useEffect(() => {
    if (focusAttorneyId) {
      setSelected(focusAttorneyId);
    }
  }, [focusAttorneyId]);

  async function loadDirectory() {
    onError(null);
    const params = new URLSearchParams();
    if (state.trim()) {
      params.set("state", state.trim().toUpperCase());
    }
    if (specialty) {
      params.set("specialty", specialty);
    }
    const query = params.toString();
    const listed = await apiJson<{ attorneys: AttorneyRecord[] }>(
      config,
      query ? `/attorneys?${query}` : "/attorneys",
    );
    setAttorneys(listed.attorneys);
    const mine = await apiJson<{ consults: ConsultRecord[] }>(config, "/consults");
    setConsults(mine.consults);
  }

  useEffect(() => {
    void loadDirectory().catch((err) => {
      onError(err instanceof Error ? err.message : "Could not load attorneys");
    });
  }, [config]);

  async function onFilter(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await loadDirectory();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load attorneys");
    } finally {
      setBusy(false);
    }
  }

  async function onRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected) {
      onError("Choose a listed attorney first.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      await apiJson<ConsultRecord>(config, "/consults", {
        method: "POST",
        body: JSON.stringify({
          attorneyId: selected,
          caseId: caseId || undefined,
          message,
        }),
      });
      setMessage("");
      await loadDirectory();
      onMessage("Consult requested in-app. This does not assign counsel and does not send email.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not request consult");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="attorney-directory" className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Attorney directory</p>
      <p className="mt-1 text-sm text-slate-600">{disclaimer.marketplace}</p>
      <form className="mt-4 grid gap-3 sm:grid-cols-3" onSubmit={(event) => void onFilter(event)}>
        <label className="block text-sm">
          State
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 uppercase"
            maxLength={2}
            value={state}
            onChange={(event) => setState(event.target.value)}
            placeholder="CA"
          />
        </label>
        <label className="block text-sm">
          Specialty
          <select
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={specialty}
            onChange={(event) => setSpecialty(event.target.value)}
          >
            {SPECIALTIES.map((item) => (
              <option key={item.value || "any"} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="self-end rounded-md border border-slate-300 px-4 py-2 text-sm" disabled={busy}>
          Filter
        </button>
      </form>
      {attorneys.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">No published listings match.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {attorneys.map((item) => (
            <li key={item.attorneyId}>
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-200 px-3 py-3 text-sm">
                <input
                  type="radio"
                  className="mt-1"
                  name="attorney"
                  checked={selected === item.attorneyId}
                  onChange={() => setSelected(item.attorneyId)}
                />
                <span>
                  <span className="font-medium">{item.displayName}</span>
                  {item.verified ? null : (
                    <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">Unverified</span>
                  )}
                  <span className="mt-1 block text-slate-600">
                    {item.firmName} · {item.usState} ·{" "}
                    {item.specialties.map((value) => SPECIALTY_LABEL[value] ?? value).join(", ")}
                  </span>
                  <span className="mt-1 block text-slate-600">{item.bio}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      <form className="mt-5 space-y-3" onSubmit={(event) => void onRequest(event)}>
        {cases.length ? (
          <label className="block text-sm">
            Case (optional)
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
            >
              {cases.map((item) => (
                <option key={item.caseId} value={item.caseId}>
                  {item.visaClass} · {item.status}
                  {item.intent ? ` · ${item.intent}` : ""}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="block text-sm">
          Short message
          <textarea
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            rows={3}
            maxLength={400}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Educational consult request. Do not paste passport numbers."
          />
        </label>
        <button type="submit" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50" disabled={busy}>
          Request consult
        </button>
      </form>
      {consults.length ? (
        <div className="mt-5">
          <p className="text-sm font-medium">Your consult requests</p>
          <ul className="mt-2 space-y-2 text-sm text-slate-600">
            {consults.map((item) => (
              <li key={item.consultId} className="rounded-md bg-slate-50 px-3 py-2">
                {item.attorneyDisplayName || item.attorneyId} · {item.status}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
