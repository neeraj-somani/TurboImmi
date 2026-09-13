import { useEffect, useState } from "react";
import disclaimer from "../../../shared/disclaimer.json";
import { apiJson, type CaseRecord, type CaseScore, type SpaConfig } from "../api";
import AttorneyReviewAttestation from "./AttorneyReviewAttestation";

type Props = {
  config: SpaConfig;
  cases: CaseRecord[];
  onSaved: (updated: CaseRecord) => void;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

export default function ScorePanel({ config, cases, onSaved, onMessage, onError }: Props) {
  const [caseId, setCaseId] = useState(cases[0]?.caseId ?? "");
  const [explain, setExplain] = useState(false);
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(false);

  const selected = cases.find((item) => item.caseId === caseId) ?? cases[0];
  const score: CaseScore | undefined = selected?.score;
  const alreadyAttested = Boolean(selected?.attestationAcceptedAt);

  useEffect(() => {
    if (!cases.length) {
      setCaseId("");
      setAccepted(false);
      return;
    }
    const next = cases.find((item) => item.caseId === caseId) ?? cases[0];
    setCaseId(next.caseId);
    setAccepted(Boolean(next.attestationAcceptedAt));
  }, [caseId, cases]);

  async function runScore() {
    if (!caseId) {
      onError("Create a draft case first.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const updated = await apiJson<CaseRecord>(config, `/cases/${caseId}/score`, {
        method: "POST",
        body: JSON.stringify({ explain }),
      });
      onSaved(updated);
      onMessage("Score updated. Completeness and consistency only — not approval odds.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not score case");
    } finally {
      setBusy(false);
    }
  }

  async function submitAttestation() {
    if (!caseId) {
      onError("Create a draft case first.");
      return;
    }
    if (!accepted) {
      onError("Check the attorney-review attestation first.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const updated = await apiJson<CaseRecord>(config, `/cases/${caseId}/attestation`, {
        method: "POST",
        body: JSON.stringify({ accepted: true, text: disclaimer.attestation }),
      });
      onSaved(updated);
      onMessage("Attestation saved. Status is ready_to_file. This does not file anything.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save attestation");
    } finally {
      setBusy(false);
    }
  }

  if (!cases.length) {
    return (
      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Validation score</p>
        <p className="mt-1 text-sm text-slate-600">
          Create a draft case, then check completeness and consistency. {disclaimer.scoreNotOdds}
        </p>
      </section>
    );
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Validation score</p>
      <p className="mt-1 text-sm text-slate-600">{disclaimer.scoreNotOdds}</p>
      {cases.length > 1 ? (
        <label className="mt-4 block text-sm">
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
      <label className="mt-3 flex items-start gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          className="mt-1"
          checked={explain}
          onChange={(event) => setExplain(event.target.checked)}
        />
        <span>Explain rule hits in plain language (sends rule ids only, not passport numbers)</span>
      </label>
      <button
        type="button"
        className="mt-3 rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        disabled={busy}
        onClick={() => void runScore()}
      >
        {busy ? "Working…" : "Run score"}
      </button>
      {score ? (
        <div className="mt-4 space-y-3 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <p className="rounded-md bg-slate-50 px-3 py-2">
              Completeness <span className="font-semibold">{score.completeness}%</span>
            </p>
            <p className="rounded-md bg-slate-50 px-3 py-2">
              Consistency <span className="font-semibold">{score.consistency}%</span>
            </p>
          </div>
          {score.deductions.length === 0 ? (
            <p className="text-slate-600">No rule hits. Still not approval odds.</p>
          ) : (
            <ul className="space-y-2">
              {score.deductions.map((item) => (
                <li key={item.id} className="rounded-md border border-slate-200 px-3 py-2">
                  <span className="font-medium">{item.id}</span> · {item.severity} · {item.message}
                </li>
              ))}
            </ul>
          )}
          {score.explanation ? (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-amber-950">{score.explanation}</p>
          ) : null}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-600">No score yet. Fill profile, interview, and packet, then run.</p>
      )}
      <div className="mt-6">
        <AttorneyReviewAttestation
          checked={accepted}
          onChange={setAccepted}
          disabled={alreadyAttested || busy}
          note="Checking this and saving it marks the case ready_to_file. It does not file with USCIS and does not assign counsel."
        />
        <button
          type="button"
          className="mt-3 rounded-md border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
          disabled={busy || alreadyAttested || !accepted}
          onClick={() => void submitAttestation()}
        >
          {alreadyAttested ? "Attestation saved" : "Save attestation"}
        </button>
      </div>
      <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-4">
        <p className="text-sm font-medium text-slate-800">Request consult</p>
        <p className="mt-1 text-sm text-slate-600">{disclaimer.marketplace}</p>
        <button
          type="button"
          className="mt-3 rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
          onClick={() => {
            document.getElementById("attorney-directory")?.scrollIntoView({ behavior: "smooth" });
            onMessage("Pick a listed attorney below. This does not assign counsel.");
          }}
        >
          Request consult
        </button>
      </div>
    </section>
  );
}
