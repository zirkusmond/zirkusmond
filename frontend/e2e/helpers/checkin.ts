import { expect, request } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";

import { DJANGO_URL } from "./urls.ts";

/**
 * Logs a staff user into the Django admin and returns a request context carrying the
 * session cookie — the same auth the QR scanner page relies on.
 */
export const staffSession = async (
  username: string,
  password: string,
): Promise<APIRequestContext> => {
  const ctx = await request.newContext({ baseURL: DJANGO_URL });

  const loginPage = await ctx.get("/mondmin/login/");
  const csrf = /name="csrfmiddlewaretoken" value="([^"]+)"/.exec(
    await loginPage.text(),
  )?.[1];
  if (!csrf)
    throw new Error("Could not find CSRF token on the admin login page");

  await ctx.post("/mondmin/login/?next=/mondmin/", {
    form: { csrfmiddlewaretoken: csrf, username, password, next: "/mondmin/" },
  });

  // Sanity check: staff-only scanner endpoint must now be accessible.
  const events = await ctx.get("/qr-scanner/get-events");
  expect(events.status(), "staff login failed").toBe(200);
  return ctx;
};

/** Same call the QR scanner makes after decoding `{ticket, event}` from a ticket QR code. */
export const checkIn = (
  ctx: APIRequestContext,
  ticketId: string,
  eventId: number,
) => ctx.post(`/qr-scanner/${ticketId}/check-in?event=${eventId}`);
