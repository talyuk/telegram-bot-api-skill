# Errors, retries and delivery

## The response envelope

Every response is JSON with a boolean `ok`. On success the payload is in `result`; on
failure there is an `error_code` (mirroring the HTTP status), a human-readable
`description`, and sometimes `parameters` of type
[ResponseParameters](https://core.telegram.org/bots/api#responseparameters).

```json
{"ok": false, "error_code": 429, "description": "Too Many Requests: retry after 17",
 "parameters": {"retry_after": 17}}
```

`ResponseParameters` carries exactly two optional fields: `retry_after` and
`migrate_to_chat_id`.

**The reference says of `error_code`: "its contents are subject to change in the
future."** So branch on the `description` string, and treat `error_code` as a coarse
bucket. `description` strings are not versioned either, which is why the rule below is
to match substrings rather than whole strings.

## Classify into three buckets, not two

The usual bug is a two-way split (retry / don't retry) that quietly deletes a chat row
on a transient failure, or retries forever on a permanent one. Three buckets:

| Bucket | Meaning | Action |
|---|---|---|
| **Permanent** | This chat will never accept a message again | Mark the chat dead. Stop. Never retry. |
| **Transient** | This attempt failed; the chat is fine | Retry with backoff. |
| **Unknown** | Anything unmatched | Retry a bounded number of times, then alert a human. Do **not** fold into "permanent". |

### Permanent — stop sending to this chat

| `description` substring | Code | Source |
|---|---|---|
| `bot was blocked by the user` | 403 | server source, `USER_IS_BLOCKED` |
| `user is deactivated` | 403 | server source, `INPUT_USER_DEACTIVATED` |
| `bot was kicked from the group chat` / `supergroup chat` / `channel chat` | 403 | server source |
| `chat not found` | 400 | server source |
| `bot is not a member of the` | 403 | server source |
| `bot can't initiate conversation with a user` | 403 | forwarded from the backend |
| `user not found` | 400 | forwarded from the backend |
| `not enough rights to send` | 400 | forwarded from the backend |

**Match the suffix, not the whole string.** Verified in
[`telegram-bot-api/Client.cpp`](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.cpp),
where these two sit nine lines apart and are built inconsistently:

```cpp
} else if (error_message == "INPUT_USER_DEACTIVATED") {
  error_code = 403;
  error_message = "Forbidden: user is deactivated";   // prefix baked in
} else if (error_message == "USER_IS_BLOCKED") {
  error_code = 403;
  error_message = "bot was blocked by the user";      // no prefix; added later
```

So an exact-match on `"Forbidden: bot was blocked by the user"` misses cases that the
substring `"bot was blocked by the user"` catches. The rows marked *forwarded from the
backend* are not constructed in the Bot API server at all — they arrive from Telegram's
core and are relayed, which is another reason not to anchor on a full string.

### Transient — retry

| Condition | Code | Action |
|---|---|---|
| `Too Many Requests` | 429 | Sleep `parameters.retry_after` (+ jitter), retry. Stall only that chat, not the whole queue. |
| `Bad Gateway` / `Gateway Timeout` | 502 / 504 | Exponential backoff. |
| `Internal Server Error` | 500 | Exponential backoff. |
| Connection reset, DNS failure, read timeout | — | Backoff. **A timeout is not a failure to deliver** — see idempotency below. |

### Migration — not an error, a redirect

`400 Bad Request: group chat was upgraded to a supergroup chat` arrives with
`parameters.migrate_to_chat_id`. Rewrite your stored `chat_id` to that value and retry.
That id may exceed 32 significant bits; it fits in a signed 64-bit integer, and the docs
warn some languages have "difficulty/silent defects" interpreting it. In JS it exceeds
`Number.MAX_SAFE_INTEGER` territory for related ids — parse chat ids as strings or
BigInt if your stack is JSON-number-typed.

## Backoff

On 429, `retry_after` is authoritative — do not compute your own delay and do not cap it
below what Telegram asked for. Add jitter so a batch that all hit the limit at once does
not resume in lockstep. Everywhere else, exponential backoff with a ceiling.

A crash loop must not hammer the API: if your worker restarts, it should not replay a
whole queue at full rate. Put the rate limiter's state outside the process, or start each
run with a short warm-up.

## Idempotency

The Bot API has **no idempotency key**. A request that times out may still have been
delivered. If you retry blindly you will double-send.

The only durable defence is your own dedup table: write "intent to send (chat, item)"
before the call, mark it sent after a confirmed 2xx, and on restart skip intents already
marked. Key it on something frozen at insert time — never on an expression you might
recompute later, or a changed key silently re-notifies everything.

`sendMediaGroup` is the worst case: it returns N messages and has no atomic guarantee,
so a partial failure can leave some of the album delivered.

## Per-chat ordering

Telegram does not guarantee that two concurrent sends to one chat arrive in the order you
issued them. If order matters (a card followed by its buttons, a correction after a
message), serialize per chat — one in-flight request per `chat_id` — rather than relying
on wall-clock spacing.

## Webhook retries

The only official commitment: *"we will repeat the request and give up after a reasonable
amount of attempts."* Any specific number (3 attempts, 5 attempts) is folklore. The
published server source shows exponential backoff with no fixed count.

Consequences: **return 200 fast**. Do the work asynchronously. A slow handler turns into
duplicate deliveries, and duplicates are indistinguishable from new updates apart from
`update_id`.

Verify webhook authenticity with `setWebhook`'s `secret_token` (1–256 characters), which
Telegram echoes in the `X-Telegram-Bot-Api-Secret-Token` header on every request. Check
it on every call; do not rely on IP allowlists alone.
