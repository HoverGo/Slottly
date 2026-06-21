import pytest
from pydantic import ValidationError

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.schemas import PasswordChange, UserRegister


def test_password_hash_and_verify():
    hashed = hash_password("Password123")
    assert hashed != "Password123"
    assert verify_password("Password123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token("user-uuid")
    assert decode_access_token(token) == "user-uuid"
    assert decode_access_token("invalid.token.here") is None


def test_register_password_requires_digit():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.com", password="PasswordOnly", full_name="Test")


def test_register_password_requires_letter():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.com", password="12345678", full_name="Test")


def test_password_change_validators():
    with pytest.raises(ValidationError):
        PasswordChange(current_password="Password1", new_password="Password1")
