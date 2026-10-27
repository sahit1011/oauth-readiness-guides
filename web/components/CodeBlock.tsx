import { CopyButton } from "./CopyButton";

export function CodeBlock({ title, language, content }: { title: string; language: string | null; content: string }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-zinc-200 bg-[#f6f8fa]">
      <figcaption className="flex items-center justify-between gap-3 border-b border-zinc-200 bg-white px-3 py-1.5">
        <span className="truncate text-sm font-medium text-zinc-800">{title}</span>
        <span className="flex items-center gap-2">
          {language && <span className="font-mono text-xs text-zinc-500">{language}</span>}
          <CopyButton text={content} />
        </span>
      </figcaption>
      <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-6 text-zinc-800">{content}</pre>
    </figure>
  );
}
