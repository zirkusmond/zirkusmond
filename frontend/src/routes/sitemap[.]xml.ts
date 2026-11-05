import { createFileRoute } from "@tanstack/react-router";

import { fetchUpcomingShowCards, siteOrigin } from "#/lib/discovery.ts";

const STATIC_PATHS = [
  "/",
  "/shows",
  "/about",
  "/contact",
  "/rentals",
  "/impressum",
  "/datenschutz",
];

const escapeXml = (value: string): string =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

const buildSitemap = (origin: string, showIds: number[]): string => {
  const staticEntries = STATIC_PATHS.map(
    (path) => `  <url>
    <loc>${escapeXml(`${origin}${path}`)}</loc>
    <changefreq>${path === "/shows" ? "daily" : "weekly"}</changefreq>
    <priority>${path === "/" ? "1.0" : "0.7"}</priority>
  </url>`,
  );

  const showEntries = showIds.map(
    (id) => `  <url>
    <loc>${escapeXml(`${origin}/shows/${id}`)}</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>`,
  );

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${[...staticEntries, ...showEntries].join("\n")}
</urlset>
`;
};

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const shows = await fetchUpcomingShowCards().catch(() => []);
        const body = buildSitemap(
          siteOrigin(request),
          shows.map((show) => show.id),
        );

        return new Response(body, {
          headers: {
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
          },
        });
      },
    },
  },
});
