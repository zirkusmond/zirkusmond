import { createFileRoute, notFound } from "@tanstack/react-router";
import { queryOptions, useSuspenseQuery } from "@tanstack/react-query";

import ContentSection from "#/components/zirkusmond/general/ContentSection";
import PageContainer from "#/components/zirkusmond/general/PageContainer";
import PageHeader from "#/components/zirkusmond/general/PageHeader";
import SectionCard from "#/components/zirkusmond/general/SectionCard";
import { ApiError, fetchJson } from "#/lib/api.ts";

interface ShowStatsSearch {
  token: string;
}

const validateShowStatsSearch = (
  search: Record<string, unknown>,
): ShowStatsSearch => {
  return {
    token: typeof search.token === "string" ? search.token : "",
  };
};

interface ShowStatsEvent {
  id: number;
  timeAndDate: string;
  reservationCapacity: number;
  reservedTickets: number;
  revenue: number;
}

interface ShowStats {
  showTitle: string;
  events: ShowStatsEvent[];
  // totals: {
  //   reservationCapacity: number;
  //   reservedTickets: number;
  //   checkedInTickets: number;
  // };
}

const showStatsQueryOptions = (
  showId: string,
  token: string,
  opts?: { preload?: boolean },
) =>
  queryOptions({
    queryKey: ["showStats", showId, token],
    queryFn: () =>
      fetchJson<ShowStats>(
        `/shows/${showId}/stats?token=${encodeURIComponent(token)}`,
        opts,
      ),
  });

const RouteComponent = () => {
  const { showId } = Route.useParams();
  const { token } = Route.useSearch();
  const { data: stats } = useSuspenseQuery(
    showStatsQueryOptions(showId, token),
  );
  console.log(stats);
  return (
    <PageContainer>
      <PageHeader>Show ticket sales for {stats.showTitle}</PageHeader>

      <ContentSection className="text-white max-w-2xl mx-auto">
        {stats.events.map((e) => (
          <SectionCard className="space-y-6">
            <h4>{e.timeAndDate}</h4>
          </SectionCard>
        ))}
      </ContentSection>
    </PageContainer>
  );
};

export const Route = createFileRoute("/shows_/$showId/stats")({
  validateSearch: validateShowStatsSearch,
  loaderDeps: ({ search }) => ({ token: search.token }),
  loader: async ({ context: { queryClient }, params, deps, preload }) => {
    try {
      return await queryClient.query({
        ...showStatsQueryOptions(params.showId, deps.token, { preload }),
        staleTime: "static",
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `Zirkus Mond – ${loaderData.showTitle}` },
          {
            name: "description",
            content: `Ticketverkauf für ${loaderData.showTitle}`,
          },
        ]
      : [],
  }),
  component: RouteComponent,
});
