import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import SiteFooter from "../components/SiteFooter";

type Props = {
  title: string;
  children: ReactNode;
};

export default function LegalPage({ title, children }: Props) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500">TurboImmi</p>
        <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Draft — counsel review. Not a final Terms of Service or Privacy Policy.
        </p>
        <div className="mt-6 space-y-4 text-slate-700">{children}</div>
        <p className="mt-8 text-sm">
          <Link className="underline" to="/">
            Back to home
          </Link>
        </p>
        <SiteFooter />
      </div>
    </main>
  );
}
