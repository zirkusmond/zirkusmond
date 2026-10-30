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
  totals: {
    reservationCapacity: number;
    reservedTickets: number;
    revenue: number;
  };
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

const formatRevenue = (value: number) =>
  new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(value);

const RouteComponent = () => {
  const { showId } = Route.useParams();
  const { token } = Route.useSearch();
  const { data: stats } = useSuspenseQuery(
    showStatsQueryOptions(showId, token),
  );

  return (
    <PageContainer>
      <PageHeader>Show ticket sales for {stats.showTitle}</PageHeader>
      <h5 className="text-white text-center">
        This page is only visible to people with the link
      </h5>
      <ContentSection className="text-white max-w-3xl mx-auto">
        <SectionCard>
          <table className="block w-full text-left md:table">
            <thead className="hidden md:table-header-group">
              <tr className="border-b border-white/40 text-lg uppercase tracking-wide text-primary">
                <th className="pb-3 pr-4 font-semibold">Event</th>
                <th className="px-4 pb-3 text-right font-semibold">
                  Tickets sold
                </th>
                <th className="pb-3 pl-4 text-right font-semibold">Revenue</th>
              </tr>
            </thead>
            <tbody className="block md:table-row-group">
              {stats.events.map((event) => (
                <tr
                  key={event.id}
                  className="mb-3 block  border border-white/50 p-4 last:mb-0 md:mb-0 md:table-row md:border-0 md:border-b md:p-0"
                >
                  <td className="flex items-center justify-between gap-4 py-1 md:table-cell md:py-3 md:pr-4">
                    <span className="font-semibold text-white/70 md:hidden">
                      Event
                    </span>
                    <span className="text-base">{event.timeAndDate}</span>
                  </td>
                  <td className="flex items-center justify-between gap-4 py-1 md:table-cell md:px-4 md:py-3 md:text-right">
                    <span className="font-semibold text-white/70 md:hidden">
                      Tickets sold
                    </span>
                    <span className="text-base">
                      {event.reservedTickets} / {event.reservationCapacity}
                    </span>
                  </td>
                  <td className="flex items-center justify-between gap-4 py-1 md:table-cell md:py-3 md:pl-4 md:text-right">
                    <span className="font-semibold text-white/70 md:hidden">
                      Revenue
                    </span>
                    <span className="text-base">
                      {formatRevenue(Number(event.revenue))}
                    </span>
                  </td>
                </tr>
              ))}
              {stats.events.length === 0 && (
                <tr className="block md:table-row">
                  <td
                    colSpan={3}
                    className="block py-6 text-center text-base text-white/70 md:table-cell"
                  >
                    No events yet.
                  </td>
                </tr>
              )}
            </tbody>
            {stats.events.length > 0 && (
              <tfoot className="block md:table-footer-group">
                <tr className="mt-4 block  border border-white/20 p-4 font-semibold text-lg md:mt-0 md:table-row md:ne md:border-0 md:border-t md:border-white/40">
                  <td className="block pb-2 md:table-cell md:pb-0 md:pr-4 md:pt-3">
                    Total
                  </td>
                  <td className="flex items-center justify-between gap-4 py-1 md:table-cell md:px-4 md:pt-3 md:text-right">
                    <span className="text-base font-semibold text-white/70 md:hidden">
                      Tickets sold
                    </span>
                    <span className="text-base md:text-lg">
                      {stats.totals.reservedTickets} /{" "}
                      {stats.totals.reservationCapacity}
                    </span>
                  </td>
                  <td className="flex items-center justify-between gap-4 py-1 md:table-cell md:pl-4 md:pt-3 md:text-right">
                    <span className="text-base font-semibold text-white/70 md:hidden">
                      Revenue
                    </span>
                    <span className="text-base md:text-lg">
                      {formatRevenue(Number(stats.totals.revenue))}
                    </span>
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </SectionCard>
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
