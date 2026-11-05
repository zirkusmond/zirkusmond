import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";

import EventsSection from "#/components/zirkusmond/home/EventsSection";
import PageContainer from "#/components/zirkusmond/general/PageContainer";
import { allShowsQueryOptions } from "#/lib/api.ts";
import { showListJsonLd } from "#/lib/structuredData.ts";

const RouteComponent = () => {
  // TanStack Query: reads the cache entry the loader ensured; no loading state.
  const { data } = useSuspenseQuery(allShowsQueryOptions());

  return (
    <PageContainer>
      <EventsSection shows={data.upcomingShows} showHomeLink />
    </PageContainer>
  );
};

export const Route = createFileRoute("/shows")({
  // TanStack Query: prefetch into the cache during SSR / navigation.
  loader: ({ context: { queryClient }, preload }) =>
    queryClient.query({
      ...allShowsQueryOptions({ preload }),
      staleTime: "static",
    }),
  head: ({ loaderData }) => ({
    meta: [
      { title: "Zirkus Mond – Shows & Events" },
      {
        name: "description",
        content:
          "Alle Shows und Events im Zirkus Mond Berlin – Trapez, Akrobatik, Cabaret, Varieté, Physical Theatre und mehr. Jetzt Tickets sichern!",
      },
      {
        name: "keywords",
        content:
          "Zirkus Shows Berlin, Zirkus Events Berlin, Live Shows Berlin, Trapez, Akrobatik Berlin, Cabaret, Varieté, Physical Theatre, Familien Events Berlin",
      },
      ...(loaderData
        ? [{ "script:ld+json": showListJsonLd(loaderData.upcomingShows) }]
        : []),
    ],
  }),
  component: RouteComponent,
});
