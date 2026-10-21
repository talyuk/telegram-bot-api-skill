---
name: telegram-bot-api
description: Use when writing or debugging anything against the Telegram Bot API or Telegram Mini Apps — bot handlers, webhooks vs getUpdates, sendMessage/sendPhoto/sendMediaGroup, inline keyboards and callback_data, parse_mode escaping, initData validation, Telegram Stars and payments, 429 flood control, blocked-user errors, or aiogram/python-telegram-bot/grammY/telegraf code. Also use when asked which Bot API version introduced a field or method.
---

# Telegram Bot API

Snapshot: **Bot API 10.3, released 2026-08-24.** 185 methods, 400 types.

## Look it up; do not recall it

The Bot API ships roughly monthly and most of its surface postdates any model's
training cutoff. Recalled limits are wrong often enough to cost a production incident,
and they are wrong *confidently* — the numbers feel precise.

A lookup costs one command (paths are relative to this skill's directory —
`~/.claude/skills/telegram-bot-api/`):

```bash
scripts/tg-api.py show sendPhoto       # real parameter table, with types and required flags
scripts/tg-api.py search clipboard     # find the method or type by name or summary
scripts/tg-api.py fields Message       # field names only
scripts/tg-api.py since 10.0           # changelog bullets at or after a version
scripts/tg-api.py version              # snapshot vs live — says if the snapshot is stale
scripts/tg-api.py refresh              # re-fetch core.telegram.org, rewrite spec.json
```

`spec.json` is parsed from `core.telegram.org/bots/api` itself, so `show` prints the
documentation's own table rather than a paraphrase of it.

**Run `version` first** whenever the answer depends on a recent feature. If it reports
stale, `refresh` and re-read the reference file covering the area you are touching.

## Facts that are usually misremembered

Every row below was answered wrongly by a competent agent working from memory.

| Claim that feels right | Actually |
|---|---|
| Photos are 10 MB whatever the transport | **By URL: 5 MB** (20 MB other types). By upload: 10 MB (50 MB other). By `file_id`: unlimited. |
| 30 msg/s is a global API request cap | It applies to **bulk notifications** only. There is no documented global request cap. |
| You just have to stay under 30/s | `allow_paid_broadcast` raises it to **1000/s** at 0.1 Stars per message past the free 30. |
| Telegram sends `Retry-After` headers | It sends **no** rate-limit headers. Read `parameters.retry_after` from the JSON body. |
| Self-hosting the Bot API server raises send limits | It does not. File sizes and webhook transport only. |
| `copy_text` buttons came in 7.5 | **7.11** (2024-10-31). |
| `BotCommand.description` is 3–256 | **1–256**. |
| A poll takes 2–10 options | **1–12** since 9.1/10.0. |
| `signature` is excluded from the initData HMAC | Only **`hash`** is. `signature` is signed data. (The *Ed25519* check excludes both.) |
| Bot API 8.0 shipped around Aug 2024 | **2024-11-17.** |
| `allowed_updates` defaults to everything | It defaults to the **previous** value, and never includes `chat_member`, `message_reaction`, `message_reaction_count` unless asked. |

Transcribe the Ed25519 public keys from `references/mini-apps.md`; never retype them.
A key one byte short rejects every payload — with a clear length error in Python,
but as an ordinary signature mismatch in looser stacks.

## Where things are

| File | Covers |
|---|---|
| `references/limits.md` | Rate limits (official vs folklore), paid broadcasts, file-size ceilings per transport, every length limit |
| `references/errors.md` | The response envelope, three-bucket error classification with exact `description` substrings, backoff, idempotency, webhook retries |
| `references/sending.md` | parse_mode choice and escaping, entities, link previews, media groups, inline keyboards, the 64-byte `callback_data` budget |
| `references/updates.md` | Polling vs webhooks, `allowed_updates`, the full `Update` field list, offsets, command scopes |
| `references/mini-apps.md` | initData delivery and both validation schemes, origin hardening, launch surfaces, WebApp JS version gates |
| `references/payments.md` | Stars vs card rails, invoice flow, pre-checkout, subscriptions, refunds |
| `references/versions.md` | Changelog navigation, 10.x summary, library → Bot API support |
| `scripts/tg-api.py` | The query/refresh tool above |
| `scripts/initdata.py` | Tested initData validator, both schemes |
| `scripts/test_initdata.py` | Its fixtures — run it after changing the validator |

## Rules worth applying without being asked

- **Escape the data, then build the markup** — never the reverse. Prefer `HTML`
  (3 characters to escape) over `MarkdownV2` (18, including `.` `-` `+`).
- **Classify send failures into three buckets, not two.** Permanent (stop), transient
  (retry), unknown (bounded retry, then alert). Folding "unknown" into "permanent"
  deletes live users.
- **Match error `description` as a substring**, never whole-string — Telegram prepends
  `Forbidden: ` / `Bad Request: ` inconsistently across cases.
- **Budget `callback_data` in bytes.** 64 bytes; Cyrillic costs 2 per character, so it
  overflows in production and fails as a 400 at send time.
- **There is no idempotency key.** A timed-out send may have been delivered; keep your
  own dedup table.
- **`answerCallbackQuery` on every callback**, even a no-op, or the client spins.
- **Never trust `initDataUnsafe`** for authorization, and never let an iframe call
  `window.Telegram.WebApp` — origin hardening has been enforced since 2026-07-20.

## Red flags

Stop and run `tg-api.py show` instead:

- About to state a size, length or rate limit from memory.
- About to say which version introduced a field.
- Reaching for a field name you have not seen in this session's tool output.
- Reading a version off the changelog's *first* match — it is reverse-chronological, so
  that is the most recent touch, not the introduction.
