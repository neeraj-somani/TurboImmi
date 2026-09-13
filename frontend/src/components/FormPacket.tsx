import { FormEvent, useEffect, useState } from "react";
import { apiJson, type CaseRecord, type PacketFields, type SpaConfig } from "../api";

type Props = {
  config: SpaConfig;
  cases: CaseRecord[];
  onSaved: (updated: CaseRecord) => void;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

function emptyPacket(): PacketFields {
  return {
    petitionerLegalName: "",
    petitionerUsAddress: "",
    petitionerFein: "",
    petitionerOrgType: "",
    beneficiaryGiven: "",
    beneficiaryFamily: "",
    beneficiaryDateOfBirth: "",
    beneficiaryCountryOfBirth: "",
    beneficiaryCitizenship: "",
    beneficiaryPassportNumber: "",
    beneficiaryPassportExpiry: "",
    beneficiaryAlienNumber: "",
    jobTitle: "",
    socCode: "",
    wageAmount: "",
    wageUnit: "",
    hoursPerWeek: "",
    worksiteAddress: "",
    lcaEtaNumber: "",
    requestedStart: "",
    requestedEnd: "",
    capExemptClaim: false,
    offsiteItinerary: false,
    evidencePassport: false,
    evidenceOfferLetter: false,
    evidenceLca: false,
  };
}

export default function FormPacket({ config, cases, onSaved, onMessage, onError }: Props) {
  const [caseId, setCaseId] = useState(cases[0]?.caseId ?? "");
  const [fields, setFields] = useState<PacketFields>(emptyPacket());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!cases.length) {
      setCaseId("");
      setFields(emptyPacket());
      return;
    }
    const selected = cases.find((item) => item.caseId === caseId) ?? cases[0];
    setCaseId(selected.caseId);
    setFields({ ...emptyPacket(), ...(selected.packet || {}) });
  }, [caseId, cases]);

  function setText(key: keyof PacketFields, value: string) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!caseId) {
      onError("Create a draft case first.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const saved = await apiJson<CaseRecord>(config, `/cases/${caseId}`, {
        method: "PATCH",
        body: JSON.stringify({
          lcaEtaNumber: fields.lcaEtaNumber || undefined,
          formFields: fields,
        }),
      });
      onSaved(saved);
      onMessage("Packet review saved. This is not a USCIS filing. A licensed attorney must review it.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save packet");
    } finally {
      setBusy(false);
    }
  }

  if (!cases.length) {
    return (
      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">Form packet</p>
        <p className="mt-1 text-sm text-slate-600">Create a draft case, then review the mapped fields here.</p>
      </section>
    );
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Form packet review</p>
      <p className="mt-1 text-sm text-slate-600">
        Educational mapping of profile + interview onto I-129 / H-style fields. Not a government form,
        not a filing, and not legal advice. PDF export is later. A licensed attorney must review
        before anyone files.
      </p>
      <form className="mt-4 space-y-4" onSubmit={(event) => void onSubmit(event)}>
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
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Petitioner</legend>
          <label className="block text-sm">
            Legal name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.petitionerLegalName ?? ""}
              onChange={(event) => setText("petitionerLegalName", event.target.value)}
            />
          </label>
          <label className="block text-sm">
            US address
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.petitionerUsAddress ?? ""}
              onChange={(event) => setText("petitionerUsAddress", event.target.value)}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              FEIN (optional)
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.petitionerFein ?? ""}
                onChange={(event) => setText("petitionerFein", event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Org type (optional)
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.petitionerOrgType ?? ""}
                onChange={(event) => setText("petitionerOrgType", event.target.value)}
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Beneficiary</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              Given name
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.beneficiaryGiven ?? ""}
                onChange={(event) => setText("beneficiaryGiven", event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Family name
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.beneficiaryFamily ?? ""}
                onChange={(event) => setText("beneficiaryFamily", event.target.value)}
              />
            </label>
          </div>
          <label className="block text-sm">
            Date of birth
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.beneficiaryDateOfBirth ?? ""}
              onChange={(event) => setText("beneficiaryDateOfBirth", event.target.value)}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              Passport number
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.beneficiaryPassportNumber ?? ""}
                onChange={(event) => setText("beneficiaryPassportNumber", event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Passport expiry
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.beneficiaryPassportExpiry ?? ""}
                onChange={(event) => setText("beneficiaryPassportExpiry", event.target.value)}
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Employment</legend>
          <label className="block text-sm">
            Job title
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.jobTitle ?? ""}
              onChange={(event) => setText("jobTitle", event.target.value)}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-sm">
              Wage
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.wageAmount ?? ""}
                onChange={(event) => setText("wageAmount", event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Unit
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.wageUnit ?? ""}
                onChange={(event) => setText("wageUnit", event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Hours / week
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={fields.hoursPerWeek ?? ""}
                onChange={(event) => setText("hoursPerWeek", event.target.value)}
              />
            </label>
          </div>
          <label className="block text-sm">
            Worksite
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.worksiteAddress ?? ""}
              onChange={(event) => setText("worksiteAddress", event.target.value)}
            />
          </label>
          <label className="block text-sm">
            LCA ETA number (optional)
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={fields.lcaEtaNumber ?? ""}
              onChange={(event) => setText("lcaEtaNumber", event.target.value)}
            />
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={Boolean(fields.offsiteItinerary)}
              onChange={(event) =>
                setFields((current) => ({ ...current, offsiteItinerary: event.target.checked }))
              }
            />
            <span>Off-site / itinerary work (flag only; no specialty-occupation essay).</span>
          </label>
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Evidence checklist</legend>
          <p className="text-sm text-slate-600">Presence flags only. Files are not stored as a vault.</p>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={Boolean(fields.evidencePassport)}
              onChange={(event) =>
                setFields((current) => ({ ...current, evidencePassport: event.target.checked }))
              }
            />
            <span>Passport biographic page</span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={Boolean(fields.evidenceOfferLetter)}
              onChange={(event) =>
                setFields((current) => ({ ...current, evidenceOfferLetter: event.target.checked }))
              }
            />
            <span>Offer letter</span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={Boolean(fields.evidenceLca)}
              onChange={(event) =>
                setFields((current) => ({ ...current, evidenceLca: event.target.checked }))
              }
            />
            <span>LCA (if any)</span>
          </label>
        </fieldset>
        <p className="text-sm text-slate-600">
          Classification from the interview: {fields.intent || "not set"} · {fields.entryPath || "not set"}
          {fields.requestedStart ? ` · ${fields.requestedStart}` : ""}
          {fields.requestedEnd ? ` to ${fields.requestedEnd}` : ""}.
        </p>
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save packet review"}
        </button>
      </form>
    </section>
  );
}
