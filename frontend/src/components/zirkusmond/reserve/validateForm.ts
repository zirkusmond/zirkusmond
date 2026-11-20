import type { TFunction } from "i18next";
import type { GuestFormData } from "./reservationDraft.ts";

const EMAIL_REGEX =
  /^[^\s@.]+(?:\.[^\s@.]+)*@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

export const isValidEmail = (email: string): boolean => EMAIL_REGEX.test(email);

export const validateReservationForm = (
  guestFormData: GuestFormData,
  guestCount: number,
  eventId: string,
  t: TFunction,
): Record<string, string> => {
  const { firstName, lastName, email } = guestFormData;
  const GENERIC_ERROR = t("form_error_required");
  const errors: Record<string, string> = {};

  // First, so it's the field that gets focus when several are missing.
  if (!eventId) {
    errors["event"] = t("form_error_event_required");
  }
  if (!firstName) {
    errors["first-name"] = GENERIC_ERROR;
  }
  if (!lastName) {
    errors["last-name"] = GENERIC_ERROR;
  }
  if (!email) {
    errors["email"] = GENERIC_ERROR;
  } else if (!isValidEmail(email)) {
    errors["email"] = t("form_error_invalid_email");
  }

  for (let i = 0; i < guestCount; i++) {
    const { firstName: guestFirstName, lastName: guestLastName } =
      guestFormData.guests[i];

    if (!guestFirstName) {
      errors[`guest-${i}-first-name`] = GENERIC_ERROR;
    }
    if (!guestLastName) {
      errors[`guest-${i}-last-name`] = GENERIC_ERROR;
    }
  }

  return errors;
};

export const clearFieldError = (
  fieldErrors: Record<string, string>,
  id: string,
): Record<string, string> => {
  if (!(id in fieldErrors)) return fieldErrors;
  const next = { ...fieldErrors };
  delete next[id];
  return next;
};
