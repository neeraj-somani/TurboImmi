import disclaimer from "../../../shared/disclaimer.json";

type Props = {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  note?: string;
};

export default function AttorneyReviewAttestation({ checked, onChange, disabled, note }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm font-medium text-slate-800">Attorney review before filing</p>
      <label className="mt-3 flex items-start gap-3 text-sm text-slate-700">
        <input
          type="checkbox"
          className="mt-1"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span>{disclaimer.attestation}</span>
      </label>
      <p className="mt-2 text-xs text-slate-500">{note ?? disclaimer.scoreNotOdds}</p>
    </div>
  );
}
