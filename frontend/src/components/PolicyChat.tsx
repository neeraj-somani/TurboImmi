import { FormEvent, useState } from "react";
import disclaimer from "../../../shared/disclaimer.json";
import { apiJson, type ChatResponse, type PolicyCitation, type SpaConfig } from "../api";

type Turn = {
  question: string;
  answer: string;
  refused: boolean;
  citations: PolicyCitation[];
};

type Props = {
  config: SpaConfig;
  onMessage: (text: string) => void;
  onError: (text: string | null) => void;
};

export default function PolicyChat({ config, onMessage, onError }: Props) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const question = draft.trim();
    if (!question) {
      onError("Type a question first.");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const result = await apiJson<ChatResponse>(config, "/chat", {
        method: "POST",
        body: JSON.stringify({ message: question }),
      });
      setTurns((current) => [
        ...current,
        {
          question,
          answer: result.answer,
          refused: result.refused,
          citations: result.citations,
        },
      ]);
      setRemaining(result.remaining);
      setDraft("");
      onMessage(
        result.refused
          ? "No cited excerpt for that. Verify on USCIS.gov. A licensed attorney must review before filing."
          : "Answered from stored USCIS excerpts. Verify the linked page. Not legal advice.",
      );
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not send chat");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Policy chat</p>
      <p className="mt-1 text-sm text-slate-600">{disclaimer.short}</p>
      <p className="mt-2 text-sm text-slate-600">
        Answers come only from a short set of USCIS excerpts, with a deep link and as-of date. If we
        do not have a cited source, we stay quiet. This is not legal advice and not a USCIS or DHS
        endorsement.
      </p>
      {turns.length > 0 ? (
        <ul className="mt-4 space-y-3 text-sm">
          {turns.map((turn, index) => (
            <li key={`${turn.question}-${index}`} className="rounded-md border border-slate-200 px-3 py-3">
              <p className="font-medium text-slate-800">You</p>
              <p className="mt-1 text-slate-700">{turn.question}</p>
              <p className="mt-3 font-medium text-slate-800">{turn.refused ? "No cited source" : "From USCIS excerpts"}</p>
              <p className="mt-1 text-slate-700">{turn.answer}</p>
              {turn.citations.length > 0 ? (
                <ul className="mt-2 space-y-1">
                  {turn.citations.map((cite) => (
                    <li key={`${cite.source_url}-${cite.title}`}>
                      <a className="underline" href={cite.source_url} target="_blank" rel="noreferrer">
                        {cite.title}
                      </a>
                      <span className="text-slate-500"> · as of {cite.retrieved_at} · Verify on USCIS.gov</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          Try a question about the H-1B regular cap, electronic registration, or the labor condition
          application.
        </p>
      )}
      <form className="mt-4 space-y-3" onSubmit={(event) => void onSubmit(event)}>
        <label className="block text-sm">
          Question
          <textarea
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            rows={3}
            maxLength={400}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="What is the H-1B regular cap?"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            disabled={busy}
          >
            {busy ? "Looking up…" : "Ask"}
          </button>
          {remaining !== null ? (
            <p className="text-sm text-slate-600">{remaining} chat turns left today</p>
          ) : (
            <p className="text-sm text-slate-600">Limit is 15 turns per UTC day.</p>
          )}
        </div>
      </form>
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
