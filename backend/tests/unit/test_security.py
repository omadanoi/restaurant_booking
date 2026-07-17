import uuid

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hashes_are_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_password_with_malformed_hash_returns_false() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "customer")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "customer"
    assert payload["type"] == "access"


def test_tampered_token_rejected() -> None:
    token = create_access_token(uuid.uuid4(), "customer")
    with pytest.raises(AuthenticationError):
        decode_access_token(token[:-2] + "xx")


def test_garbage_token_rejected() -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token("definitely-not-a-jwt")


def test_refresh_tokens_are_unique_and_hashed_deterministically() -> None:
    raw1, raw2 = generate_refresh_token(), generate_refresh_token()
    assert raw1 != raw2
    assert hash_refresh_token(raw1) == hash_refresh_token(raw1)
    assert hash_refresh_token(raw1) != hash_refresh_token(raw2)
    assert len(hash_refresh_token(raw1)) == 64  # sha256 hex
