import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { apiJson, homePath, type CaseRecord, type ProfileResponse } from "../api";
import { startHostedUiLogout } from "../auth";
import FormPacket from "../components/FormPacket";
import IntentInterview from "../components/IntentInterview";
import AttorneyDirectory from "../components/AttorneyDirectory";
import NewsCards from "../components/NewsCards";
import PolicyChat from "../components/PolicyChat";
import ScorePanel from "../components/ScorePanel";
import JourneyMap, { JOURNEY_LABELS, JOURNEY_STAGES } from "../components/JourneyMap";
import SiteFooter from "../components/SiteFooter";
import PrefillPanel from "../components/PrefillPanel";
import { useSpa } from "../spa";

export default function ApplicantHome() {
  const { config, me, signedIn } = useSpa();
  const [given, setGiven] = useState("");
  const [family, setFamily] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [employer, setEmployer] = useState("");
  const [status, setStatus] = useState("");
  const [stage, setStage] = useState("h1b");
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!signedIn || me?.role !== "Applicant") {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const profile = await apiJson<ProfileResponse>(config, "/me/profile");
        const listed = await apiJson<{ cases: CaseRecord[] }>(config, "/cases");
        if (cancelled) {
          return;
        }
        setGiven(profile.profile.legalName?.given ?? "");
        setFamily(profile.profile.legalName?.family ?? "");
        setJobTitle(profile.profile.jobTitle ?? "");
        setEmployer(profile.profile.employerLegalName ?? "");
        setStatus(profile.profile.currentStatus ?? "");
        setStage(profile.profile.journeyStage ?? "h1b");
        setCases(listed.cases);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load profile");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [config, me?.role, signedIn]);

  if (!signedIn) {
    return <Navigate to="/" replace />;
  }
  if (!me?.roleChosen) {
    return <Navigate to="/choose-role" replace />;
  }
  if (me.role !== "Applicant") {
    return <Navigate to={homePath(me)} replace />;
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await apiJson(config, "/me/profile", {
        method: "PUT",
        body: JSON.stringify({
          legalName: { given, family },
          jobTitle,
          employerLegalName: employer,
          currentStatus: status,
          journeyStage: stage,
        }),
      });
      const listed = await apiJson<{ cases: CaseRecord[] }>(config, "/cases");
      setCases(listed.cases);
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    }
  }

  async function onCreateCase() {
    setError(null);
    try {
      const created = await apiJson<CaseRecord>(config, "/cases", {
        method: "POST",
        body: JSON.stringify({ visaClass: "H-1B" }),
      });
      setCases((current) => [created, ...current]);
      setMessage("Draft H-1B case created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create case");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-2xl px-6 py-12">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Applicant</p>
            <h1 className="mt-1 text-2xl font-semibold">Your H-1B workspace</h1>
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
        <p className="mt-3 text-sm text-slate-600">
          Educational only. A licensed attorney must review before filing. Completeness is not
          approval odds.
        </p>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Profile</p>
            <p className="mt-1 text-slate-600">Save names and job facts below.</p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Documents</p>
            <p className="mt-1 text-slate-600">Optional confirm-before-save prefill.</p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Interview</p>
            <p className="mt-1 text-slate-600">Cap, transfer, or extension.</p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Packet</p>
            <p className="mt-1 text-slate-600">Review mapped I-129 / H-style fields.</p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Score</p>
            <p className="mt-1 text-slate-600">Completeness and consistency, not approval odds.</p>
          </li>
          <li className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
            <p className="font-medium">Attorneys</p>
            <p className="mt-1 text-slate-600">Published listings only. Request consult is in-app.</p>
          </li>
        </ul>
        <JourneyMap stage={stage} />
        <PrefillPanel
          config={config}
          onApplied={(profile) => {
            setGiven(profile.legalName?.given ?? "");
            setFamily(profile.legalName?.family ?? "");
            setJobTitle(profile.jobTitle ?? "");
            setEmployer(profile.employerLegalName ?? "");
          }}
          onMessage={setMessage}
          onError={setError}
        />
        <form className="mt-8 space-y-4 rounded-lg border border-slate-200 bg-white p-5" onSubmit={(event) => void onSave(event)}>
          <p className="font-medium">Profile</p>
          <label className="block text-sm">
            Given name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={given}
              onChange={(event) => setGiven(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Family name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={family}
              onChange={(event) => setFamily(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Current status
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              placeholder="F-1, H-1B, …"
            />
          </label>
          <label className="block text-sm">
            Journey stage
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={stage}
              onChange={(event) => setStage(event.target.value)}
            >
              {JOURNEY_STAGES.map((value) => (
                <option key={value} value={value}>
                  {JOURNEY_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Employer legal name
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={employer}
              onChange={(event) => setEmployer(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Job title
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
            />
          </label>
          <button type="submit" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">
            Save profile
          </button>
        </form>
        <IntentInterview
          config={config}
          cases={cases}
          onSaved={(updated) => {
            setCases((current) => current.map((item) => (item.caseId === updated.caseId ? updated : item)));
          }}
          onMessage={setMessage}
          onError={setError}
        />
        <FormPacket
          config={config}
          cases={cases}
          onSaved={(updated) => {
            setCases((current) => current.map((item) => (item.caseId === updated.caseId ? updated : item)));
          }}
          onMessage={setMessage}
          onError={setError}
        />
        <ScorePanel
          config={config}
          cases={cases}
          onSaved={(updated) => {
            setCases((current) => current.map((item) => (item.caseId === updated.caseId ? updated : item)));
          }}
          onMessage={setMessage}
          onError={setError}
        />
        <PolicyChat config={config} onMessage={setMessage} onError={setError} />
        <AttorneyDirectory config={config} cases={cases} onMessage={setMessage} onError={setError} />
        <NewsCards config={config} onError={setError} />
        <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <p className="font-medium">H-1B cases</p>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              onClick={() => void onCreateCase()}
            >
              New draft case
            </button>
          </div>
          {cases.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">No cases yet.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {cases.map((item) => (
                <li key={item.caseId} className="rounded-md bg-slate-50 px-3 py-2">
                  <span className="font-medium">{item.visaClass}</span> · {item.status}
                  {item.intent ? ` · ${item.intent}` : ""}
                  {item.entryPath ? ` · ${item.entryPath}` : ""}
                  {item.score
                    ? ` · ${item.score.completeness}% complete / ${item.score.consistency}% consistent`
                    : ""}
                </li>
              ))}
            </ul>
          )}
        </section>
        {message ? <p className="mt-4 text-sm text-emerald-800">{message}</p> : null}
        {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
        <SiteFooter />
      </div>
    </main>
  );
}
