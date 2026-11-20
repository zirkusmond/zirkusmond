import DynamicForm from "#/components/zirkusmond/form/DynamicForm";
import {
  buildPersonalInfoFields,
  buildTicketFields,
} from "#/components/zirkusmond/reserve/formFieldBuilders";
import type { Show } from "#/interfaces/show";

interface ReservationFormProps {
  show: Show;
  selectedEventId: string;
  setSelectedEventId: (id: string) => void;
  attendeeCount: number;
  setAttendeeCount: (count: number) => void;
  fieldErrors: Record<string, string>;
  clearFieldError: (id: string) => void;
}

export default function ReservationForm({
  show,
  selectedEventId,
  setSelectedEventId,
  attendeeCount,
  setAttendeeCount,
  fieldErrors,
  clearFieldError,
}: ReservationFormProps) {
  const ticketFields = buildTicketFields({
    show,
    selectedEventId,
    setSelectedEventId,
    attendeeCount,
    setAttendeeCount,
    fieldErrors,
    clearFieldError,
  });
  const personalInfoFields = buildPersonalInfoFields(
    fieldErrors,
    clearFieldError,
  );

  return (
    <div className="w-full flex flex-col justify-center mx-auto gap-6 my-8">
      <DynamicForm title="Tickets" fields={ticketFields} />
      {!show.baseTicketPrice && (
        <p className="w-full my-3 sm:my-4">
          For your Reservation, you will have to pay{" "}
          {show.reservationPrice ?? 5} Euro per Ticket. This will be fully
          deducted from your entree fee at the box office.
        </p>
      )}
      <DynamicForm title="Personal Information" fields={personalInfoFields} />
    </div>
  );
}
