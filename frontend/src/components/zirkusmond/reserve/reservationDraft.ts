import { useEffect } from "react";

export interface GuestFormData {
  firstName: string;
  lastName: string;
  email: string;
  guests: { firstName: string; lastName: string }[];
}

export interface ReservationDraft extends GuestFormData {
  // Persisted so returning from the payment step (back button, PayPal cancel,
  // "try again", reload) restores the date the customer picked instead of
  // silently falling back to a default.
  eventId?: string;
  attendeeCount: number;
  customPrice?: number;
  newsletter: boolean;
}

export const extractGuestFormData = (
  formData: FormData,
  guestCount: number,
): GuestFormData => {
  const guests: GuestFormData["guests"] = [];

  for (let i = 0; i < guestCount; i++) {
    guests.push({
      firstName: formData.get(`guest-${i}-first-name`) as string,
      lastName: formData.get(`guest-${i}-last-name`) as string,
    });
  }

  return {
    firstName: formData.get("firstName") as string,
    lastName: formData.get("lastName") as string,
    email: formData.get("email") as string,
    guests,
  };
};

const DRAFT_KEY = "reservation-draft";

export const loadDraft = (): ReservationDraft | null => {
  if (typeof window === "undefined") return null;

  const draftJson = sessionStorage.getItem(DRAFT_KEY);
  if (!draftJson) return null;

  try {
    return JSON.parse(draftJson);
  } catch (error) {
    console.error(
      `Failed to parse field inputs: ${draftJson}, error: ${error}`,
    );
    return null;
  }
};

export const saveDraft = (draft: ReservationDraft) => {
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
};

const EMPTY_DRAFT: ReservationDraft = {
  firstName: "",
  lastName: "",
  email: "",
  guests: [],
  attendeeCount: 1,
  newsletter: false,
};

// Merge a partial update into the stored draft. The text inputs (uncontrolled,
// read from the DOM on form change) and the controlled state (event, ticket
// count, price, newsletter) are saved independently, so neither overwrites the
// other with stale values.
export const updateDraft = (partial: Partial<ReservationDraft>) => {
  if (typeof window === "undefined") return;
  saveDraft({ ...EMPTY_DRAFT, ...loadDraft(), ...partial });
};

// Returns the saved event if it can still be booked, otherwise the only
// bookable event when there is exactly one, otherwise "" (customer must pick).
// Never defaults to the first of several dates: that silently booked the
// wrong date for customers retrying a payment.
export const resolveInitialEventId = (
  bookableEventIds: string[],
  savedEventId: string | undefined,
): string => {
  if (savedEventId && bookableEventIds.includes(savedEventId)) {
    return savedEventId;
  }
  return bookableEventIds.length === 1 ? bookableEventIds[0] : "";
};

export const clearDraft = () => {
  sessionStorage.removeItem(DRAFT_KEY);
};

export const setFormValue = (name: string, value: string | undefined) => {
  if (value === undefined) return;

  const form = document.getElementById(
    "reservation-form",
  ) as HTMLFormElement | null;
  if (!form) return;

  const el = form.elements.namedItem(name);
  if (el instanceof HTMLInputElement) el.value = value;
};

export const useFormStorage = (savedInputs: ReservationDraft | null) => {
  useEffect(() => {
    if (!savedInputs) return;

    setFormValue("firstName", savedInputs.firstName);
    setFormValue("lastName", savedInputs.lastName);
    setFormValue("email", savedInputs.email);

    savedInputs.guests.forEach((guest, i) => {
      setFormValue(`guest-${i}-first-name`, guest.firstName);
      setFormValue(`guest-${i}-last-name`, guest.lastName);
    });
  });
};
