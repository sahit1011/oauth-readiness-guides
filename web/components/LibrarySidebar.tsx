import Link from "next/link";
import { listGuides } from "@/lib/api";
import type { Tier } from "@/lib/types";

const DOT: Record<Tier, string> = {
  instant: "bg-emerald-500",
  easy: "bg-lime-500",
  moderate: "bg-amber-500",
  high: "bg-orange-500",
  restricted: "bg-red-500",
};

export async function LibrarySidebar({ current }: { current: string }) {
  const guides = await listGuides();
  return (
    <nav aria-label="Library" className="text-sm">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Library</p>
      <ul className="flex flex-col gap-0.5">
        {guides.map((g) => (
          <li key={g.slug}>
            <Link
              href={`/apps/${g.slug}`}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 ${
                g.slug === current ? "bg-zinc-100 font-medium text-zinc-900" : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
              }`}
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[g.tier.likely]}`} />
              {g.app_name}
            </Link>
          </li>
        ))}
      </ul>
      <Link href="/#generate" className="mt-4 block px-2 text-sky-700 hover:underline">
        + Generate another app
      </Link>
    </nav>
  );
}
