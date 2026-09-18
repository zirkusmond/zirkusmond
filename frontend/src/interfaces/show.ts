import type { HomepageElement } from "#/interfaces/homepage-element.ts";

export interface ShowCard {
  id: number;
  title: string;
  cardImage: string;
  eventDates: string[];
  soldOut: boolean;
}

export interface HomepageResponse {
  upcomingShows: ShowCard[];
  additionalElements: HomepageElement[];
}

export interface ShowEvent {
  id: string;
  timeAndDate: string;
  admissionTime: string;
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
  baseTicketPrice?: number;
  minTicketPrice?: number;
  maxTicketPrice?: number;
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
