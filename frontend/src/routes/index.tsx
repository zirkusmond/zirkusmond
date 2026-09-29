import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";

import EventsSection from "#/components/zirkusmond/home/EventsSection";
// import GallerySection from '#/components/zirkusmond/home/GallerySection'
import Hero from "#/components/zirkusmond/home/Hero";
import { homepageQueryOptions } from "#/lib/api.ts";
import PageContainer from "#/components/zirkusmond/general/PageContainer";
import ContactSection from "#/components/zirkusmond/home/ContactSection";
import OpenSource from "#/components/zirkusmond/home/OpenSource";
import HomepagePopup from "#/components/zirkusmond/home/django-admin-elements/popup/HomepagePopup";
import InlineSection from "#/components/zirkusmond/home/django-admin-elements/inline-section/InlineSection";
import type { InlineSectionElement } from "#/interfaces/homepage-element";
import SectionDivider from "#/components/zirkusmond/general/SectionDivider";

const App = () => {
  //
  // TanStack Query: resolves instantly from the cache filled by the loader
  // (no loading state needed); would suspend only on a cache miss.
  const { data } = useSuspenseQuery(homepageQueryOptions());
  const preShowSection = data.additionalElements.find(
    (el): el is InlineSectionElement => el.type === "preshowselement",
  );
  const postShowSection = data.additionalElements.find(
    (el): el is InlineSectionElement => el.type === "postshowselement",
  );

  return (
    <>
      <Hero heroImage={data.heroImage} />
      <PageContainer className="pt-0">
        {preShowSection && <InlineSection element={preShowSection} />}
        <EventsSection shows={data.upcomingShows} showAllEventsLink />
        {/* <GallerySection /> */}
        {postShowSection && <InlineSection element={postShowSection} />}
        <SectionDivider type="kite" />

        <ContactSection />
        <SectionDivider type="flower" />
        <OpenSource />
      </PageContainer>
      <HomepagePopup elements={data.additionalElements} />
    </>
  );
};

export const Route = createFileRoute("/")({
  // TanStack Query: `query` (with staleTime: "static") fetches into the cache
  // unless the data is already there — the non-deprecated replacement for
  // `ensureQueryData`. On the server this runs during SSR and the result is
  // dehydrated into the HTML; useSuspenseQuery below then reads it from cache.
  loader: ({ context: { queryClient }, preload }) =>
    queryClient.query({
      ...homepageQueryOptions({ preload }),
      staleTime: "static",
    }),
  head: () => ({
    meta: [
      { title: "Zirkus Mond" },
      {
        name: "description",
        content:
          "Zirkus Mond – Dein Zirkus in Berlin! Entdecke unser Programm: Live Shows, Events, Community und zeitgenössische Zirkuskunst im Herzen Berlins.",
      },
      {
        name: "keywords",
        content:
          "Zirkus Mond Berlin, Zirkus Mond Shows, Zirkus Mond Events, Zirkus Mond Tickets, Live Shows Berlin, Kulturveranstaltungen Berlin, zeitgenössischer Zirkus Berlin, unabhängiger Zirkus Berlin",
      },
    ],
  }),
  component: App,
});
