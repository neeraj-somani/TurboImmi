import { useEffect, useState } from "react";
import officialLinks from "../../../shared/official_links.json";
import { apiJson, type AlertRecord, type SpaConfig } from "../api";

type Props = {
  config: SpaConfig;
  onError?: (text: string | null) => void;
};

export default function NewsCards({ config, onError }: Props) {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [busy, setBusy] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const body = await apiJson<{ alerts: AlertRecord[] }>(config, "/alerts");
        if (!cancelled) {
          setAlerts(body.alerts);
          setLocalError(null);
          onError?.(null);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Could not load news cards";
          setLocalError(message);
          onError?.(message);
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [config, onError]);

  return (
    <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Official updates</p>
      <p className="mt-1 text-sm text-slate-600">
        Manual H-1B cards with a deep link to USCIS.gov. Not legal advice and not a USCIS or DHS
        endorsement. TurboImmi does not scrape X.
      </p>
      {localError ? <p className="mt-3 text-sm text-red-700">{localError}</p> : null}
      {busy ? (
        <p className="mt-3 text-sm text-slate-600">Loading cards…</p>
      ) : alerts.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">No cards yet.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {alerts.map((item) => (
            <li key={item.alertId} className="rounded-md border border-slate-200 px-3 py-3 text-sm">
              <p className="font-medium text-slate-800">{item.title}</p>
              <p className="mt-1 text-slate-600">
                {item.tag.replace("_", " ")} · {item.publishedOn}
              </p>
              <p className="mt-2 text-slate-700">{item.summary}</p>
              <a className="mt-2 inline-block underline" href={item.sourceUrl} target="_blank" rel="noreferrer">
                Verify on USCIS.gov
              </a>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-4">
        <p className="text-sm font-medium text-slate-800">Follow official accounts</p>
        <p className="mt-1 text-sm text-slate-600">{officialLinks.note}</p>
        <ul className="mt-3 space-y-1 text-sm">
          {officialLinks.links.map((link) => (
            <li key={link.url}>
              <a className="underline" href={link.url} target="_blank" rel="noreferrer">
                {link.title}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
