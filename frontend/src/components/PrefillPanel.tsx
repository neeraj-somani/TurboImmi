import { FormEvent, useState } from "react";
import { apiJson, ApiError, type ProfileResponse, type SpaConfig } from "../api";

const ALLOWED = ["image/jpeg", "image/png", "application/pdf"];
const MAX_BYTES = 8 * 1024 * 1024;

type Suggestions = {
  legalName?: { given?: string; family?: string };
  dateOfBirth?: string;
  countryOfBirth?: string;
  countryOfCitizenship?: string;
  passportNumber?: string;
  passportExpiry?: string;
  employerLegalName?: string;
  jobTitle?: string;
  wageAmount?: string;
  wageUnit?: string;
  worksiteAddress?: string;
};

type UploadResp = {
  jobId: string;
  uploadUrl: string | null;
  headers: { "Content-Type": string };
  skipUpload: boolean;
  docType: "passport" | "offer_letter";
};

type ExtractResp = {
  jobId: string;
  status: string;
  source?: string;
  suggestions: Suggestions;
};

type Props = {
  config: SpaConfig;
  onApplied: (profile: ProfileResponse["profile"]) => void;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

export default function PrefillPanel({ config, onApplied, onMessage, onError }: Props) {
  const [docType, setDocType] = useState<"passport" | "offer_letter">("passport");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [fields, setFields] = useState<Suggestions>({});
  const [busy, setBusy] = useState(false);

  function setField(key: keyof Suggestions, value: string) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  async function runExtract(chosen: File | null) {
    onError(null);
    if (chosen && (!ALLOWED.includes(chosen.type) || chosen.size > MAX_BYTES)) {
      onError("Only jpeg, png, or pdf up to 8 MB.");
      return;
    }
    setBusy(true);
    try {
      const uploaded = await apiJson<UploadResp>(config, "/prefill/upload-url", {
        method: "POST",
        body: JSON.stringify({
          docType,
          contentType: chosen?.type || "image/jpeg",
          contentLength: chosen?.size || 1,
        }),
      });
      if (chosen && !uploaded.skipUpload && uploaded.uploadUrl) {
        const put = await fetch(uploaded.uploadUrl, {
          method: "PUT",
          headers: uploaded.headers,
          body: chosen,
        });
        if (!put.ok) {
          throw new Error("Could not upload the file");
        }
      }
      const extracted = await apiJson<ExtractResp>(config, "/prefill/extract", {
        method: "POST",
        body: JSON.stringify({ jobId: uploaded.jobId }),
      });
      setJobId(extracted.jobId);
      setSource(extracted.source ?? null);
      setFields(extracted.suggestions || {});
      onMessage(
        extracted.source === "fixture"
          ? "Sample suggestions loaded. Edit them, then confirm. Nothing is saved yet."
          : "Suggestions ready. Edit anything that is wrong, then confirm. Nothing is saved yet.",
      );
    } catch (err) {
      onError(err instanceof ApiError || err instanceof Error ? err.message : "Extract failed");
    } finally {
      setBusy(false);
    }
  }

  async function onExtract(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      onError("Choose a jpeg, png, or pdf (8 MB or smaller), or use sample suggestions.");
      return;
    }
    await runExtract(file);
  }

  async function onConfirm() {
    if (!jobId) {
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const saved = await apiJson<ProfileResponse>(config, "/prefill/confirm", {
        method: "POST",
        body: JSON.stringify({ jobId, fields }),
      });
      onApplied(saved.profile);
      setJobId(null);
      setFields({});
      setFile(null);
      onMessage("Confirmed fields were saved to your profile. Source file deleted.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not confirm");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteUploads() {
    setBusy(true);
    onError(null);
    try {
      await apiJson(config, "/prefill/uploads", { method: "DELETE" });
      setJobId(null);
      setFields({});
      setFile(null);
      onMessage("Uploads deleted.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not delete uploads");
    } finally {
      setBusy(false);
    }
  }

  const isPassport = docType === "passport";

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Document prefill</p>
      <p className="mt-1 text-sm text-slate-600">
        Optional. You can skip this and type the profile by hand. AI suggestions are educational
        only and are not written until you confirm. Max 2 files, 8 MB, jpeg/png/pdf. A licensed
        attorney must review before filing.
      </p>
      <form className="mt-4 space-y-3" onSubmit={(event) => void onExtract(event)}>
        <label className="block text-sm">
          Document type
          <select
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={docType}
            onChange={(event) => setDocType(event.target.value as "passport" | "offer_letter")}
          >
            <option value="passport">Passport</option>
            <option value="offer_letter">Offer letter</option>
          </select>
        </label>
        <label className="block text-sm">
          File
          <input
            className="mt-1 block w-full text-sm"
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {busy ? "Working…" : "Upload and suggest"}
          </button>
          <button
            type="button"
            disabled={busy}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
            onClick={() => void runExtract(null)}
          >
            Use sample suggestions
          </button>
        </div>
      </form>
      {jobId ? (
        <div className="mt-4 space-y-3 rounded-md bg-slate-50 p-4">
          <p className="text-sm text-slate-700">
            Review these suggestions{source ? ` (source: ${source})` : ""}. Confirm writes the
            profile. Raw scan text is not stored.
          </p>
          {isPassport ? (
            <>
              <label className="block text-sm">
                Given name
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.legalName?.given ?? ""}
                  onChange={(event) =>
                    setFields((current) => ({
                      ...current,
                      legalName: { ...current.legalName, given: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="block text-sm">
                Family name
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.legalName?.family ?? ""}
                  onChange={(event) =>
                    setFields((current) => ({
                      ...current,
                      legalName: { ...current.legalName, family: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="block text-sm">
                Date of birth
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.dateOfBirth ?? ""}
                  onChange={(event) => setField("dateOfBirth", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Country of citizenship
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.countryOfCitizenship ?? ""}
                  onChange={(event) => setField("countryOfCitizenship", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Passport number
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.passportNumber ?? ""}
                  onChange={(event) => setField("passportNumber", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Passport expiry
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.passportExpiry ?? ""}
                  onChange={(event) => setField("passportExpiry", event.target.value)}
                />
              </label>
            </>
          ) : (
            <>
              <label className="block text-sm">
                Employer legal name
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.employerLegalName ?? ""}
                  onChange={(event) => setField("employerLegalName", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Job title
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.jobTitle ?? ""}
                  onChange={(event) => setField("jobTitle", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Wage amount
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.wageAmount ?? ""}
                  onChange={(event) => setField("wageAmount", event.target.value)}
                />
              </label>
              <label className="block text-sm">
                Worksite
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  value={fields.worksiteAddress ?? ""}
                  onChange={(event) => setField("worksiteAddress", event.target.value)}
                />
              </label>
            </>
          )}
          <button
            type="button"
            disabled={busy}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            onClick={() => void onConfirm()}
          >
            Confirm and save to profile
          </button>
        </div>
      ) : null}
      <button
        type="button"
        disabled={busy}
        className="mt-4 text-sm underline disabled:opacity-50"
        onClick={() => void onDeleteUploads()}
      >
        Delete my uploads
      </button>
    </section>
  );
}
