"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useGenerate } from "./GenerateContext";
import { SearchIcon } from "./icons";

export type CatalogApp = { slug: string; name: string; website: string | null; categories: string[]; managed: boolean };

export function Catalog({ apps, inLibrary }: { apps: CatalogApp[]; inLibrary: string[] }) {
  const { generate } = useGenerate();
  const [filter, setFilter] = useState("");
  const library = useMemo(() => new Set(inLibrary), [inLibrary]);

  const shown = apps.filter((a) => {
    const q = filter.trim().toLowerCase();
    return q === "" || a.name.toLowerCase().includes(q) || a.categories.some((c) => c.toLowerCase().includes(q));
  });

  return (
    <div className="flex flex-col gap-3">
      <label className="relative">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={`Filter ${apps.length} apps by name or category`}
          className="w-full rounded-lg border border-zinc-300 bg-white py-2 pl-9 pr-3 text-sm text-zinc-900 outline-none placeholder:text-zinc-400 focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
        />
      </label>
      {/* Fixed-height box that scrolls on its own, so browsing all apps doesn't scroll the page. */}
      <div className="h-[28rem] overflow-auto rounded-xl border border-zinc-200">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-zinc-50 text-xs uppercase tracking-wider text-zinc-500 shadow-[0_1px_0_0_#e4e4e7]">
            <tr>
              <th className="px-4 py-2.5 font-semibold">App</th>
              <th className="px-4 py-2.5 font-semibold">Category</th>
              <th className="px-4 py-2.5 font-semibold">Composio managed app</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {shown.map((a) => (
              <tr key={a.slug}>
                <td className="px-4 py-2.5 font-medium text-zinc-900">{a.name}</td>
                <td className="px-4 py-2.5 text-zinc-600">{a.categories.slice(0, 2).join(", ")}</td>
                <td className="px-4 py-2.5">
                  {a.managed ? (
                    <span className="text-emerald-700">Yes, start without your own app</span>
                  ) : (
                    <span className="text-zinc-700">No, bring your own app</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right">
                  {library.has(a.slug) ? (
                    <Link href={`/apps/${a.slug}`} className="font-medium text-sky-700 hover:underline">
                      Read guide
                    </Link>
                  ) : (
                    <button onClick={() => generate(a.name)} className="font-medium text-zinc-700 hover:text-zinc-900 hover:underline">
                      Generate guide
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-zinc-500">
        {shown.length === 0 ? `No app matches “${filter}”. You can still generate a guide for it above.` : `Showing ${shown.length} of ${apps.length} apps.`}
      </p>
    </div>
  );
}
