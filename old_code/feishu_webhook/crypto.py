"""Feishu event signature verification and AES decrypt helpers."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def verify_signature(
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    body: bytes,
    signature: str,
) -> bool:
    if not encrypt_key:
        return True
    if not signature:
        return False
    prefix = f"{timestamp}{nonce}{encrypt_key}".encode("utf-8")
    digest = hashlib.sha256(prefix + body).hexdigest()
    return digest == signature


def decrypt_encrypt_field(encrypt_key: str, encrypt_b64: str) -> dict[str, Any]:
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    raw = base64.b64decode(encrypt_b64)
    iv, ciphertext = raw[:16], raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return json.loads(plaintext.decode("utf-8"))


def parse_request_body(encrypt_key: str, body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode("utf-8"))
    if "encrypt" in data and encrypt_key:
        return decrypt_encrypt_field(encrypt_key, data["encrypt"])
    return data

