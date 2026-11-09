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
| **10.4** | 2026-11-09 | HTML widgets and TON wallets (8 methods, 27 types — see `widgets.md`); `StoryAreaPosition` renamed `AreaPosition`; ephemeral replies relaxed; `ton_address` and `bank_card_number` entity types; rich-message quoting |
| 10.3 | 2026-08-24 | Rich message buttons; `EphemeralMessageParameters` replaces the per-method ephemeral params; `DisabledButton` and `InlineKeyboardButton.disabled`; `force_reply` on both keyboard markups; `MessageGenerationStopped`; `CommunityChatJoined` |
| 10.2 | 2026-07-14 | Ephemeral messages; rich message blocks; `BotSubscriptionUpdated` + `Update.subscription`; **Mini App origin hardening** |
| 10.1 | 2026-06-11 | `chat_join_request_query_id` on `WebAppInitData` |
| 10.0 | 2026-05-08 | Poll overhaul (min options 2→1, media in options); communities |

### Two renames and a three-release churn

**`StoryAreaPosition` became `AreaPosition` in 10.4**, because it now also positions stickers
on TON wallet cards. A rename is a break: code referencing the old name stops compiling or
deserializing.

The ephemeral-message surface has moved in each of the last three releases:

| Release | State |
|---|---|
| 10.2 | `receiver_user_id` and `callback_query_id` added as parameters to thirteen send methods |
| 10.3 | Both **replaced** by a single `ephemeral_message_parameters` object |
| 10.4 | `callback_query_id` alone now works in any chat except channel direct-messages chats; `receiver_user_id` and the methods' `chat_id` are both optional |

Code written against any one of those three needs checking against the others.

## Things that have not changed in years

`sendMessage`, `sendPhoto`, `sendMediaGroup`, the webhook contract and the error model
are stable across 7.x → 10.x. Stale training data is low risk there.

It is **high** risk for Mini Apps, Stars/payments, Business accounts, gifts, checklists,
rich messages and communities — all of which arrived or changed substantially after most
models' cutoffs. Verify anything in that group against the live spec.

## Library → Bot API support

Verified 2026-11-09, the day 10.4 shipped. A library one release behind cannot see the newest
types at all — the update field simply does not deserialize.

**Nothing supports 10.4 yet.** Until a library catches up, `widget_query` and the TON types are
reachable only by calling the HTTP API directly.

| Library | Version | Bot API | Notes |
|---|---|---|---|
| aiogram (Python) | 3.31.0 | **10.3** | Default branch is `dev-3.x`, not `main`. Historically tracks releases within days, so check again rather than trusting this row. Requires Python ≥3.10. |
| python-telegram-bot | 22.8 | trails | Check its README's "all types and methods of Bot API X" line before relying on a recent type. |
| grammY (TS/JS) | 1.46.0 | trails | `@grammyjs/types` carries the surface. |
| telegraf (TS/JS) | 4.16.3 | trails significantly | Verify before choosing it for anything recent. |

Re-check rather than trust this table:

```bash
curl -s https://raw.githubusercontent.com/aiogram/aiogram/dev-3.x/aiogram/__meta__.py | grep api_version
curl -s https://pypi.org/pypi/python-telegram-bot/json | python3 -c 'import sys,json;print(json.load(sys.stdin)["info"]["version"])'
curl -s https://registry.npmjs.org/grammy/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])'
```
