import type { Show, ShowCard } from "#/interfaces/show.ts";

type JsonLdValue =
  string | number | boolean | null | JsonLdObject | JsonLdValue[];

interface JsonLdObject {
  [key: string]: JsonLdValue | undefined;
}

export const SITE_URL = "https://zirkusmond.de";

const ORGANIZATION_NAME = "Zirkus Mond";
const ORGANIZATION_LEGAL_NAME = "Kultstätte 58 GmbH";

const POSTAL_ADDRESS = {
  "@type": "PostalAddress",
  streetAddress: "Körtestraße 38",
  postalCode: "10967",
  addressLocality: "Berlin",
  addressCountry: "DE",
} as const;

const VENUE_ADDRESS = {
  "@type": "PostalAddress",
  streetAddress: "Rudolfstr. 14c",
  postalCode: "10245",
  addressLocality: "Berlin",
  addressCountry: "DE",
} as const;

export const organizationJsonLd = (): JsonLdObject => ({
  "@context": "https://schema.org",
  "@type": "Organization",
  name: ORGANIZATION_NAME,
  legalName: ORGANIZATION_LEGAL_NAME,
  url: SITE_URL,
  logo: `${SITE_URL}/images/logos/logo.webp`,
  email: "maxmohr@posteo.de",
  telephone: "+49 157 70280810",
  address: POSTAL_ADDRESS,
});

export const websiteJsonLd = (): JsonLdObject => ({
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: ORGANIZATION_NAME,
  url: SITE_URL,
  inLanguage: "de",
  publisher: {
    "@type": "Organization",
    name: ORGANIZATION_NAME,
    url: SITE_URL,
  },
});

const absoluteUrl = (url: string | undefined | null): string | null => {
  if (!url) return null;
  return url.startsWith("http") ? url : `${SITE_URL}${url}`;
};

export const plainText = (html: string): string =>
  html
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();

const images = (show: Show): string[] =>
  [absoluteUrl(show.bannerImage), absoluteUrl(show.cardImage)].filter(
    (image): image is string => image !== null,
  );

const offersForShow = (show: Show): JsonLdObject | null => {
  const lowPrice =
    show.effectiveMinPrice ?? show.reservationPrice ?? show.baseTicketPrice;
  if (lowPrice == null) return null;

  const highPrice = show.effectiveMaxPrice ?? lowPrice;
  const priceCurrency = show.currency ?? "EUR";
  const url = `${SITE_URL}/reserve/${show.id}`;

  if (highPrice > lowPrice) {
    return {
      "@type": "AggregateOffer",
      lowPrice,
      highPrice,
      priceCurrency,
      offerCount: 1,
      url,
    };
  }

  return {
    "@type": "Offer",
    price: lowPrice,
    priceCurrency,
    url,
  };
};

export const showJsonLd = (show: Show): JsonLdObject => {
  const offer = offersForShow(show);

  return {
    "@context": "https://schema.org",
    "@graph": show.upcomingEvents.map((event) => ({
      "@type": "Event",
      name: show.title,
      description: plainText(show.description).slice(0, 500),
      image: images(show),
      startDate: event.begin,
      doorTime: event.admission,
      eventStatus: "https://schema.org/EventScheduled",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      url: `${SITE_URL}/shows/${show.id}`,
      location: {
        "@type": "Place",
        name: ORGANIZATION_NAME,
        address: VENUE_ADDRESS,
      },
      organizer: {
        "@type": "Organization",
        name: ORGANIZATION_NAME,
        url: SITE_URL,
      },
      ...(offer
        ? {
            offers: {
              ...offer,
              availability:
                event.soldOut || !event.reservationOpen
                  ? "https://schema.org/SoldOut"
                  : "https://schema.org/InStock",
            },
          }
        : {}),
    })),
  };
};

export const showListJsonLd = (shows: ShowCard[]): JsonLdObject => ({
  "@context": "https://schema.org",
  "@type": "ItemList",
  itemListElement: shows.map((show, index) => ({
    "@type": "ListItem",
    position: index + 1,
    name: show.title,
    url: `${SITE_URL}/shows/${show.id}`,
  })),
});
