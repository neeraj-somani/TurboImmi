import { Link } from "react-router-dom";
import disclaimer from "../../../shared/disclaimer.json";

export default function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-slate-200 pt-6 text-sm text-slate-600">
      <p>{disclaimer.short}</p>
      <p className="mt-2">
        <Link className="underline" to={disclaimer.tosPath}>
          Terms of Service
        </Link>
        {" · "}
        <Link className="underline" to={disclaimer.privacyPath}>
          Privacy Policy
        </Link>
        <span className="text-slate-500"> (draft — counsel review)</span>
      </p>
    </footer>
  );
}
