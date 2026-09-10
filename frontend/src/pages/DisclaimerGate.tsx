import { useState } from "react";
import { Link } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";
import { acceptDisclaimer } from "../disclaimerAck";

type Props = {
  onAccepted: () => void;
};

export default function DisclaimerGate({ onAccepted }: Props) {
  const [checked, setChecked] = useState(false);

  function continueOn() {
    acceptDisclaimer(disclaimer.version);
    onAccepted();
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">TurboImmi</p>
        <h1 className="mt-2 text-3xl font-semibold">Please read this first</h1>
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Draft notice — counsel review before any public launch.
        </p>
        <p className="mt-6 text-slate-700">{disclaimer.full}</p>
        <p className="mt-4 text-sm text-slate-600">{disclaimer.scoreNotOdds}</p>
        <p className="mt-2 text-sm text-slate-600">{disclaimer.marketplace}</p>
        <p className="mt-6 text-sm">
          <Link className="underline" to={disclaimer.tosPath}>
            Terms of Service
          </Link>
          {" · "}
          <Link className="underline" to={disclaimer.privacyPath}>
            Privacy Policy
          </Link>
          <span className="text-slate-500"> (draft — counsel review)</span>
        </p>
        <label className="mt-8 flex items-start gap-3 text-sm text-slate-800">
          <input
            type="checkbox"
            className="mt-1"
            checked={checked}
            onChange={(event) => setChecked(event.target.checked)}
          />
          <span>
            I understand TurboImmi is educational only, is not a law firm, and a licensed attorney
            must review before filing.
          </span>
        </label>
        <button
          type="button"
          disabled={!checked}
          className="mt-6 rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
          onClick={continueOn}
        >
          Continue
        </button>
      </div>
    </main>
  );
}
