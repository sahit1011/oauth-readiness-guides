import type { Claim } from "@/lib/types";
import { EvidenceBadge } from "./badges";

export function ClaimView({ claim }: { claim: Claim }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[15px] leading-6 text-zinc-800">
        <EvidenceBadge status={claim.status} /> <span className="ml-1">{claim.statement}</span>
        {claim.source_ids.map((id) => (
          <a key={id} href={`#source-${id}`} className="ml-1 align-super text-[11px] font-medium text-sky-700 hover:underline">
            {id}
          </a>
        ))}
      </p>
      {/* Only a verified quote is shown: after a downgrade the original "quote" is exactly what failed the check. */}
      {claim.status === "sourced" && claim.quote && (
        <blockquote className="rounded-md border-l-2 border-sky-300 bg-zinc-50 px-3 py-1.5 text-sm leading-6 text-zinc-700">“{claim.quote}”</blockquote>
      )}
    </div>
  );
}

export function ClaimList({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) return null;
  return (
    <ul className="flex flex-col gap-3">
      {claims.map((c, i) => (
        <li key={i}>
          <ClaimView claim={c} />
        </li>
      ))}
    </ul>
  );
}

/** Evidence folded away so steps read as instructions first. */
export function EvidenceDetails({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) return null;
  return (
    <details className="group rounded-lg border border-zinc-200 bg-white px-3 py-2">
      <summary className="cursor-pointer select-none text-sm font-medium text-zinc-700 group-open:mb-2">Evidence ({claims.length})</summary>
      <ClaimList claims={claims} />
    </details>
  );
}
