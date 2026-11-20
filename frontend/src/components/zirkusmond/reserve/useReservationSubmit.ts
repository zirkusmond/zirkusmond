import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import type { Show } from "#/interfaces/show.ts";
import { useCreateReservation, createPaymentIntent } from "#/lib/payments.ts";
import { clearFieldError, validateReservationForm } from "./validateForm.ts";
import { extractGuestFormData, updateDraft } from "./reservationDraft.ts";

interface UseReservationSubmitParams {
  show: Show;
  selectedEventId: string;
  attendeeCount: number;
  customPrice: number;
  newsletter: boolean;
  guestCount: number;
}

export const useReservationSubmit = ({
  show,
  selectedEventId,
  attendeeCount,
  customPrice,
  newsletter,
  guestCount,
}: UseReservationSubmitParams) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const mutation = useCreateReservation();

  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isProcessing, setIsProcessing] = useState(false);

  const handleClearFieldError = (id: string) => {
    setFieldErrors((prev) => clearFieldError(prev, id));
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLFormElement>) => {
    // Only the uncontrolled text inputs are read here; the controlled fields
    // (event, ticket count, price, newsletter) are persisted by an effect in
    // ReservationPage, since this closure would only see their previous values.
    const formData = new FormData(e.currentTarget);
    updateDraft(extractGuestFormData(formData, guestCount));
  };

  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsProcessing(true);

    const formData = new FormData(e.currentTarget);
    const guestFormData = extractGuestFormData(formData, guestCount);

    const errors = validateReservationForm(
      guestFormData,
      guestCount,
      selectedEventId,
      t,
    );
    setFieldErrors(errors);

    const firstErrorId = Object.keys(errors)[0];
    if (firstErrorId) {
      setIsProcessing(false);
      document.getElementById(firstErrorId)?.focus();
      return;
    }

    mutation.mutate(
      {
        ...guestFormData,
        showId: String(show.id),
        eventId: selectedEventId,
        newsletter,
        attendeeCount,
        customTicketPrice: customPrice,
      },
      {
        onSuccess: async (data) => {
          try {
            const paymentIntent = await createPaymentIntent(
              data.reservationId,
              customPrice,
            );
            navigate({
              to: "/reserve/$showId/payment",
              params: { showId: String(show.id) },
              search: {
                reservationId: data.reservationId,
                customTicketPrice: customPrice,
                clientSecret: paymentIntent.clientSecret,
              },
            });
          } catch (err) {
            setIsProcessing(false);
            setError(
              err instanceof Error
                ? err.message
                : t("reservation_error_generic"),
            );
          }
        },
        onError: (err) => {
          setIsProcessing(false);
          setError(
            err instanceof Error ? err.message : t("reservation_error_generic"),
          );
        },
      },
    );
  };

  return {
    handleSubmit,
    handleFormChange,
    handleClearFieldError,
    error,
    fieldErrors,
    isProcessing,
  };
};
