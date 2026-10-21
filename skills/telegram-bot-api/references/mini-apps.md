# Mini Apps (Web Apps)

Mini Apps track Bot API versions but move on their own cadence — the latest Mini App
change was **Bot API 10.1** (2026-06-11, `chat_join_request_query_id` on
`WebAppInitData`), even though the Bot API itself is at 10.3.

## Where initData comes from

Telegram opens the app at your URL with everything in the **URL fragment**, not the
query string:

```
https://your.app/#tgWebAppData=...&tgWebAppVersion=9.6&tgWebAppPlatform=ios&tgWebAppThemeParams=...
```

The fragment is never sent to the server on the initial request, so **the page's own GET
carries no identity**. `telegram-web-app.js` parses the fragment and exposes:

- `Telegram.WebApp.initData` — the raw signed query string. This is what you POST to
  your backend.
- `Telegram.WebApp.initDataUnsafe` — the same data pre-parsed. Named "unsafe" because it
  is client-side and unauthenticated. **Never** use it for an authorization decision.

Practical consequence: the HTML page itself must be rendered without knowing who the
user is. Language, theme and any personalization either come from a later authenticated
API call, or are a guess (`Accept-Language`) that the app corrects once `initData` is
validated.

## Validating initData

Two schemes with **different exclusion rules**. Getting them confused is the usual bug.

| | Key | Excluded from check string | Prefix |
|---|---|---|---|
| First-party | HMAC-SHA256 with the bot token | **`hash` only** — `signature` is signed data and stays in | none |
| Third-party | Ed25519, Telegram's public key | **`hash` and `signature`** | `<bot_id>:WebAppData\n` |

Working, tested implementation of both: **`scripts/initdata.py`** in this skill.

### The four ways this goes wrong

1. **Argument order.** `secret_key = HMAC_SHA256(<bot_token>, "WebAppData")` in the docs
   reads backwards. The constant `"WebAppData"` is the **key**; the token is the
   **message**: `hmac.new(b"WebAppData", token, sha256)`.
2. **Dropping `signature` from the HMAC check string.** Only `hash` comes out. aiogram's
   `check_webapp_signature` pops exactly `hash` — match that.
3. **Re-encoding values.** Hash the decoded strings exactly as parsed. A Cyrillic
   `first_name` makes this fail 100% of the time rather than intermittently, which is
   the lucky version.
4. **`parse_qsl` rewrites `+` to a space.** It applies `unquote_plus` semantics. If any
   value arrives with a raw, un-percent-encoded `+`, the check string no longer matches
   what Telegram signed and a valid payload is rejected. Measured: with a raw `+` in
   `start_param`, `parse_qsl`-based validation rejects a correctly signed payload while a
   manual `unquote` parser accepts it. Parse by hand with `unquote`, which leaves `+`
   alone. (aiogram uses `parse_qsl` and carries this exposure.)

Also: compare with a constant-time comparison, and check `auth_date` freshness —
the signature never expires on its own.

### Telegram's Ed25519 public keys

```
production  e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d
test        40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec
```

Both are exactly **64 hex characters = 32 bytes**. Transcribe them, never retype them:
a truncated key fails with "an Ed25519 public key is 32 bytes long" in Python, but in
looser stacks it rejects every payload while looking like a signature mismatch.

## Origin hardening — live since 2026-07-20

Bot API 10.2 disallowed calling Mini App methods from any origin other than the Mini
App's own domain. The protection was enabled automatically for all Mini Apps on
**July 20, 2026**; you can opt out via the @BotFather Mini App, accepting responsibility
for any links to untrusted sites.

**An embedded iframe — a map, an analytics widget, a payment frame — cannot call
`window.Telegram.WebApp`.** Keep every Telegram call in your own top-level document and
`postMessage` into the frame. Do not opt out to avoid refactoring.

## Launch surfaces

| Surface | Gets `initData`? | Can send a message back? |
|---|---|---|
| Keyboard button (`KeyboardButton.web_app`) | yes | `sendData()` → a service message to the bot |
| Inline keyboard button (`InlineKeyboardButton.web_app`) | yes | `answerWebAppQuery` |
| Menu button (`setChatMenuButton`) | yes | via your own API |
| Direct link (`t.me/bot/app`) | yes | via your own API |
| Inline mode / attachment menu | yes | `answerWebAppQuery` |

`setChatMenuButton` takes **no `language_code`** — there is one menu button per bot (or
per chat), so a multilingual bot cannot localize it per reader the way `setMyCommands`
allows.

### The sendData trap

`WebApp.sendData(data)` works **only** from a keyboard-button Mini App, closes the app
immediately, and delivers ≤4096 bytes as a service message. It does not work from an
inline button, a menu button or a direct link. If you need a request/response, call your
own backend over HTTPS with `initData` in a header instead.

## WebApp JS API — version gates

The runtime is whatever the user's client shipped, which may be far older than the
current Bot API. Feature-detect with `WebApp.isVersionAtLeast('8.0')` and degrade;
calling a method the client does not know is silently ignored on some platforms.

| Since | Members |
|---|---|
| 6.0 | `initData`, `initDataUnsafe`, `version`, `platform`, `colorScheme`, `themeParams`, `viewportHeight`, `viewportStableHeight`, `ready()`, `expand()`, `close()`, `sendData()`, `onEvent()`, `offEvent()`, `openLink()`, `openTelegramLink()`, `isVersionAtLeast()`, `MainButton`, `SecondaryButton`, `BackButton`, `SettingsButton`, `HapticFeedback`, `CloudStorage`, `BiometricManager` |
| 6.1 | `setHeaderColor()`, `setBackgroundColor()`, `openInvoice()` |
| 6.2 | `showPopup()`, `showAlert()`, `showConfirm()`, `enableClosingConfirmation()` |
| 6.4 | `showScanQrPopup()`, `closeScanQrPopup()`, `readTextFromClipboard()` |
| 6.7 | `switchInlineQuery()` |
| 6.9 | `requestWriteAccess()`, `requestContact()`, `CloudStorage` item methods |
| 7.7 | `enableVerticalSwipes()`, `disableVerticalSwipes()` |
| 7.8 | `shareToStory()` |
| 7.10 | `setBottomBarColor()` |
| 8.0 | `requestFullscreen()`, `exitFullscreen()`, `lockOrientation()`, `addToHomeScreen()`, `shareMessage()`, `setEmojiStatus()`, `downloadFile()`, `Accelerometer`, `DeviceOrientation`, `Gyroscope`, `LocationManager`, `safeAreaInset`, `isActive` |
| 9.0 | `DeviceStorage`, `SecureStorage` |
| 9.1 | `hideKeyboard()` |
| 9.5 | `BottomButton.iconCustomEmojiId` |
| 9.6 | `requestChat()` |

## Testing

Mini Apps only run inside a Telegram client. `eruda`/`vConsole` plus Telegram's debug
mode (enable in the client's experimental settings) is the practical debugging route on
mobile; Telegram Desktop and Web can open devtools directly.

Counting and plurals in the browser must come from `Intl.PluralRules` over the reader's
language, not a hand-rolled rule — Polish disagrees with Russian at 21, 31, 41 and 101,
which is exactly the case that survives a demo and fails in production.
