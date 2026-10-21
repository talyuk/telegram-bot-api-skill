# Payments and Telegram Stars

Two payment rails, with different rules.

| | Telegram Stars (XTR) | Card payments |
|---|---|---|
| `currency` | `"XTR"` | ISO-4217 code |
| Provider token | **omitted** | from @BotFather, per provider |
| Allowed goods | digital goods and services | physical goods, per provider terms |
| Availability | everywhere Telegram is | depends on the provider's country coverage |
| `prices` | exactly one `LabeledPrice` | may be itemised |
| Tips | not supported | `max_tip_amount`, `suggested_tip_amounts` |

For digital goods Apple and Google require Stars in their app stores, so a bot selling
access inside Telegram effectively means Stars.

## Flow

1. `sendInvoice` (a message) or `createInvoiceLink` (a URL you can put behind any
   button, including a Mini App's `openInvoice`).
2. Telegram sends `pre_checkout_query`. **`answerPreCheckoutQuery` within 10 seconds**
   or the payment fails. Do the final availability check here — it is the last point at
   which you can refuse.
3. On success a `Message` arrives with `successful_payment`
   (`SuccessfulPayment`: `telegram_payment_charge_id`, `provider_payment_charge_id`,
   `invoice_payload`, `total_amount`, `currency`, plus subscription fields).
4. Grant entitlement keyed on `telegram_payment_charge_id`, which is your idempotency
   key. Never key on `invoice_payload` alone — a user can pay the same invoice twice.

`shipping_query` / `answerShippingQuery` only appear for flexible-priced physical goods.

Field limits: `title` 1–32, `description` 1–255 characters, `payload` 1–128 **bytes**
(never put user-controlled text in the payload — it is size-capped and echoed back).

## Subscriptions

`createInvoiceLink` takes `subscription_period` (Bot API 8.0) — currently **2592000
seconds (30 days)** is the only accepted value, and a subscription price may not exceed **10000 Stars**. Recurring charges produce further
`successful_payment` messages carrying `is_recurring` / `is_first_recurring`.

Bot API 10.2 added `BotSubscriptionUpdated` and the `subscription` field on `Update`:
lifecycle changes (cancelled, expired, renewed) arrive as their own update rather than
having to be inferred. **Add `"subscription"` to `allowed_updates`** or it never fires.

## Refunds and balances

- `refundStarPayment(user_id, telegram_payment_charge_id)` — full refunds only.
- `getStarTransactions` / `getMyStarBalance` — reconciliation.
- `editUserStarSubscription` — cancel a subscription on the bot's side.
- Stars a bot receives are withdrawable via Fragment after a holding period.

## Before building this

Check the user's country actually supports what you are selling, on the rail you chose,
in the client they use. Payment coverage is the part of the Bot API that varies most by
jurisdiction, and it is not discoverable from the API surface — it fails at the user's
checkout, not at your call site.
