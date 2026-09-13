export const JOURNEY_STAGES = [
  "f1",
  "cpt",
  "opt",
  "stem_opt",
  "h1b",
  "h4",
  "h4_ead",
  "perm",
  "i140",
  "aos",
] as const;

export type JourneyStage = (typeof JOURNEY_STAGES)[number];

export const JOURNEY_LABELS: Record<JourneyStage, string> = {
  f1: "F-1",
  cpt: "CPT",
  opt: "OPT",
  stem_opt: "STEM OPT",
  h1b: "H-1B",
  h4: "H-4",
  h4_ead: "H-4 EAD",
  perm: "PERM",
  i140: "I-140",
  aos: "AOS",
};

type Props = {
  stage: string;
};

export default function JourneyMap({ stage }: Props) {
  const current = JOURNEY_STAGES.includes(stage as JourneyStage) ? stage : "h1b";
  return (
    <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
      <p className="font-medium">Journey map</p>
      <p className="mt-1 text-sm text-slate-600">
        Stub of later stages. Only H-1B is in scope for this helper. Saving a stage does not mean
        you are approved for it.
      </p>
      <ol className="mt-4 flex flex-wrap gap-2">
        {JOURNEY_STAGES.map((value) => {
          const active = value === current;
          return (
            <li
              key={value}
              className={
                active
                  ? "rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white"
                  : "rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
              }
            >
              {JOURNEY_LABELS[value]}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
