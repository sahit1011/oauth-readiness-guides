import type { NextRequest } from "next/server";
import { getGuide } from "@/lib/api";
import { guideToMarkdown } from "@/lib/markdown";

export async function GET(request: NextRequest, ctx: RouteContext<"/apps/[slug]/markdown">) {
  const { slug } = await ctx.params;
  const version = request.nextUrl.searchParams.get("v");
  const stored = await getGuide(slug, version);
  if (stored === null) return new Response(`No guide for ${slug}`, { status: 404 });
  const pageUrl = new URL(`/apps/${slug}${version ? `?v=${version}` : ""}`, request.nextUrl.origin).toString();
  return new Response(guideToMarkdown(stored, pageUrl), {
    headers: {
      "content-type": "text/markdown; charset=utf-8",
      "content-disposition": `attachment; filename="${slug}-oauth-guide.md"`,
    },
  });
}
