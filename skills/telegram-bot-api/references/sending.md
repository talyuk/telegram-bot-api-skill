# Sending messages: formatting, media, keyboards

## Transport

`https://api.telegram.org/bot<TOKEN>/METHOD_NAME`, HTTPS only, GET or POST. Parameters
may be passed as a URL query string, `application/x-www-form-urlencoded`,
`application/json` (not for file uploads), or `multipart/form-data` (required for
uploads). Method names are case-insensitive; all queries must be UTF-8.

When answering a webhook you may return the method call itself as the response body —
set the `method` parameter and use one of the three non-upload content types. You cannot
learn whether such a call succeeded, so use it only for fire-and-forget replies.

## Parse mode: use HTML

Three modes exist: `HTML`, `MarkdownV2`, and legacy `Markdown`. **Choose HTML for
anything with interpolated data.**

MarkdownV2 requires escaping 18 characters outside entities:

```
_ * [ ] ( ) ~ ` > # + - = | { } . !
```

That set includes `.` `-` `+` `(` `)` — characters present in almost every price,
address, phone number and measurement. One missed escape is a `400 Bad Request: can't
parse entities`, at send time.

HTML requires escaping three characters in body text — `&` → `&amp;`, `<` → `&lt;`,
`>` → `&gt;` — plus `"` → `&quot;` inside attribute values. Only `&lt; &gt; &amp; &quot;`
and numeric entities are supported; no other named entity is.

Supported HTML tags: `b`/`strong`, `i`/`em`, `u`/`ins`, `s`/`strike`/`del`,
`span class="tg-spoiler"`/`tg-spoiler`, `a href`, `tg-emoji emoji-id`, `code`, `pre`,
`blockquote`, `blockquote expandable`. Language for a `pre` block goes on a nested
`code class="language-python"`; a standalone `code` tag cannot carry a language.

Nesting rules: if two entities share characters, one must be fully contained in the
other. `bold`, `italic`, `underline`, `strikethrough`, `spoiler` nest freely except
inside `pre`/`code`. `blockquote` and `expandable_blockquote` cannot nest. Nothing else
may contain anything else.

### Escaping is not optional and not partial

Escape the **data**, then assemble the markup. Escaping after assembly destroys your own
tags. Never pass user- or third-party-supplied text through unescaped: a listing title
containing `<` is a 400 at best, and a crafted one injects markup.

### Alternative: skip parse_mode entirely

Pass `entities` (or `caption_entities`) — an array of `MessageEntity` with explicit
`offset`/`length` — and no `parse_mode`. Offsets are in **UTF-16 code units**, so
emoji and other astral-plane characters count as 2. This is immune to escaping bugs and
is the right call when the text is assembled from many untrusted fragments.

A parser that switches exhaustively on `MessageEntity.type` needs the full set — 10.4 added
`ton_address` and `bank_card_number`. Run `scripts/tg-api.py show MessageEntity` for the
current list rather than hardcoding one.

## Custom emoji and user mentions

`tg://user?id=<user_id>` mentions a user without a username, but **only** inside an
inline link or an inline keyboard button — not in plain message text. It is only
guaranteed to resolve if the user has previously messaged the bot privately or sent it a
callback query, and does not have Forwarded Messages privacy enabled for the bot.

Custom emoji entities are restricted to bots that bought additional usernames on
Fragment, or to messages the bot sends directly when its owner has Telegram Premium.
Always supply a real fallback emoji — it renders wherever custom emoji cannot.

## Link previews

`link_preview_options` (a `LinkPreviewOptions`, Bot API 7.0) supersedes the deprecated
`disable_web_page_preview` boolean:

- `is_disabled` — suppress the preview card. The link stays clickable; the card and the
  entity are independent.
- `url` — preview a different URL than the one in the text.
- `prefer_small_media` / `prefer_large_media` — size of the preview image.
- `show_above_text` — render the card above the message instead of below.

Captions on media have no preview card, so this is irrelevant to `sendPhoto` et al.

## Media

`sendMediaGroup` takes **2–10 items** and has **no `reply_markup`** — an album cannot
carry an inline keyboard. A single-item group is a 400; branch to `sendPhoto` at N=1.
Documents and audio can only be grouped with their own type. Put the caption on the
first item.

To attach buttons to an album, send the album then a separate `sendMessage` carrying the
keyboard — and account for both in your rate budget.

`show_caption_above_media` (Bot API 7.4) moves the caption above the media.
`has_spoiler` blurs it until tapped.

See `limits.md` §3 for the per-transport size ceilings, which differ and are routinely
misremembered.

## Inline keyboards

`InlineKeyboardButton` — exactly one of the type fields must be set, alongside `text`:

| Field | Notes |
|---|---|
| `callback_data` | **1–64 bytes.** Budget it; see below. |
| `url` | HTTP or `tg://` |
| `web_app` | Launches a Mini App; returns data via `answerWebAppQuery` |
| `login_url` | Telegram Login |
| `switch_inline_query` / `_current_chat` / `_chosen_chat` | Inline mode |
| `copy_text` | `CopyTextButton`, text 1–256 chars, copies to clipboard with no round trip. **Bot API 7.11** |
| `callback_game`, `pay` | Games, invoices |
| `disabled` | `DisabledButton` — renders inert. **Bot API 10.3** |

Cosmetic, on any button (**Bot API 9.4**): `style` — one of `"danger"` (red),
`"success"` (green), `"primary"` (blue) — and `icon_custom_emoji_id`.
`InlineKeyboardMarkup` and `ReplyKeyboardMarkup` also gained `force_reply` in 10.3.

### The 64-byte callback_data budget

64 **bytes**, not characters. Cyrillic and other non-Latin text costs 2 bytes per
character, so a payload that fits during development overflows in production, and the
failure is a 400 at send time — not a construction-time error.

Never serialize display strings into `callback_data`. Put a short verb and opaque ids
in it, and keep the human-readable state server-side:

```
d:<draft>:<field>:<value_id>      # 1-2 char verb, ids only
```

`answerCallbackQuery` must be called for every callback query, even when you do nothing
— otherwise the client shows a spinner until it times out. Its `text` is 0–200 chars.

## Message ordering and edits

`editMessageText` and friends need the original `chat_id` + `message_id` (or
`inline_message_id`). Editing to identical content returns
`400 Bad Request: message is not modified` — guard against it rather than treating it as
a failure.

`deleteMessages` / `forwardMessages` / `copyMessages` take 1–100 ids per call.

**Widget messages cannot be copied** with `copyMessage` or `copyMessages`, and are always sent
with protected content so they cannot be forwarded either (Bot API 10.4 — see `widgets.md`). A
broadcast built on `copyMessage` silently cannot carry one.
