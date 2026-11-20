import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { Show, ShowEvent } from "#/interfaces/show";
import ReservationPage from "./ReservationPage";
import { loadDraft, resolveInitialEventId } from "./reservationDraft";

const mutate = vi.fn();

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));
vi.mock("#/lib/payments.ts", () => ({
  useCreateReservation: () => ({ mutate }),
  createPaymentIntent: vi.fn(),
}));

// Radix Slider measures itself; jsdom has no ResizeObserver.
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const makeEvent = (id: string, label: string, soldOut = false): ShowEvent => ({
  id,
  timeAndDate: label,
  admissionTime: "",
  soldOut,
});

const makeShow = (events: ShowEvent[]): Show =>
  ({
    id: 360,
    title: "8 years of Zirkus Mond",
    baseTicketPrice: 25,
    upcomingEvents: events,
  }) as unknown as Show;

const FOUR_DATES = [
  makeEvent("574", "13.11"),
  makeEvent("575", "14.11"),
  makeEvent("576", "20.11"),
  makeEvent("577", "21.11"),
];

const getForm = (container: HTMLElement) =>
  container.querySelector<HTMLFormElement>("#reservation-form")!;

const getEventButton = (container: HTMLElement) =>
  container.querySelector<HTMLButtonElement>("#event")!;

const pickEvent = (container: HTMLElement, label: string) => {
  fireEvent.click(getEventButton(container));
  fireEvent.click(screen.getByText(label));
};

const fillBuyer = (container: HTMLElement) => {
  for (const [name, value] of [
    ["firstName", "Akim"],
    ["lastName", "Kushnerovich"],
    ["email", "akim@example.com"],
  ]) {
    fireEvent.change(container.querySelector(`[name="${name}"]`)!, {
      target: { value },
    });
  }
};

const submittedEventIds = () =>
  mutate.mock.calls.map(([params]) => (params as { eventId: string }).eventId);

beforeEach(() => {
  sessionStorage.clear();
  mutate.mockClear();
});

afterEach(cleanup);

describe("ReservationPage event selection", () => {
  it("keeps the chosen date when the customer comes back from the payment step and retries", () => {
    const show = makeShow(FOUR_DATES);

    // Attempt 1: pick the 21st and go to payment.
    let { container } = render(<ReservationPage show={show} />);
    pickEvent(container, "21.11");
    fillBuyer(container);
    fireEvent.submit(getForm(container));

    // Payment step unmounts the form; "Back" / PayPal cancel remounts it.
    cleanup();
    ({ container } = render(<ReservationPage show={show} />));

    expect(getEventButton(container).textContent).toContain("21.11");
    fireEvent.submit(getForm(container));

    expect(submittedEventIds()).toEqual(["577", "577"]);
  });

  it("does not preselect the first of several dates and blocks submit until one is picked", () => {
    const { container } = render(
      <ReservationPage show={makeShow(FOUR_DATES)} />,
    );

    expect(getEventButton(container).textContent).not.toContain("13.11");
    fillBuyer(container);
    fireEvent.submit(getForm(container));

    expect(mutate).not.toHaveBeenCalled();
    expect(getEventButton(container).getAttribute("aria-invalid")).toBe("true");

    pickEvent(container, "20.11");
    expect(getEventButton(container).getAttribute("aria-invalid")).toBe(
      "false",
    );
    fireEvent.submit(getForm(container));
    expect(submittedEventIds()).toEqual(["576"]);
  });

  it("preselects the date when only one is bookable", () => {
    const show = makeShow([
      makeEvent("574", "13.11", true),
      makeEvent("575", "14.11"),
    ]);
    const { container } = render(<ReservationPage show={show} />);

    fillBuyer(container);
    fireEvent.submit(getForm(container));

    expect(submittedEventIds()).toEqual(["575"]);
  });

  it("does not restore a saved date that has sold out in the meantime", () => {
    let { container } = render(<ReservationPage show={makeShow(FOUR_DATES)} />);
    pickEvent(container, "21.11");
    cleanup();

    const soldOutNow = FOUR_DATES.map((event) =>
      event.id === "577" ? { ...event, soldOut: true } : event,
    );
    ({ container } = render(<ReservationPage show={makeShow(soldOutNow)} />));
    fillBuyer(container);
    fireEvent.submit(getForm(container));

    expect(mutate).not.toHaveBeenCalled();
  });

  it("persists the ticket count changed with the +/- buttons", () => {
    render(<ReservationPage show={makeShow(FOUR_DATES)} />);
    fireEvent.click(screen.getByLabelText("Increase"));
    fireEvent.click(screen.getByLabelText("Increase"));

    expect(loadDraft()?.attendeeCount).toBe(3);
  });
});

describe("resolveInitialEventId", () => {
  it("returns the saved event when it is still bookable", () => {
    expect(resolveInitialEventId(["1", "2"], "2")).toBe("2");
  });

  it("returns empty for several dates and no (valid) saved event", () => {
    expect(resolveInitialEventId(["1", "2"], undefined)).toBe("");
    expect(resolveInitialEventId(["1", "2"], "9")).toBe("");
  });

  it("returns the only bookable event", () => {
    expect(resolveInitialEventId(["7"], undefined)).toBe("7");
  });

  it("returns empty when nothing is bookable", () => {
    expect(resolveInitialEventId([], "7")).toBe("");
  });
});
