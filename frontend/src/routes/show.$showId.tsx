import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";

import PageContainer from "#/components/zirkusmond/general/PageContainer";
import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import { ShowDetails } from "#/components/zirkusmond/show/ShowDetails";
import { ReserveButton } from "#/components/zirkusmond/show/ReserveButton";
import TimeDetails from "#/components/zirkusmond/event/TimeDetails";
import { Button } from "#/components/ui/button.tsx";
import { ApiError, showQueryOptions } from "#/lib/api.ts";
import NotFound from "#/components/zirkusmond/general/NotFound";
import NavigationButtonWrapper from "#/components/zirkusmond/general/NavigationButtonWrapper";
import { useTranslation } from "react-i18next";
import { Home } from "lucide-react";

const RouteComponent = () => {
  const { t } = useTranslation();
  const { showId } = Route.useParams();
  // TanStack Query: same key as the loader, so this reads from the cache the
  // loader filled instead of fetching again.
  const { data: show } = useSuspenseQuery(showQueryOptions(showId));
  return (
    <PageContainer className="px-0 md:px-4">
      {show.bannerImage && (
        <img
          src={show.bannerImage}
          alt={`${show.title} Banner`}
          className="mx-auto w-full object-cover"
        />
      )}
      <div className="flex flex-wrap justify-center gap-6 py-8">
        {show.upcomingEvents.map((event) => (
          <TimeDetails
            key={event.id}
            date={event.timeAndDate}
            admissionTime={event.admissionTime}
            soldOut={event.soldOut}
          />
        ))}
      </div>

      <div className="my-8 flex justify-center">
        {show.soldOut ? (
          <h4 className="text-center">{t("show_sold_out")}</h4>
        ) : show.reservationOpen ? (
          <ReserveButton show={show} />
        ) : (
          <h4 className="text-center">{t("show_reservations_not_open")}</h4>
        )}
      </div>

      <SectionDivider type="flower" />

      <ShowDetails show={show} />
      <NavigationButtonWrapper>
        {show.reservationOpen && !show.soldOut && <ReserveButton show={show} />}
        <Button variant={"secondary"} asChild>
          <Link to="/">
            <Home />
            {t("common_home")}
          </Link>
        </Button>
      </NavigationButtonWrapper>
    </PageContainer>
  );
};

export const Route = createFileRoute("/show/$showId")({
  // TanStack Query: prefetch the show into the cache during SSR / navigation.
  // The data is also returned so `head` can use it as loaderData; a 404 from
  // the API is translated into the router's notFound page.
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
    meta: loaderData ? [{ title: `Zirkus Mond - ${loaderData.title}` }] : [],
  }),
  component: RouteComponent,
  notFoundComponent: () => <NotFound entityName="Show" />,
});
