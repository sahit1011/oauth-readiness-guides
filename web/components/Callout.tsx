import { CheckIcon, InfoIcon, WarningIcon } from "./icons";

const VARIANT = {
  note: { box: "border-sky-200 bg-sky-50/60", icon: "text-sky-700", Icon: InfoIcon },
  warning: { box: "border-amber-200 bg-amber-50/70", icon: "text-amber-700", Icon: WarningIcon },
  success: { box: "border-emerald-200 bg-emerald-50/60", icon: "text-emerald-700", Icon: CheckIcon },
} as const;

export function Callout({ variant, title, children }: { variant: keyof typeof VARIANT; title?: string; children: React.ReactNode }) {
  const v = VARIANT[variant];
  return (
    <div className={`flex gap-3 rounded-lg border px-4 py-3 ${v.box}`}>
      <v.Icon className={`mt-0.5 h-5 w-5 shrink-0 ${v.icon}`} />
      <div className="flex min-w-0 flex-col gap-1 text-[15px] leading-6 text-zinc-800">
        {title && <p className="font-semibold text-zinc-900">{title}</p>}
        {children}
      </div>
    </div>
  );
}
