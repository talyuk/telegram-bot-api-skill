#!/usr/bin/env python3
"""Fixtures for initdata.py. Run: python3 scripts/test_initdata.py

Signs payloads with a throwaway token/keypair and checks that validation accepts
exactly what it should. The Ed25519 cases use a generated keypair, not Telegram's
real key, so they exercise the construction rather than the constant.
"""
import base64, hashlib, hmac, json, os, sys, time
from urllib.parse import quote, parse_qsl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from initdata import validate, validate_third_party, InitDataError, _parse

TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
NOW = str(int(time.time()))
USER = json.dumps({"id": 1, "first_name": "Алексей", "last_name": "O'Brien"}, ensure_ascii=False)
fails = []


def enc(d):
    return "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in d.items())


def sign(fields):
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    return enc(fields) + "&hash=" + hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()


def check(name, fn, should_pass):
    global fails
    try:
        fn()
        got, why = True, ""
    except (InitDataError, Exception) as e:
        got, why = False, f" ({type(e).__name__}: {str(e)[:50]})"
    ok = got == should_pass
    if not ok:
        fails.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:34} {'accepted' if got else 'rejected'}{why}")


print("first-party (HMAC, bot token)")
raw_plus = sign({"auth_date": NOW, "user": USER, "start_param": "a+b"}).replace("a%2Bb", "a+b")
for name, data, expect in [
    ("cyrillic user",            sign({"auth_date": NOW, "query_id": "AAE", "user": USER}), True),
    ("signature present (kept)", sign({"auth_date": NOW, "user": USER, "signature": "ab_-12"}), True),
    ("raw '+' in value",         raw_plus, True),
    ("empty value",              sign({"auth_date": NOW, "user": USER, "start_param": ""}), True),
    ("tampered payload",         sign({"auth_date": NOW, "user": USER}).replace(
                                     quote("Алексей", safe=''), quote("Мария", safe='')), False),
    ("stale auth_date",          sign({"auth_date": "1600000000", "user": USER}), False),
    ("missing hash",             "auth_date=" + NOW, False),
    ("duplicate key",            sign({"auth_date": NOW, "user": USER}) + "&auth_date=1", False),
]:
    check(name, lambda d=data: validate(d, TOKEN), expect)
check("wrong bot token", lambda: validate(sign({"auth_date": NOW, "user": USER}), "999:WRONG"), False)

print("\nthe parse_qsl trap (why _parse exists)")
signed_plus = _parse(raw_plus)["start_param"]
naive_plus = dict(parse_qsl(raw_plus))["start_param"]
print(f"  signed value {signed_plus!r}; parse_qsl yields {naive_plus!r}")
if signed_plus == "a+b" and naive_plus == "a b":
    print("  PASS  parse_qsl would corrupt this payload; _parse does not")
else:
    fails.append("parse_qsl trap"); print("  FAIL  trap no longer reproduces")

print("\nthird-party (Ed25519, generated keypair)")
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    BOT_ID = 12345678
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes_raw()
    f = {"auth_date": NOW, "query_id": "AAE", "user": USER}
    dcs = f"{BOT_ID}:WebAppData\n" + "\n".join(f"{k}={f[k]}" for k in sorted(f))
    sig = base64.urlsafe_b64encode(priv.sign(dcs.encode())).decode().rstrip("=")
    data = enc(f) + f"&signature={sig}&hash=deadbeef"
    check("valid signature",  lambda: validate_third_party(data, BOT_ID, pub), True)
    check("tampered payload", lambda: validate_third_party(
        data.replace(quote("Алексей", safe=''), quote("Мария", safe='')), BOT_ID, pub), False)
    check("wrong bot_id",     lambda: validate_third_party(data, 999, pub), False)
    check("31-byte key",      lambda: validate_third_party(data, BOT_ID, pub[:31]), False)
    for label, key in [("prod", "e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d"),
                       ("test", "40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec")]:
        n = len(bytes.fromhex(key))
        print(f"  {'PASS' if n == 32 else 'FAIL'}  shipped {label} key is {n} bytes")
        if n != 32:
            fails.append(f"{label} key length")
except ImportError:
    print("  SKIP  install `cryptography` to exercise the Ed25519 path")

print("\n" + ("FAILED: " + ", ".join(fails) if fails else "all checks passed"))
sys.exit(1 if fails else 0)
