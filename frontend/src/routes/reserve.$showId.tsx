import { createFileRoute, notFound } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";

import PageContainer from "#/components/zirkusmond/general/PageContainer";
import ReservationPage from "#/components/zirkusmond/reserve/ReservationPage";
import { ApiError, showQueryOptions } from "#/lib/api.ts";
import PageHeader from "#/components/zirkusmond/general/PageHeader";

const RouteComponent = () => {
  const { showId } = Route.useParams();
  // TanStack Query: reads the cache entry the loader ensured; suspends only
  // on a cache miss.
  const { data: show } = useSuspenseQuery(showQueryOptions(showId));

  return (
    <PageContainer>
      <PageHeader>{show.title}</PageHeader>
      <ReservationPage show={show} />
    </PageContainer>
  );
};

export const Route = createFileRoute("/reserve/$showId")({
  // TanStack Query: same query as /shows/$showId, so a user coming from the
  // show page gets an instant render from cache; a 404 becomes notFound.
  loader: async ({ context: { queryClient }, params, preload }) => {
    try {
      return await queryClient.query({
        ...showQueryOptions(params.showId, { preload }),
        staleTime: "static",
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) throw notFound();
      throw error;
    }
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [{ title: `Zirkus Mond Reservation - ${loaderData.title}` }]
      : [],
  }),
  component: RouteComponent,
});
