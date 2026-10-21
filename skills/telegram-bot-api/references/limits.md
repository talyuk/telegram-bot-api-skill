# Limits — rate, size, length

Every number here is quoted from `core.telegram.org` as of Bot API 10.3 (2026-08-24).
Regenerate the length table with `scripts/tg-api.py show <method>`.

## 1. Rate limits: what is official and what is not

Telegram publishes exactly three send-rate numbers, all in the
[Bots FAQ](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this),
all hedged. There is no rate limit table in the API reference.

| Claim | Status | Evidence |
|---|---|---|
| ~1 message/second **per chat** | OFFICIAL | FAQ: *"In a single chat, avoid sending more than one message per second. We may allow short bursts that go over this limit, but eventually you'll begin receiving 429 errors."* |
| 20 messages/minute **per group** | OFFICIAL | FAQ: *"In a group, bots are not be able to send more than 20 messages per minute."* |
| ~30 messages/second **bulk broadcast** | OFFICIAL | FAQ: *"For bulk notifications, bots are not able to broadcast more than about 30 messages per second, unless they enable paid broadcasts to increase the limit."* |
| 30/s is a **global API request cap** | FOLKLORE | levlam (tdlib maintainer), [tdlib/td#1834](https://github.com/tdlib/td/issues/1834): *"There is no such thing as 'API requests frequency'."* The 30/s applies to bulk notifications, not to `getUpdates`, `editMessageText`, `answerCallbackQuery`. |
| `retry_after` on 429 | OFFICIAL | [ResponseParameters](https://core.telegram.org/bots/api#responseparameters) |
| `Retry-After` / `X-RateLimit-*` **HTTP headers** | FOLKLORE — does not exist | The API reference contains zero occurrences of either. Rate-limit data is in the JSON body only: `parameters.retry_after`. |
| Repeated 429s escalate to a 24-hour ban | FOLKLORE | No primary source. |
| Self-hosting the Bot API server raises send limits | FOLKLORE — false | The [official feature list](https://core.telegram.org/bots/api#using-a-local-bot-api-server) covers file sizes and webhook transport only. levlam, [telegram-bot-api#677](https://github.com/tdlib/telegram-bot-api/issues/677): *"The self-hosted Bot API server doesn't affect request flood limits."* |
| An album debits the budget as 1 message, or as N | FOLKLORE either way | Undocumented. `sendMediaGroup` returns N `Message` objects; that is inference. |

Design against **both** limiters — a global ~30/s bucket and a per-chat ≥1s spacer.
They bind at different times: the global one during a broadcast, the per-chat one when
one user matches several events in the same batch.

## 2. Paid Broadcasts — the documented way past 30/s

Pass `allow_paid_broadcast: true` (added Bot API 7.11) on any send method to lift the
cap to **1000 messages/second**, at **0.1 Stars per message** beyond the free 30/s,
withdrawn from the bot's Star balance. Only successfully broadcast messages are charged.

**The eligibility threshold is stated twice, and the two statements disagree. Still
unresolved as of 10.3 — do not quote one without the other:**

| Source | Requirement |
|---|---|
| [API reference § Paid Broadcasts](https://core.telegram.org/bots/api#paid-broadcasts) | *"a bot must have at least **10,000 Stars** on its balance"* |
| [FAQ § How can I message all of my subscribers](https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bots-subscribers-at-once) | *"at least **100,000 Stars** on its balance **and at least 100,000 monthly active users**"* |

If you are not paying: the FAQ's own advice is to spread a broadcast over **8–12 hours**.

## 3. File size ceilings — different per transport

The three transports do **not** share a ceiling. This is the single most misremembered
table in the Bot API; assuming "10 MB everywhere" fails on the URL path at 5 MB.

| Transport | Photos | Everything else |
|---|---|---|
| `file_id` (already on Telegram's servers) | no limit | no limit |
| HTTP URL (Telegram fetches it) | **5 MB** | **20 MB** |
| multipart/form-data upload | **10 MB** | **50 MB** |
| Download via `getFile` | — | **20 MB** |
| Local Bot API server | — | upload 2000 MB, download unlimited |

`sendPhoto` additionally requires: **≤10 MB**, **width + height ≤ 10000**, and
**width/height ratio ≤ 20**. Violations are a `400 Bad Request`, not a silent downscale.

Other media: audio/document/video/animation/voice **50 MB** each ("this limit may be
changed in the future"). `sendVoice` by URL must be `audio/ogg` and ≤1 MB; 1–20 MB voice
notes are delivered as files. Thumbnails: JPEG, <200 kB, width and height ≤320.
`sendVideoNote` ≤1 minute. Story photo 1080×1920 ≤10 MB; story video ≤30 MB.

**Cheapest path for repeated sends: upload once, keep the `file_id`, reuse it.**
`file_id` is unique per bot and cannot be transferred between bots; the same file may
have several valid `file_id`s for one bot. You cannot change a file's type when
resending by `file_id`, and thumbnails cannot be resent.

## 4. Length limits

Counted in **UTF-16 code units** ("characters" in the docs), except `callback_data` and
payloads, which are **bytes**. Cyrillic is 1 unit but 2 bytes — a `callback_data` that
fits in ASCII can overflow once a city name lands in it, and it fails at send time as a
400, not at construction time.

| Field | Limit |
|---|---|
| `sendMessage.text` | 1–4096 characters |
| any `caption` | 0–1024 characters |
| `InlineKeyboardButton.callback_data` | **1–64 bytes** |
| `InlineKeyboardButton.text` | no documented limit |
| `CopyTextButton.text` | 1–256 characters |
| `answerCallbackQuery.text` | 0–200 characters |
| `BotCommand.command` | 1–32 characters, lowercase English letters, digits, underscores |
| `BotCommand.description` | **1–256** characters |
| `setMyName.name` | 0–64 characters |
| `setMyDescription.description` | 0–512 characters |
| `setMyShortDescription.short_description` | 0–120 characters |
| `sendPoll.question` | 1–300 characters |
| `sendPoll.options` | **1–12 options** (min dropped 2→1 in 10.0; max raised to 12 in 9.1), each `InputPollOption.text` 1–100 characters |
| `sendPoll.explanation` | 0–200 characters |
| `ReplyParameters.quote` | 0–1024 characters after entities parsing |
| `sendMediaGroup.media` | **2–10 items** |
| `forwardMessages` / `copyMessages` / `deleteMessages` | 1–100 message ids |
| `sendInvoice` / `createInvoiceLink` | `title` 1–32, `description` 1–255 characters, `payload` 1–128 bytes |
| `setWebhook.secret_token` | 1–256 characters |
| `setWebhook.max_connections` | 1–100 (local server: up to 100000) |
| `getUpdates.limit` | 1–100, default 100 |

## 5. Other ceilings worth knowing

- Undelivered updates are kept **24 hours**, then dropped.
- An ephemeral message may be sent within **15 seconds** of the triggering callback
  query or ephemeral message, unless the bot is a chat administrator.
- `answerInlineQuery.cache_time` defaults to 300 s.
- A story can hold ≤10 location areas, ≤5 suggested reactions, ≤3 link areas,
  ≤3 weather areas.
