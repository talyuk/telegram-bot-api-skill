"""Telegram Mini App initData validation. Bot API 10.3.

Two independent schemes, deliberately kept separate:

  validate()              HMAC-SHA256 with the bot token. Excludes ONLY `hash`;
                          `signature`, when present, is part of the signed string.
  validate_third_party()  Ed25519 against Telegram's public key, for parties that
                          must not hold the bot token. Excludes BOTH `hash` and
                          `signature`, and prefixes "<bot_id>:WebAppData\\n".

Verified against signed fixtures: Cyrillic names, a raw '+' in a value, empty
values, a present `signature`, tampering, wrong token, wrong bot_id, stale
auth_date and a missing hash.

Ed25519 path needs `cryptography` (or swap in pynacl - see verify_ed25519).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import unquote

# https://core.telegram.org/bots/webapps#validating-data-for-third-party-use
# 64 hex characters == 32 bytes. A truncated key does not fail loudly at verify
# time on every library - check the length if verification rejects everything.
ED25519_PUBLIC_KEY_PROD = bytes.fromhex(
    "e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d"
)
ED25519_PUBLIC_KEY_TEST = bytes.fromhex(
    "40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec"
)

_JSON_FIELDS = ("user", "receiver", "chat")


class InitDataError(ValueError):
    """initData failed to parse or failed verification."""


def _parse(init_data: str) -> dict[str, str]:
    """Parse the query string by hand.

    NOT urllib.parse.parse_qsl: it applies unquote_plus semantics and rewrites a
    literal '+' to a space. Telegram signed the '+', so the check string no longer
    matches and a valid payload is rejected. unquote() leaves '+' alone.
    """
    if not init_data:
        raise InitDataError("empty initData")
    out: dict[str, str] = {}
    for pair in init_data.split("&"):
        if not pair:
            continue
        k, sep, v = pair.partition("=")
        if not sep:
            raise InitDataError(f"malformed pair: {pair!r}")
        key = unquote(k)
        if key in out:
            # Duplicates would make the sorted check string ambiguous.
            raise InitDataError(f"duplicate key: {key!r}")
        out[key] = unquote(v)
    return out


def _check_string(fields: dict[str, str]) -> str:
    return "\n".join(f"{k}={fields[k]}" for k in sorted(fields))


def _finish(fields: dict, auth_date: str | None, max_age: int) -> dict:
    if auth_date is None or not auth_date.isdigit():
        raise InitDataError("missing or non-numeric auth_date")
    if max_age and time.time() - int(auth_date) > max_age:
        raise InitDataError("stale initData")
    for f in _JSON_FIELDS:
        if f in fields:
            try:
                fields[f] = json.loads(fields[f])
            except json.JSONDecodeError as e:
                raise InitDataError(f"bad JSON in {f}: {e}") from e
    return fields


def validate(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """Verify initData with the bot token. Returns the parsed fields."""
    fields = _parse(init_data)
    received = fields.pop("hash", None)
    if not received:
        raise InitDataError("missing hash")

    # Note the argument order: the CONSTANT is the key, the token is the message.
    # The docs write it as HMAC_SHA256(<bot_token>, "WebAppData"), which reads
    # backwards and is the most common way to get this wrong.
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, _check_string(fields).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InitDataError("hash mismatch")
    return _finish(fields, fields.get("auth_date"), max_age)


def verify_ed25519(public_key: bytes, message: bytes, signature: bytes) -> None:
    """Raise unless `signature` is a valid Ed25519 signature over `message`."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    # pynacl equivalent:
    #   from nacl.signing import VerifyKey
    #   VerifyKey(public_key).verify(message, signature)


def validate_third_party(
    init_data: str,
    bot_id: int,
    public_key: bytes = ED25519_PUBLIC_KEY_PROD,
    max_age: int = 86400,
) -> dict:
    """Verify initData without the bot token, using Telegram's public key."""
    fields = _parse(init_data)
    sig = fields.pop("signature", None)
    fields.pop("hash", None)          # excluded here, unlike in validate()
    if not sig:
        raise InitDataError("missing signature")

    dcs = f"{bot_id}:WebAppData\n" + _check_string(fields)
    raw = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))  # padding stripped in transit
    try:
        verify_ed25519(public_key, dcs.encode(), raw)
    except Exception as e:
        raise InitDataError(f"signature verification failed: {e}") from e
    return _finish(fields, fields.get("auth_date"), max_age)
