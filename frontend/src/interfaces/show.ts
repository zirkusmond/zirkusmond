import type { HomepageElement } from "#/interfaces/homepage-element.ts";

export interface ShowCard {
  id: number;
  title: string;
  cardImage: string;
  eventDates: string[];
  eventDatesIso: string[];
  soldOut: boolean;
}

export interface HeroImage {
  id: number;
  image: string;
  mobileImage?: string;
  active: boolean;
}

export interface HomepageResponse {
  upcomingShows: ShowCard[];
  additionalElements: HomepageElement[];
  heroImage: HeroImage | null;
}

export interface ShowEvent {
  id: string;
  timeAndDate: string;
  admissionTime: string;
  begin: string;
  admission: string;
  reservationCapacity: number;
  remainingCapacity: number;
  reservationOpen: boolean;
  soldOut: boolean;
}

export interface Show {
  id: number;
  title: string;
  description: string;
  cast: string;
  cardImage: string;
  bannerImage?: string;
  videoLink?: string;
  websiteLink?: string;
  currency?: string;
  baseTicketPrice?: number;
  minTicketPrice?: number;
  maxTicketPrice?: number;
  effectiveMinPrice?: number | null;
  effectiveMaxPrice?: number | null;
  reservationPrice?: number;
  thirdPartyReservation?: boolean;
  thirdPartyReservationLink?: string;
  upcomingEvents: ShowEvent[];
  lastModified: string;
  reservationOpen: boolean;
  soldOut: boolean;
}

export interface ShowDetailResponse {
  show: Show;
}
