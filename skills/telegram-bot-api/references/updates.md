# Receiving updates

Two mutually exclusive transports: `getUpdates` (long polling) and `setWebhook`.
Setting a webhook disables `getUpdates` and vice versa. Undelivered updates are held for
**24 hours**, then dropped.

## Polling vs webhook

| | Long polling | Webhook |
|---|---|---|
| Inbound port / TLS | none needed | public HTTPS, valid cert (or a local Bot API server for HTTP) |
| Latency | one round trip | lowest |
| Scaling | one poller per token, period | Telegram fans out to `max_connections` (1–100) |
| Failure mode | you stop asking | Telegram retries an unknown number of times |
| Ops cost | trivial | cert renewal, reverse proxy, a public surface |

Long polling is the right default until inbound HTTPS is already solved. `timeout` is
seconds; **short polling (`timeout=0`) is for testing only** per the docs. `limit` is
1–100, default 100.

**Two pollers on one token is the silent failure.** Telegram hands each update to
whichever consumer asks first, so a laptop running the production token steals live
traffic and surfaces only as an intermittent conflict error. Check which bot a token
belongs to before starting anything: the id is the part before the colon.

## allowed_updates

Both `getUpdates` and `setWebhook` take `allowed_updates`. **Omitting it does not mean
"everything"** — it means the previous setting, and the default excludes
`chat_member`, `message_reaction`, `message_reaction_count`. Pass the list explicitly
and keep it in one constant shared by both call sites.

Adding a feature (payments, subscriptions, reactions) means adding its update type here.
A handler that never fires is usually this, not a routing bug.

`Update` carries `update_id` plus **at most one** optional field. As of 10.4 there are 29 of them:

```
message  edited_message  channel_post  edited_channel_post  business_connection
business_message  edited_business_message  deleted_business_messages  guest_message
message_reaction  message_reaction_count  inline_query  chosen_inline_result
callback_query  shipping_query  pre_checkout_query  purchased_paid_media  poll
poll_answer  my_chat_member  chat_member  chat_join_request  chat_boost
removed_chat_boost  managed_bot  subscription  stopped_message_generation
widget_query  shared_widget_query
```

`widget_query` and `shared_widget_query` are new in 10.4 — see `widgets.md`.

Regenerate with `scripts/tg-api.py show Update`.

## Webhook specifics

- `secret_token` (1–256 chars) is echoed in the `X-Telegram-Bot-Api-Secret-Token`
  header on every delivery. Verify it on every request.
- **Return 200 immediately** and process asynchronously. Telegram's only retry
  commitment is "a reasonable amount of attempts" with no published count; a slow
  handler manufactures duplicates.
- Deduplicate on `update_id`. Retried deliveries are byte-identical to the original.
- You may answer the webhook with a method call in the response body (set `method`),
  but you cannot see whether it succeeded.
- `getWebhookInfo` reports `pending_update_count` and `last_error_message` — the first
  place to look when a bot goes quiet.
- `deleteWebhook(drop_pending_updates=true)` clears a backlog; without it, switching
  transports replays everything still inside the 24-hour window.

## Offsets and acknowledgement

`getUpdates(offset=N)` acknowledges everything below `N`. Passing
`offset = last_update_id + 1` is what marks updates as handled — forget it and Telegram
redelivers the same batch forever. Acknowledge only after the update is durably
processed, or crash recovery loses it.

## Commands

`setMyCommands` accepts a `language_code` and a `scope`
(`BotCommandScopeDefault`, `...Chat`, `...AllPrivateChats`, `...ChatAdministrators`, …).
Resolution is most-specific-first: chat scope beats all-private-chats beats default, and
within a scope the user's language beats the empty-language fallback.

`BotCommand.command` is 1–32 chars, lowercase English letters, digits and underscores
only; `description` is 1–256. `is_ephemeral` (10.2) marks a command whose reply is
visible only to the sender.
