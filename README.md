# Telegram Bot API skill

[![ci](https://github.com/talyuk/telegram-bot-api-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/talyuk/telegram-bot-api-skill/actions/workflows/ci.yml)

An [Agent Skill](https://agentskills.io) that gives Claude an accurate, current reference for the
**Telegram Bot API** and **Telegram Mini Apps** — plus a tool that queries a snapshot parsed
straight from `core.telegram.org` and refreshes it when Telegram ships a release.

Currently tracking **Bot API 10.3** (released 2026-08-24) — 185 methods, 400 types.

## Why

The Bot API ships roughly monthly, so most of its surface postdates any model's training cutoff.
Recalled limits are wrong often enough to cost a production incident, and they are wrong
*confidently* — the numbers feel precise.

These were all answered incorrectly by a capable agent working from memory:

| Claim that feels right | Actually |
|---|---|
| Photos are 10 MB whatever the transport | **By URL: 5 MB.** By upload: 10 MB. By `file_id`: unlimited. |
| 30 msg/s is a global API request cap | It applies to **bulk notifications** only. |
| You just have to stay under 30/s | `allow_paid_broadcast` raises it to **1000/s** at 0.1 Stars per message. |
| Telegram sends `Retry-After` headers | It sends **none**. Read `parameters.retry_after` from the body. |
| `copy_text` buttons came in 7.5 | **7.11.** |
| A poll takes 2–10 options | **1–12** since 9.1/10.0. |
| `signature` is excluded from the initData HMAC | Only **`hash`** is. |

The skill replaces recall with a one-command lookup.

## Install

### Claude Code

```
/plugin marketplace add talyuk/telegram-bot-api-skill
```

Then `Browse and install plugins` → `telegram-bot-api-skill` → `telegram-bot-api` → `Install now`.

### Manually

Clone it anywhere and symlink the skill into your agent's skills directory:

```bash
git clone https://github.com/talyuk/telegram-bot-api-skill.git
ln -s "$PWD/telegram-bot-api-skill/skills/telegram-bot-api" ~/.claude/skills/telegram-bot-api
```

`~/.agents/skills/` works as a cross-runtime location (Codex, Copilot CLI, Gemini CLI also read it).

## What's inside

```
skills/telegram-bot-api/
├── SKILL.md                     index, the corrections table, rules worth applying unprompted
├── references/
│   ├── limits.md                rate limits (official vs folklore), paid broadcasts,
│   │                            file-size ceilings per transport, every length limit
│   ├── errors.md                response envelope, three-bucket error classification with
│   │                            exact `description` substrings, backoff, idempotency
│   ├── sending.md               parse-mode choice and escaping, entities, link previews,
│   │                            media groups, keyboards, the 64-byte callback_data budget
│   ├── updates.md               polling vs webhooks, allowed_updates, Update fields, scopes
│   ├── mini-apps.md             initData delivery, both validation schemes, origin
│   │                            hardening, launch surfaces, WebApp JS version gates
│   ├── payments.md              Stars vs card rails, invoices, pre-checkout, subscriptions
│   └── versions.md              changelog navigation, 10.x summary, library support
└── scripts/
    ├── tg-api.py                query + refresh tool
    ├── spec.json                the parsed snapshot (601 entries, 82 releases)
    ├── initdata.py              tested initData validator, both schemes
    └── test_initdata.py         its fixtures
```

## The tool

```bash
scripts/tg-api.py show sendPhoto       # real parameter table, with types and required flags
scripts/tg-api.py search clipboard     # find a method or type by name or summary
scripts/tg-api.py fields Message       # field names only
scripts/tg-api.py since 10.0           # changelog bullets at or after a version
scripts/tg-api.py version              # snapshot vs live — says if the snapshot is stale
scripts/tg-api.py refresh              # re-fetch core.telegram.org, rewrite spec.json
```

`show` prints the documentation's own table rather than a paraphrase of it:

```
$ scripts/tg-api.py show CopyTextButton
# CopyTextButton   [Available types]
https://core.telegram.org/bots/api#copytextbutton

This object represents an inline keyboard button that copies specified text to the clipboard.

  text  String
      The text to be copied to the clipboard; 1-256 characters
```

Standard library only — no dependencies. (`initdata.py`'s Ed25519 path needs
[`cryptography`](https://pypi.org/project/cryptography/) or PyNaCl; the HMAC path needs nothing.)

## Keeping it current

```bash
scripts/tg-api.py version
```

If it reports stale, run `refresh` and re-read whichever reference file covers what the new
release touched. The changelog is **reverse-chronological**, so when dating a feature take the
*last* mention of it — taking the first is how `CopyTextButton` gets misattributed to 7.5.

## How it was verified

Built with [test-driven skill development](https://github.com/obra/superpowers): run the
scenarios *without* the skill first, document what fails, then write the skill against those
specific failures.

- **Baseline (RED).** Three agents answered Telegram questions from memory. Failures are the
  table above — plus one that truncated Telegram's Ed25519 public key to 63 hex characters, which
  rejects every payload while reading as an ordinary signature mismatch.
- **With the skill (GREEN).** The same questions, answered correctly, including both agents
  independently flagging the reverse-chronological changelog trap.
- **Primary sources.** `spec.json` is parsed from the API reference itself. The error-string
  advice is confirmed against
  [`telegram-bot-api/Client.cpp`](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.cpp),
  where `user is deactivated` is built *with* its `Forbidden: ` prefix and
  `bot was blocked by the user` *without* it, nine lines apart — which is why the skill says to
  match the suffix, not the whole string.
- **The validator is tested, not just written.** `test_initdata.py` covers 15 cases: Cyrillic
  names, a raw `+` that breaks `parse_qsl`-based validation, tampering, wrong token, wrong
  `bot_id`, stale `auth_date`, a missing hash, and a short key.

```bash
python3 skills/telegram-bot-api/scripts/test_initdata.py
```

One thing the skill preserves rather than resolves: paid-broadcast eligibility is stated twice by
Telegram and the two disagree — the API reference says 10,000 Stars, the FAQ says 100,000 Stars
*and* 100,000 monthly active users. Still unreconciled as of 10.3, so the skill cites both.

## Contributing

Corrections welcome, especially anything measured. Please cite a primary source — the API
reference, the FAQ, or the Bot API server source — and if you change `initdata.py`, add a fixture
to `test_initdata.py`.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Telegram.
