# HTML widgets and TON wallets

New in **Bot API 10.4** (2026-11-09). 8 methods and 27 types, almost all of it widgets and TON.

**No library supports this yet** — aiogram is still on 10.3. Until one catches up, the
`widget_query` update will not deserialize and you are calling the HTTP API by hand.

## What a widget is

An HTML widget inside a message (`Widget`, carried on `Message.widget` and
`ExternalReplyInfo.widget`). The user interacts with it, and it sends your bot a
`WidgetQuery` you answer. `sendWidget` creates one; `sendSharedWidget` re-sends a shared
widget the bot already created.

## The constraints that will bite

Each of these is stated in the reference and each fails as a rejected call or a dead widget
rather than anything obvious.

| Constraint | Detail |
|---|---|
| **Private chats only** | In the production environment `sendWidget` and `sendSharedWidget` deliver only to private chats. Group and channel sends are not available yet. |
| **Always protected** | Sent widgets *automatically* get protected content, so they cannot be forwarded. You do not opt into this and cannot opt out. |
| **Never copyable** | Widget messages cannot be copied with `copyMessage` or `copyMessages`. A broadcast built on `copyMessage` silently cannot carry one. |
| **Not inline yet** | `InputWidgetMessageContent` and `InputSharedWidgetMessageContent` exist, but widgets cannot be sent in response to inline queries in production. |
| **Restricted by `can_send_other_messages`** | That right in `ChatPermissions` / `ChatMemberRestricted` now also governs widgets. |

## Answering a query is not updating the widget

The single easiest mistake here:

- `answerWidgetQuery` must be called **within 15 seconds**. Its answer reaches only the widget
  that sent the query and **does not change the widget's data**.
- To change what the widget shows, call `editMessageWidgetData` (a widget in a message the bot
  sent, or sent via the bot) or `editSharedWidgetData` (a shared widget's public data).

Answer *and* edit if you want both a reply and a visible change. Answering alone leaves the
widget showing stale data; editing alone leaves the query unanswered until it times out.

## Documented rate limits

Unlike the send path, these are in the API reference itself:

| Limit | Scope |
|---|---|
| **5 queries per 5 seconds** | Per user, across *all* of the bot's widgets — not per widget. |
| **Public data: once per second** | `editSharedWidgetData` on a shared widget's public data. |
| **15 seconds to answer** | `answerWidgetQuery`, same budget as an ephemeral reply. |

## Updates to subscribe to

Two new `Update` fields. Neither arrives unless you add it to `allowed_updates`:

| Field | Type | Source |
|---|---|---|
| `widget_query` | `WidgetQuery` | A widget in a message the bot sent, or sent via the bot |
| `shared_widget_query` | `SharedWidgetQuery` | A *forwarded* message carrying a shared widget the bot created |

## TON wallet

`WidgetQueryType` is a union describing what a query carries:

| Variant | Carries |
|---|---|
| `WidgetQueryTypeData` | Bot-defined data plus the user's TON wallet card |
| `WidgetQueryTypeSignData` | Data signed by one of the user's TON wallets |
| `WidgetQueryTypeSentTransaction` | Notification that a transaction was sent from a TON wallet |

Supporting types: `WidgetQueryWallet`, `TonWalletCard`, `TonWalletCardSticker`, `TonNft`,
`TonNftAttribute`. `ChatFullInfo.ton_wallet_card` exposes a user's card;
`Message.ton_wallet_transfer` is the service message for a transfer.

A signature or a transaction notification arriving over the Bot API is a **claim relayed
through Telegram**, not a settled transfer. Verify on-chain before granting anything of value —
the same rule as any payment callback, and `WidgetQueryTypeSentTransaction` is explicitly a
*notification*.

## Also in 10.4

- **`StoryAreaPosition` is renamed `AreaPosition`** — a breaking rename, because the type now
  also positions stickers on TON wallet cards. Code referencing the old name breaks.
- **Ephemeral replies got easier.** `callback_query_id` alone, with no `receiver_user_id`, now
  works in any chat except channel direct-messages chats, and `receiver_user_id` plus the send
  methods' `chat_id` are both optional. See `versions.md` for the 10.2 → 10.3 → 10.4 arc.
- **New `MessageEntity` types:** `ton_address` and `bank_card_number`. A parser switching
  exhaustively on entity type needs both, and `RichTextTonAddress` is the rich-message
  equivalent.
- **Rich-message quoting:** `TextQuote.rich_texts` and `ReplyParameters.quote_rich_texts`.
- `getUniqueGift` (look up a unique gift by name), `deleteBusinessAccountGift` (delete a managed
  business account's regular gift without taking Stars for it),
  `getChatShareThemeBackdrops` plus `ChatFullInfo.share_theme`, and
  `Message.paid_messages_waived`.
- `verifyUser` / `verifyChat` gained `custom_description_parse_mode` and
  `custom_description_entities`.
