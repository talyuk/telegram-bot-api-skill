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

Search for the class and field together, not the field name alone. Field names get reused
across classes: `subscription_period` first appears in 7.9 on `ChatInviteLink` (paid channel
invites), but `createInvoiceLink.subscription_period` — Stars subscription invoices — is 8.0.
Searching for the bare name dates the wrong feature.

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

Verified 2026-11-13. A library one release behind cannot see the newest types at all — the
update field simply does not deserialize.

**Nothing supports 10.4 yet.** aiogram and grammY both have 10.4 support open as a pull request;
until one ships, `widget_query` and the TON types are reachable only through the HTTP API.

| Library | Version | Bot API | Notes |
|---|---|---|---|
| aiogram (Python) | 3.31.0 | **10.3** | Usually ships within days of a release. Default branch is `dev-3.x`, not `main`. Python ≥3.10. |
| grammY (TS/JS) | 1.46.0 | **10.3** | Merged 10.3 support one day after the release. The surface lives in `@grammyjs/types`, whose README still says "Bot API 5.1" — old prose, not a support claim. |
| python-telegram-bot | 22.8 | **10.0** | Four releases behind; nothing from 10.1–10.4 merged. |
| telegraf (TS/JS) | 4.16.3 | **7.1** | Per its README badge. No Stars subscription invoices (8.0), ephemeral messages (10.2) or widgets (10.4). |

Re-check rather than trust this table. A package version says nothing about API support, so
each of these reads the supported API version itself:

```bash
curl -s https://raw.githubusercontent.com/aiogram/aiogram/dev-3.x/aiogram/__meta__.py | grep api_version
gh search prs --repo grammyjs/types "support Bot API" --merged --sort updated --limit 1 --json title -q '.[0].title'
curl -s https://raw.githubusercontent.com/python-telegram-bot/python-telegram-bot/master/README.rst | grep -o 'Telegram Bot API \*\*[0-9.]*\*\*'
curl -s https://raw.githubusercontent.com/telegraf/telegraf/v4/README.md | grep -o 'Bot API [0-9][0-9.]*' | head -1
```
