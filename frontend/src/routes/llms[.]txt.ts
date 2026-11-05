import { createFileRoute } from "@tanstack/react-router";

import {
  fetchShow,
  fetchUpcomingShowCards,
  siteOrigin,
} from "#/lib/discovery.ts";
import type { DiscoveryShow } from "#/lib/discovery.ts";

const dateTimeFormat = new Intl.DateTimeFormat("de-DE", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Berlin",
});

const timeFormat = new Intl.DateTimeFormat("de-DE", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Berlin",
});

const formatDateTime = (iso: string): string =>
  dateTimeFormat.format(new Date(iso));

const formatTime = (iso: string): string => timeFormat.format(new Date(iso));

const priceText = (show: DiscoveryShow): string => {
  if (show.reservation_price !== null) {
    return `${show.reservation_price} ${show.currency} Reservierungsgebühr, Restbetrag an der Abendkasse`;
  }
  if (show.effective_min_price === null) {
    return "Keine Preise hinterlegt";
  }
  if (
    show.effective_max_price !== null &&
    show.effective_max_price > show.effective_min_price
  ) {
    return `${show.effective_min_price}–${show.effective_max_price} ${show.currency} (Selbstpreis-Skala)`;
  }
  return `${show.effective_min_price} ${show.currency}`;
};

const eventText = (show: DiscoveryShow): string => {
  if (show.upcoming_events.length === 0) {
    return "  - Keine kommenden Termine angekündigt";
  }
  return show.upcoming_events
    .map((event) => {
      const status = event.sold_out
        ? "ausverkauft"
        : event.reservation_open
          ? `${event.remaining_capacity} Plätze frei`
          : "Reservierung geschlossen";
      return `  - ${formatDateTime(event.begin)} (Einlass ${formatTime(
        event.admission,
      )}): ${status}`;
    })
    .join("\n");
};

const bookingText = (show: DiscoveryShow, origin: string): string => {
  if (show.third_party_reservation) {
    return show.third_party_reservation_link
      ? `  - Tickets: ${show.third_party_reservation_link} (externer Anbieter)`
      : "  - Tickets: externer Anbieter";
  }
  if (show.sold_out) {
    return "  - Tickets: ausverkauft";
  }
  if (!show.reservation_open) {
    return "  - Tickets: Reservierung derzeit geschlossen";
  }
  return `  - Tickets: ${origin}/reserve/${show.id}`;
};

const buildShowSection = (show: DiscoveryShow, origin: string): string =>
  `### ${show.title}

- Seite: ${origin}/shows/${show.id}
- Preise: ${priceText(show)}
${bookingText(show, origin)}
- Termine:
${eventText(show)}`;

const buildLlmsTxt = (origin: string, shows: DiscoveryShow[]): string => {
  const showSections = shows
    .map((show) => buildShowSection(show, origin))
    .join("\n\n");

  return `# Zirkus Mond

> Zirkus Mond ist ein Veranstaltungsort für zeitgenössischen Zirkus, Theater, Tanz und Konzerte in Berlin-Friedrichshain. Das Programm umfasst eigene Produktionen und Gastveranstaltungen.

## Standort und Kontakt

- Spielstätte: Rudolfstr. 14c, 10245 Berlin
- Betreiber: Kultstätte 58 GmbH, Körtestraße 38, 10967 Berlin
- E-Mail: maxmohr@posteo.de
- Telefon: +49 157 70280810
- Website: ${origin}

## Maschinenlesbare Daten

- Alle kommenden Shows: ${origin}/api/shows/
- Einzelne Show (Termine, Preise, Kapazität): ${origin}/api/shows/<id>
- Sitemap: ${origin}/sitemap.xml

Alle API-Antworten sind JSON. Datumsangaben mit den Feldern \`begin\` und \`admission\` sind ISO-8601-Zeitstempel, Preise sind in EUR.

## Shows und Termine

${showSections || "Derzeit sind keine kommenden Shows veröffentlicht."}

## Weitere Seiten

- Alle Shows: ${origin}/shows
- Über uns: ${origin}/about
- Kontakt: ${origin}/contact
- Vermietung: ${origin}/rentals
- Impressum: ${origin}/impressum
- Datenschutz: ${origin}/datenschutz
`;
};

export const Route = createFileRoute("/llms.txt")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const origin = siteOrigin(request);
        const cards = await fetchUpcomingShowCards().catch(() => []);
        const shows = (
          await Promise.all(
            cards.map((card) => fetchShow(card.id).catch(() => null)),
          )
        ).filter((show): show is DiscoveryShow => show !== null);

        return new Response(buildLlmsTxt(origin, shows), {
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=600",
          },
        });
      },
    },
  },
});
