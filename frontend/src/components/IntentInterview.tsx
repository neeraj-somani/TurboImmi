import { FormEvent, useEffect, useState } from "react";
import { apiJson, type CaseRecord, type SpaConfig } from "../api";

const INTENTS = [
  { value: "cap", label: "Cap (new / lottery-subject H-1B)" },
  { value: "transfer", label: "Transfer (already in H-1B, new employer)" },
  { value: "extension", label: "Extension (stay in H-1B)" },
] as const;

const ENTRY_PATHS = [
  { value: "change_of_status", label: "Change of status (stay in the U.S.)" },
  { value: "consular", label: "Consular processing (visa stamp abroad)" },
] as const;

type Props = {
  config: SpaConfig;
  cases: CaseRecord[];
  onSaved: (updated: CaseRecord) => void;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

export default function IntentInterview({ config, cases, onSaved, onMessage, onError }: Props) {
  const [caseId, setCaseId] = useState(cases[0]?.caseId ?? "");
  const [intent, setIntent] = useState("");
  const [entryPath, setEntryPath] = useState("");
  const [capExempt, setCapExempt] = useState(false);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!cases.length) {
      setCaseId("");
      return;
    }
    const selected = cases.find((item) => item.caseId === caseId) ?? cases[0];
    setCaseId(selected.caseId);
    setIntent(selected.intent ?? "");
    setEntryPath(selected.entryPath ?? "");
    setCapExempt(Boolean(selected.capExemptClaim));
    setStart(selected.requestedStart ?? "");
    setEnd(selected.requestedEnd ?? "");
  }, [caseId, cases]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!caseId || !intent || !entryPath) {
      onError("Choose a filing type and an entry path.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const saved = await apiJson<CaseRecord>(config, `/cases/${caseId}`, {
        method: "PATCH",
        body: JSON.stringify({
          intent,
          entryPath,
          capExemptClaim: capExempt,
          requestedStart: start || undefined,
          requestedEnd: end || undefined,
        }),
      });
      onSaved(saved);
      onMessage("Interview saved on this case. A licensed attorney must still review before filing.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save interview");
    } finally {
      setBusy(false);
    }
  }

  if (!cases.length) {
    return (
      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">H-1B intent interview</p>
        <p className="mt-1 text-sm text-slate-600">Create a draft case first, then answer these questions.</p>
      </section>
    );
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">H-1B intent interview</p>
      <p className="mt-1 text-sm text-slate-600">
        Documents cannot tell cap vs transfer vs extension. These answers are educational only and
        are not a government determination. A licensed attorney must review before filing.
      </p>
      <form className="mt-4 space-y-3" onSubmit={(event) => void onSubmit(event)}>
        {cases.length > 1 ? (
          <label className="block text-sm">
            Case
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
        <fieldset>
          <legend className="text-sm font-medium">What is this filing?</legend>
          <div className="mt-2 space-y-2">
            {INTENTS.map((option) => (
              <label key={option.value} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="intent"
                  className="mt-1"
                  checked={intent === option.value}
                  onChange={() => setIntent(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-medium">How do you plan to proceed?</legend>
          <div className="mt-2 space-y-2">
            {ENTRY_PATHS.map((option) => (
              <label key={option.value} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="entryPath"
                  className="mt-1"
                  checked={entryPath === option.value}
                  onChange={() => setEntryPath(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={capExempt}
            onChange={(event) => setCapExempt(event.target.checked)}
          />
          <span>Cap-exempt claim (employer or role may be exempt). This is a note, not a legal finding.</span>
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Requested start
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              type="date"
              value={start}
              onChange={(event) => setStart(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Requested end
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              type="date"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save interview"}
        </button>
      </form>
    </section>
  );
}
