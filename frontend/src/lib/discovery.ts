import { SERVER_API_URL } from "#/lib/api.ts";

export interface DiscoveryEvent {
  id: number;
  begin: string;
  admission: string;
  time_and_date: string;
  reservation_capacity: number;
  remaining_capacity: number;
  reservation_open: boolean;
  sold_out: boolean;
}

export interface DiscoveryShowCard {
  id: number;
  title: string;
  event_dates: string[];
  event_dates_iso: string[];
  sold_out: boolean;
}

export interface DiscoveryShow {
  id: number;
  title: string;
  description: string;
  currency: string;
  base_ticket_price: number | null;
  min_ticket_price: number | null;
  max_ticket_price: number | null;
  effective_min_price: number | null;
  effective_max_price: number | null;
  reservation_price: number | null;
  reservation_open: boolean;
  sold_out: boolean;
  third_party_reservation: boolean;
  third_party_reservation_link: string;
  upcoming_events: DiscoveryEvent[];
}

export const siteOrigin = (request: Request): string => {
  const url = new URL(request.url);
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const proto =
    forwardedProto?.split(",")[0]?.trim() || url.protocol.replace(":", "");
  const host = request.headers.get("host") || url.host;
  return `${proto}://${host}`;
};

export const fetchUpcomingShowCards = async (): Promise<
  DiscoveryShowCard[]
> => {
  const response = await fetch(`${SERVER_API_URL}/shows/`);
  if (!response.ok) {
    throw new Error(`Failed to load shows: ${response.status}`);
  }
  const data = (await response.json()) as {
    upcoming_shows?: DiscoveryShowCard[];
  };
  return data.upcoming_shows ?? [];
};

export const fetchShow = async (showId: number): Promise<DiscoveryShow> => {
  const response = await fetch(`${SERVER_API_URL}/shows/${showId}`);
  if (!response.ok) {
    throw new Error(`Failed to load show ${showId}: ${response.status}`);
  }
  const data = (await response.json()) as { show: DiscoveryShow };
  return data.show;
};
