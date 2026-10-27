"use client";

import { useEffect, useState } from "react";

/** "On this page" list that highlights the section currently in view. */
export function Toc({ items }: { items: [id: string, title: string][] }) {
  const [active, setActive] = useState(items[0]?.[0]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      // Count a section as current once its heading passes the top fifth of the viewport.
      { rootMargin: "0px 0px -80% 0px" },
    );
    for (const [id] of items) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [items]);

  return (
    <nav aria-label="On this page" className="text-sm">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">On this page</p>
      <ul className="flex flex-col border-l border-zinc-200">
        {items.map(([id, title]) => (
          <li key={id}>
            <a
              href={`#${id}`}
              className={`-ml-px block border-l py-1 pl-3 leading-5 ${
                active === id ? "border-zinc-900 font-medium text-zinc-900" : "border-transparent text-zinc-600 hover:text-zinc-900"
              }`}
            >
              {title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
