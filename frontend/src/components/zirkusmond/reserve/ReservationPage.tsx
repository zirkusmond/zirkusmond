import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Button } from "#/components/ui/button.tsx";
import { Loader2, CreditCard, ArrowLeft, TestTube } from "lucide-react";
import type { Show } from "#/interfaces/show.ts";
import { fillReservationFormWithDummyData } from "./fillDummyData.ts";
import GuestForm from "./components/GuestForm.tsx";
import ReservationForm from "./components/ReservationForm.tsx";
import NewsletterForm from "./components/NewsletterForm.tsx";
import SlidingScale from "./components/SlidingScale.tsx";
import SectionCard from "../general/SectionCard.tsx";
import NavigationButtonWrapper from "../general/NavigationButtonWrapper.tsx";
import { useTranslation } from "react-i18next";
import { loadDraft, useFormStorage } from "./reservationDraft.ts";
import { useReservationSubmit } from "./useReservationSubmit.ts";

interface ReservationPageProps {
  show: Show;
}

export default function ReservationPage({ show }: ReservationPageProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Initialise formInputs from sessionStorage if they exist
  const savedInputs = loadDraft();
  useFormStorage(savedInputs);

  const [selectedEventId, setSelectedEventId] = useState(
    show.upcomingEvents[0]?.id,
  );
  const [attendeeCount, setAttendeeCount] = useState(
    () => savedInputs?.attendeeCount ?? 1,
  );
  const [customPrice, setCustomPrice] = useState(
    () =>
      savedInputs?.customPrice ??
      show.baseTicketPrice ??
      show.reservationPrice ??
      15,
  );
  const [newsletter, setNewsletter] = useState(
    () => savedInputs?.newsletter ?? false,
  );

  const guestCount = Math.min(9, Math.max(0, attendeeCount - 1));

  const {
    handleSubmit,
    handleFormChange,
    handleClearFieldError,
    error,
    fieldErrors,
    isProcessing,
  } = useReservationSubmit({
    show,
    selectedEventId,
    attendeeCount,
    customPrice,
    newsletter,
    guestCount,
  });

  const handleBack = () => {
    navigate({ to: "/shows/$showId", params: { showId: String(show.id) } });
  };

  const handleFillDummyData = () => {
    fillReservationFormWithDummyData({
      show,
      setSelectedEventId,
      setAttendeeCount,
      setNewsletter,
      setCustomPrice,
    });
  };

  return (
    <div className="flex items-center justify-center max-w-7xl mx-auto text-white p-1 md:p-8">
      <form
        onSubmit={handleSubmit}
        id="reservation-form"
        noValidate
        onChange={handleFormChange}
      >
        {import.meta.env.DEV && (
          <div className="flex justify-end mb-2">
            <Button
              type="button"
              variant="secondary"
              onClick={handleFillDummyData}
            >
              <TestTube />
              {t("button_fill_test_data")}
            </Button>
          </div>
        )}
        <SectionCard>
          <ReservationForm
            show={show}
            selectedEventId={selectedEventId}
            setSelectedEventId={setSelectedEventId}
            attendeeCount={attendeeCount}
            setAttendeeCount={setAttendeeCount}
            fieldErrors={fieldErrors}
            clearFieldError={handleClearFieldError}
          />

          <GuestForm
            guestCount={guestCount}
            fieldErrors={fieldErrors}
            clearFieldError={handleClearFieldError}
          />
          <NewsletterForm
            newsletter={newsletter}
            setNewsletter={setNewsletter}
          />

          <div className="my-4 sm:my-6 max-w-2xl mx-auto">
            <SlidingScale
              show={show}
              customPrice={customPrice}
              setCustomPrice={setCustomPrice}
            />
          </div>

          <div className="my-3 sm:my-4 text-center">
            <h4>
              {t("reservation_total_price")}:{" "}
              <span className="font-bold">
                {(attendeeCount * customPrice).toFixed(2)}
              </span>{" "}
              €
            </h4>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-white/10 border-2 border-destructive text-red/30 text-xl">
              <p className="text-red-300 text-center">{error}</p>
            </div>
          )}

          <NavigationButtonWrapper>
            <Button
              type="submit"
              disabled={isProcessing}
              className="sm:min-w-[200px]"
            >
              {isProcessing ? (
                <Loader2 className="animate-spin" />
              ) : (
                <CreditCard />
              )}
              {isProcessing
                ? t("button_processing")
                : t("button_proceed_to_payment")}
            </Button>
            <Button type="button" variant="secondary" onClick={handleBack}>
              <ArrowLeft />
              {t("button_back_to_show")}
            </Button>
          </NavigationButtonWrapper>
        </SectionCard>
      </form>
    </div>
  );
}
