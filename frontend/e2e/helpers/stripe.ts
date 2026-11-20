import { createHmac } from "node:crypto";
import type { FrameLocator, Page } from "@playwright/test";

import { DJANGO_URL } from "./urls.ts";

/** Must match STRIPE_WEBHOOK_SECRET in backend/config/settings/e2e.py. */
const WEBHOOK_SECRET = "whsec_e2e";

const stripeSecretKey = () => {
  const key = process.env.STRIPE_TEST_SECRET_KEY ?? "";
  if (!key.startsWith("sk_test_")) {
    throw new Error("STRIPE_TEST_SECRET_KEY must be set to a Stripe test key");
  }
  return key;
};

/** `pi_123_secret_abc` -> `pi_123` */
export const paymentIntentIdFromClientSecret = (clientSecret: string) =>
  clientSecret.split("_secret_")[0];

export const retrievePaymentIntent = async (
  id: string,
): Promise<Record<string, unknown> & { id: string; status: string }> => {
  const res = await fetch(`https://api.stripe.com/v1/payment_intents/${id}`, {
    headers: { Authorization: `Bearer ${stripeSecretKey()}` },
  });
  if (!res.ok)
    throw new Error(
      `Stripe PI retrieve failed: ${res.status} ${await res.text()}`,
    );
  return (await res.json()) as Record<string, unknown> & {
    id: string;
    status: string;
  };
};

/**
 * Delivers a `payment_intent.succeeded` webhook for a real (test-mode) PaymentIntent
 * to Django, signed the same way Stripe signs it. Replaces `stripe listen`.
 */
export const sendPaymentIntentSucceededWebhook = async (
  paymentIntentId: string,
) => {
  const intent = await retrievePaymentIntent(paymentIntentId);
  const payload = JSON.stringify({
    id: `evt_e2e_${Date.now()}`,
    object: "event",
    type: "payment_intent.succeeded",
    created: Math.floor(Date.now() / 1000),
    livemode: false,
    data: { object: intent },
  });
  const timestamp = Math.floor(Date.now() / 1000);
  const signature = createHmac("sha256", WEBHOOK_SECRET)
    .update(`${timestamp}.${payload}`)
    .digest("hex");

  return fetch(`${DJANGO_URL}/payments/webhook/stripe`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Stripe-Signature": `t=${timestamp},v1=${signature}`,
    },
    body: payload,
  });
};

/**
 * The Stripe PaymentElement iframe. Stripe's iframe titles are localized and change, so
 * locate it structurally: the only iframe inside the payment <form>.
 */
const paymentElementFrame = (page: Page): FrameLocator =>
  page.locator("form iframe").first().contentFrame();

export const fillTestCard = async (page: Page) => {
  const frame = paymentElementFrame(page);
  // With layout "accordion" and several methods enabled, card may need expanding first.
  const cardNumber = frame.locator('input[name="number"]');
  const cardOption = frame.getByRole("button", { name: /Karte|Card/i }).first();
  await cardNumber.or(cardOption).first().waitFor({ timeout: 30_000 });
  if (!(await cardNumber.isVisible())) await cardOption.click();

  await cardNumber.fill("4242424242424242");
  await frame.locator('input[name="expiry"]').fill("12/34");
  await frame.locator('input[name="cvc"]').fill("123");
};
