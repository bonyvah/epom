import pytest
import jwt
from fastapi import HTTPException
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_invite_token,
    decode_invite_token,
)
from app.config import settings

def test_password_hashing_and_verification():
    password = "supersecretpassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_access_token_creation_and_decoding():
    user_id = "12345678-1234-5678-1234-567812345678"
    token = create_access_token(user_id)
    
    decoded_sub = decode_access_token(token)
    assert decoded_sub == user_id


def test_decode_access_token_missing_sub():
    # Token missing 'sub'
    payload = {"exp": 9999999999}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_decode_access_token_invalid():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("invalid.token.signature")
    assert exc_info.value.status_code == 401


def test_invite_token_creation_and_decoding():
    project_id = "abcdef12-3456-7890-abcd-ef1234567890"
    email = "test@example.com"
    
    token = create_invite_token(project_id, email)
    decoded_project_id = decode_invite_token(token)
    
    assert decoded_project_id == project_id


def test_decode_invite_token_invalid_sub():
    # Token with wrong subject (not 'invite')
    payload = {"sub": "not-invite", "project_id": "123", "email": "a@b.com"}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    with pytest.raises(HTTPException) as exc_info:
        decode_invite_token(token)
    assert exc_info.value.status_code == 400