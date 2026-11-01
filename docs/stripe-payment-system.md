# Stripe Payment System Documentation

## Overview

Zirkusmond now uses a single Stripe-based payment flow.

The active path does **not** go through `django-payments`. Instead, the backend creates its own
`Payment` records, creates Stripe `PaymentIntent`s directly, and uses Stripe webhooks as the source
of truth for final payment state.

At a high level:

1. a reservation is created in Django
2. the backend creates a local `Payment` plus a Stripe `PaymentIntent`
3. the frontend renders Stripe Elements and confirms the payment
4. Stripe sends webhook events back to Django
5. Django updates the `Payment` status and queues emails

## Architecture

### Main components

1. **Reservation creation**
   - `reservations/views.py`
   - `reserve()` creates the `Reservation` and its `Guest` records before payment starts.

2. **Payment model**
   - `backend/reservations/payments/models.py`
   - `Payment` is the canonical payment record used by the active flow.

3. **Payment intent creation**
   - `backend/reservations/payments/views.py`
   - `CreatePaymentIntentView` validates the selected ticket price, creates a `Payment`, creates a
     Stripe `PaymentIntent`, stores its ID, and returns the client secret.

4. **Stripe confirmation in the frontend**
   - `frontend/src/components/zirkusmond/reserve/components/StripePaymentForm.tsx`
   - Stripe Elements collects the payment details and calls `stripe.confirmPayment(...)`.

5. **Return endpoint**
   - `backend/reservations/payments/views.py`
   - `stripe_return()` handles the redirect back from Stripe and sends the customer to the frontend
     success or failure page.

6. **Webhook endpoint**
   - `backend/reservations/payments/views.py`
   - `StripeWebhookView` verifies the webhook signature and updates the `Payment` status.

7. **Signals and tasks**
   - `backend/reservations/payments/signals.py`
   - `backend/reservations/tasks.py`
   - Completed payments queue confirmation emails, refunded payments queue refund emails, and stale
     pending payments are marked as abandoned.

## Active payment model

`Payment` stores the state for the live Stripe integration.

Relevant fields:

- `reservation`
- `stripe_payment_intent_id`
- `payment_method`
- `status`
- `total`
- `custom_ticket_price`
- `created_at`

### Payment statuses

| Status | Meaning |
|---|---|
| `PENDING` | Local payment record created, waiting for Stripe outcome |
| `COMPLETED` | Stripe confirmed the payment |
| `FAILED` | Stripe reported a failed or canceled payment |
| `REFUNDED` | Stripe reported a refund |
| `ABANDONED` | Payment stayed pending long enough to be treated as abandoned |

## Endpoints

### `POST /payments/<reservation_id>/intent`

Creates a Stripe `PaymentIntent` for an existing reservation.

Handled by: `CreatePaymentIntentView`

Request body:

```json
{
  "custom_ticket_price": 20
}
```

Behavior:

- loads the `Reservation`
- validates that the chosen sliding-scale price is within the show's allowed range
- creates a local `Payment` row with status `PENDING`
- creates a Stripe `PaymentIntent` with:
  - `amount` in cents
  - `currency="eur"`
  - metadata including `reservation_id`, customer name, and email
- stores `stripe_payment_intent_id`
- returns the `Payment` ID and Stripe client secret

Response shape:

```json
{
  "id": "<payment-uuid>",
  "client_secret": "<stripe-client-secret>"
}
```

### `GET /payments/return/stripe`

Handled by: `stripe_return`

Query params used:

- `payment_intent`
- `reservationId`

Behavior:

- retrieves the Stripe `PaymentIntent`
- looks up the matching local `Payment`
- attempts to infer the payment method from `latest_charge.payment_method_details`
- redirects to the frontend:
  - success page if Stripe reports `succeeded`
  - failure page otherwise

The return endpoint improves the user experience, but the webhook remains the authoritative source
for final payment state.

### `POST /payments/webhook/stripe`

Handled by: `StripeWebhookView`

Behavior:

- verifies the Stripe webhook signature using `STRIPE_WEBHOOK_SECRET`
- reads the event type
- updates the matching `Payment`
- returns `{"status": "ok"}` on success

## Payment flow

### 1. Create reservation

The frontend first posts reservation data to Django.

`reserve()` creates:

- one `Reservation`
- one or more `Guest` records
- optional newsletter signup

No Stripe object exists yet at this point.

### 2. Create local payment and Stripe PaymentIntent

The frontend then calls:

```text
POST /payments/<reservation_id>/intent
```

