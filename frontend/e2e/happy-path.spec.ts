import { expect, test } from "@playwright/test";

import { checkIn, staffSession } from "./helpers/checkin.ts";
import { waitForHydration } from "./helpers/hydration.ts";
import {
  assertMailpitRunning,
  countMessagesTo,
  downloadAttachment,
  waitForMessageTo,
} from "./helpers/mailpit.ts";
import { loadState } from "./helpers/state.ts";
import {
  fillTestCard,
  paymentIntentIdFromClientSecret,
  retrievePaymentIntent,
  sendPaymentIntentSucceededWebhook,
} from "./helpers/stripe.ts";

/**
 * Happy path: home -> show -> reservation form -> Stripe payment -> confirmation
 * email -> staff check-in. Runs against real Django + frontend dev servers and real
 * Stripe test mode; see playwright.config.ts.
 */
test("guest books a ticket, pays, receives the email and is checked in", async ({
  page,
}) => {
  await assertMailpitRunning();
  const state = loadState();
  const email = `e2e+${Date.now()}@example.com`;
  const buyer = { firstName: "Erika", lastName: "Mustermann" };
  const guest = { firstName: "Max", lastName: "Mustermann" };

  // 1. Home page lists the seeded show.
  await page.goto("/");
  await waitForHydration(page);
  await expect(
    page.getByRole("heading", { name: "Kommende Shows" }),
  ).toBeVisible();
  await page.getByRole("link", { name: new RegExp(state.showTitle) }).click();

  // 2. Show page -> reservation.
  await expect(page).toHaveURL(new RegExp(`/shows/${state.showId}$`));
  // The show page renders the reserve button twice (above and below the details).
  await page.getByRole("link", { name: "Tickets kaufen" }).first().click();
  await expect(page).toHaveURL(new RegExp(`/reserve/${state.showId}$`));

  // 3. Reservation form.
  const form = page.locator("#reservation-form");
  const eventOption = form.getByRole("button", {
    name: state.eventTimeAndDate,
    exact: true,
  });
  // SSR renders the form before React hydrates; retry until the click opens the dropdown.
  await expect(async () => {
    if (!(await eventOption.isVisible())) await form.locator("#event").click();
    await expect(eventOption).toBeVisible({ timeout: 1_000 });
  }).toPass();
  await eventOption.click();
  await expect(form.locator("#event")).toContainText(state.eventTimeAndDate);

  await form.getByLabel("Increase").click();
  await expect(form.locator("#attendee-count")).toHaveValue("2");

  await form.locator("#first-name").fill(buyer.firstName);
  await form.locator("#last-name").fill(buyer.lastName);
  await form.locator("#email").fill(email);
  await form.locator("#guest-0-first-name").fill(guest.firstName);
  await form.locator("#guest-0-last-name").fill(guest.lastName);

  const total = (2 * state.ticketPrice).toFixed(2);
  await expect(form).toContainText(total);
  await form.getByRole("button", { name: "Zur Zahlung" }).click();

  // 4. Payment page shows the summary and the Stripe PaymentElement.
  await expect(page).toHaveURL(/\/reserve\/\d+\/payment\?/);
  const clientSecret = new URL(page.url()).searchParams.get("clientSecret");
  const reservationId = new URL(page.url()).searchParams.get("reservationId");
  expect(clientSecret).toBeTruthy();
  expect(reservationId).toBeTruthy();

  await expect(page.getByText(state.showTitle).first()).toBeVisible();
  await expect(
    page.getByText(`${buyer.firstName} ${buyer.lastName}`),
  ).toBeVisible();
  await expect(
    page.getByText(`${guest.firstName} ${guest.lastName}`),
  ).toBeVisible();
  await expect(page.getByText(`${total} €`)).toBeVisible();

  await fillTestCard(page);

  // 5. Pay. Card payments confirm without a redirect and navigate client-side.
  await page.getByRole("button", { name: "Jetzt bezahlen" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/payment/success\\?reservationId=${reservationId}`),
    { timeout: 60_000 },
  );
  await expect(
    page.getByRole("heading", { name: "Vielen Dank für deine Reservierung" }),
  ).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();

  const paymentIntentId = paymentIntentIdFromClientSecret(clientSecret!);
  const intent = await retrievePaymentIntent(paymentIntentId);
  expect(intent.status).toBe("succeeded");
  expect(intent.amount).toBe(2 * state.ticketPrice * 100);

  // No email before the webhook: Django only trusts Stripe's webhook.
  expect(await countMessagesTo(email)).toBe(0);

  // Stripe -> Django webhook (signed with the E2E webhook secret).
  const webhook = await sendPaymentIntentSucceededWebhook(paymentIntentId);
  expect(webhook.status, await webhook.clone().text()).toBe(200);

  // 6. Confirmation email with the PDF tickets.
  const message = await waitForMessageTo(email);
  expect(message.Subject).toContain(state.showTitle);
  expect(message.Text).toContain(`Reservierungs-ID: ${reservationId}`);
  expect(message.Text).toContain("Tickets: 2");
  expect(message.Text).toContain(`Gesamtbetrag: ${total} EUR`);

  const pdf = message.Attachments.find(
    (a) => a.FileName === `tickets_${reservationId}.pdf`,
  );
  expect(pdf, "ticket PDF attachment").toBeTruthy();
  expect(pdf!.ContentType).toBe("application/pdf");
  const pdfBytes = await downloadAttachment(message, pdf!);
  expect(pdfBytes.subarray(0, 5).toString()).toBe("%PDF-");

  // 7. Staff checks the buyer in (same request the QR scanner makes for the
  //    buyer's QR code, which encodes {ticket: reservationId, event: eventId}).
  const staff = await staffSession(state.staffUsername, state.staffPassword);

  const first = await checkIn(staff, reservationId!, state.eventId);
  expect(first.status()).toBe(200);
  const firstBody = await first.json();
  expect(firstBody.success).toBe(true);
  expect(firstBody.reservation_number).toBe(reservationId);
  expect(firstBody.guests).toEqual(
    expect.arrayContaining([
      expect.stringContaining(buyer.firstName),
      expect.stringContaining(guest.firstName),
    ]),
  );

  const second = await checkIn(staff, reservationId!, state.eventId);
  expect(second.status()).toBe(400);
  expect((await second.json()).error).toBe("Ticket already checked in");

  await staff.dispose();
});
