# Versions, changelog, libraries

## Checking the current version

```bash
scripts/tg-api.py version      # snapshot vs live, and tells you if it is stale
scripts/tg-api.py refresh      # re-fetch core.telegram.org and rewrite spec.json
scripts/tg-api.py since 10.0   # every changelog bullet at or after a version
```

**Pin <https://core.telegram.org/bots/api-changelog> for version checks**, not the
reference page. The reference page's "Recent changes" block sits near the **top** of the
document (the bottom is the site footer), is truncated to three releases, and its
`#recent-changes` anchor does not resolve.

The changelog is **reverse-chronological**. When dating a feature, take the **last**
mention of it, not the first — the first match is the most recent time it was touched.
This is how `CopyTextButton` gets misattributed.

## Bot API 10.x

| Version | Date | Theme |
|---|---|---|
| **10.3** | 2026-08-24 | Rich message buttons; `EphemeralMessageParameters` replaces the per-method ephemeral params; `DisabledButton` and `InlineKeyboardButton.disabled`; `force_reply` on both keyboard markups; `MessageGenerationStopped`; `CommunityChatJoined` |
| 10.2 | 2026-07-14 | Ephemeral messages; rich message blocks; `BotSubscriptionUpdated` + `Update.subscription`; **Mini App origin hardening** |
| 10.1 | 2026-06-11 | `chat_join_request_query_id` on `WebAppInitData` |
| 10.0 | 2026-05-08 | Poll overhaul (min options 2→1, media in options); communities |

### 10.3 breaking-ish change

The ephemeral-message parameters `receiver_user_id` and `callback_query_id`, added to
thirteen send methods in 10.2, were **replaced** one release later by a single
`ephemeral_message_parameters` object. Code written against 10.2 needs updating.

## Things that have not changed in years

`sendMessage`, `sendPhoto`, `sendMediaGroup`, the webhook contract and the error model
are stable across 7.x → 10.x. Stale training data is low risk there.

It is **high** risk for Mini Apps, Stars/payments, Business accounts, gifts, checklists,
rich messages and communities — all of which arrived or changed substantially after most
models' cutoffs. Verify anything in that group against the live spec.

## Library → Bot API support

Verified 2026-09-20. A library one release behind cannot see the newest types at all —
the update field simply does not deserialize.

| Library | Version | Bot API | Notes |
|---|---|---|---|
| aiogram (Python) | 3.31.0 | **10.3** | Default branch is `dev-3.x`, not `main`. Tracks releases within days. Requires Python ≥3.10. |
| python-telegram-bot | 22.8 | trails | Check its README's "all types and methods of Bot API X" line before relying on a recent type. |
| grammY (TS/JS) | 1.46.0 | tracks closely | `@grammyjs/types` carries the surface. |
| telegraf (TS/JS) | 4.16.3 | trails significantly | Verify before choosing it for anything recent. |

Re-check rather than trust this table:

```bash
curl -s https://raw.githubusercontent.com/aiogram/aiogram/dev-3.x/aiogram/__meta__.py | grep api_version
curl -s https://pypi.org/pypi/python-telegram-bot/json | python3 -c 'import sys,json;print(json.load(sys.stdin)["info"]["version"])'
curl -s https://registry.npmjs.org/grammy/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])'
```