`Payment.create_for_reservation(...)`:

- requires a custom ticket price
- reloads the reservation with its event and show
- validates the custom price against the show's effective min/max price
- computes the total from ticket count × selected ticket price
- creates the `Payment`

After that, the backend creates the Stripe `PaymentIntent` and stores its ID on the payment record.

### 3. Confirm payment in Stripe Elements

The frontend uses Stripe Elements and calls `stripe.confirmPayment(...)`.

Current behavior in the app:

- uses the client secret returned by the backend
- submits payment details through Stripe's `PaymentElement`
- sets a return URL pointing to `/payments/return/stripe?reservationId=...`
- uses `redirect: "if_required"`

### 4. Handle redirect back from Stripe

`stripe_return()` checks the `PaymentIntent` status and redirects the customer to the frontend's
success or failure route.

It also tries to store the detected payment method, including:

- card
- Apple Pay
- Google Pay
- Link
- PayPal
- Klarna
- unknown

### 5. Process webhook events

Stripe sends webhook events to Django. This is what finalizes the payment state.

#### Success

**`payment_intent.succeeded`**

- finds `Payment` by `stripe_payment_intent_id`
- sets `status = COMPLETED`
- tries to populate `payment_method` from the latest Stripe charge if it is still missing
- saves the payment

#### Failure

**`payment_intent.payment_failed`**

- sets `status = FAILED`

**`payment_intent.canceled`**

- sets `status = FAILED`

#### Refund

**`charge.refunded`**

- finds the payment by the refunded charge's `payment_intent`
- sets `status = REFUNDED`

## Emails and async work

### Confirmation email

Triggered when a `Payment` is saved with status `COMPLETED`.

Path:

- `post_save` signal on `Payment`
- `send_confirmation_email.delay(reservation_id)`
- `reservations.emails.send_confirmation_mail(reservation)`

### Refund email

Triggered when a `Payment` is saved with status `REFUNDED`.

Path:

- `post_save` signal on `Payment`
- `send_refund_email.delay(reservation_id)`
- `reservations.emails.send_refund_mail(reservation)`

### Abandoned payments cleanup

Handled by the Celery task:

- `cleanup_abandoned_payments()`

Behavior:

- finds `PENDING` payments older than 1 hour
- updates them to `ABANDONED`

This is not driven by Stripe webhooks.

## Event capacity and reporting

Confirmed reservations now depend on `Payment.Status.COMPLETED`.

For example, `Event.reservation_count()` counts completed `Payment` records linked to the event's
reservations and guests. Admin revenue/reporting code also reads from the `Payment` model.

## Error handling

### Intent creation

`CreatePaymentIntentView` returns `400` when:

- the reservation does not provide a valid custom ticket price
- the selected price is outside the allowed range

It returns `404` if the reservation does not exist.

### Webhook errors

`StripeWebhookView` returns:

- `400` for invalid payloads
- `401` for invalid signatures
- `404` if the Stripe object cannot be matched to a local `Payment`
- `500` for unexpected processing errors

### Return flow errors

`stripe_return()` redirects to the frontend failure page when:

- `payment_intent` is missing
- `reservationId` is missing
- Stripe retrieval fails
- the PaymentIntent status is not `succeeded`

## Testing

The current payment flow is covered in `backend/reservations/payments/tests.py`.

Useful test classes:

- `CreatePaymentIntentViewTest`
- `StripeWebhookViewTest`
- `StripeReturnViewTest`

Run the whole payment test module:

```bash
cd backend
uv run pytest reservations/payments/tests.py
```

Run one test class:

```bash
cd backend
uv run pytest reservations/payments/tests.py::StripeWebhookViewTest
```

## Stripe configuration

Required settings/env vars used by the active flow:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `FRONTEND_URL`
- `PAYMENT_HOST`
- `PAYMENT_USES_SSL`

### Local webhook testing

```bash
stripe listen --forward-to localhost:8000/payments/webhook/stripe
```

You can then trigger or replay events from Stripe CLI or the Stripe dashboard.

## Relevant files

- `backend/reservations/payments/models.py`
- `backend/reservations/payments/views.py`
- `backend/reservations/payments/signals.py`
- `backend/reservations/payments/serializers.py`
- `backend/reservations/payments/services.py`
- `backend/reservations/tasks.py`
- `backend/reservations/views.py`
- `frontend/src/lib/payments.ts`
- `frontend/src/components/zirkusmond/reserve/components/StripePaymentForm.tsx`
