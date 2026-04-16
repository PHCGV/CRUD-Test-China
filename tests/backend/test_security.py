import os
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.config import security
from app.models.usuario import Usuario


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    security._FAILED_LOGIN_ATTEMPTS.clear()
    security._LOCKED_LOGIN_UNTIL.clear()
    yield
    security._FAILED_LOGIN_ATTEMPTS.clear()
    security._LOCKED_LOGIN_UNTIL.clear()


def make_user(*, perfil: str = "USUARIO", user_id: int = 1) -> Usuario:
    return Usuario(
        id_usuario=user_id,
        nome="Usuario Teste",
        username="usuario.teste",
        senha_hash="hash",
        perfil=perfil,
        token_version=1,
    )


def test_parse_int_env_valida_limites(monkeypatch):
    monkeypatch.setenv("SEC_TEST_INT", "abc")
    assert security._parse_int_env("SEC_TEST_INT", 10, 5, 20) == 10

    monkeypatch.setenv("SEC_TEST_INT", "999")
    assert security._parse_int_env("SEC_TEST_INT", 10, 5, 20) == 20

    monkeypatch.setenv("SEC_TEST_INT", "1")
    assert security._parse_int_env("SEC_TEST_INT", 10, 5, 20) == 5


def test_create_and_decode_access_token_roundtrip():
    token = security.create_access_token(
        {
            "sub": "7",
            "username": "admin",
            "perfil": "ADMIN",
            "tv": 3,
        },
        expires_minutes=15,
    )

    payload = security.decode_token(token)

    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["tv"] == 3
    assert payload["type"] == "access"
    assert payload["iss"] == security.TOKEN_ISSUER


def test_decode_token_rejeita_claims_obrigatorias_ausentes():
    token_sem_sub = security.create_access_token({"username": "sem-sub", "tv": 1}, expires_minutes=5)
    assert security.decode_token(token_sem_sub) is None


def test_login_rate_limit_bloqueia_apos_limite_de_falhas():
    username = "joao"
    ip = "127.0.0.1"

    for _ in range(security.AUTH_MAX_FAILED_ATTEMPTS):
        security.register_failed_login(username, ip)

    with pytest.raises(HTTPException) as exc_info:
        security.check_login_allowed(username, ip)

    assert exc_info.value.status_code == 429


def test_clear_login_failures_remove_bloqueio():
    username = "joao"
    ip = "127.0.0.1"

    for _ in range(security.AUTH_MAX_FAILED_ATTEMPTS):
        security.register_failed_login(username, ip)

    security.clear_login_failures(username, ip)

    security.check_login_allowed(username, ip)


def test_require_admin_permite_apenas_admin():
    admin = make_user(perfil="ADMIN")
    assert security.require_admin(admin) is admin

    with pytest.raises(HTTPException) as exc_info:
        security.require_admin(make_user(perfil="USUARIO"))

    assert exc_info.value.status_code == 403


def test_require_same_user_or_admin():
    usuario = make_user(perfil="USUARIO", user_id=12)
    assert security.require_same_user_or_admin(12, usuario) is usuario

    admin = make_user(perfil="ADMIN", user_id=99)
    assert security.require_same_user_or_admin(12, admin) is admin

    with pytest.raises(HTTPException) as exc_info:
        security.require_same_user_or_admin(50, usuario)

    assert exc_info.value.status_code == 403


def test_require_roles_restringe_perfis():
    checker = security.require_roles("ADMIN", "SUPORTE")

    assert checker(make_user(perfil="ADMIN"))

    with pytest.raises(HTTPException) as exc_info:
        checker(make_user(perfil="USUARIO"))

    assert exc_info.value.status_code == 403


class _FakeConnection:
    def close(self):
        return None


class _FakeUsuarioDAO:
    def __init__(self, _conn):
        pass

    def ReadById(self, user_id):
        return make_user(perfil="ADMIN", user_id=user_id)


def test_get_current_access_user_rejeita_token_extensao(monkeypatch):
    monkeypatch.setattr(security, "conectar", lambda: _FakeConnection())
    monkeypatch.setattr(security, "UsuarioDAO", _FakeUsuarioDAO)
    monkeypatch.setattr(
        security,
        "decode_token",
        lambda _token: {
            "sub": "7",
            "tv": 1,
            "type": "extension",
            "aud": security.EXTENSION_TOKEN_AUDIENCE,
        },
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake")

    with pytest.raises(HTTPException) as exc_info:
        security.get_current_access_user(creds)

    assert exc_info.value.status_code == 401


def test_get_current_user_aceita_token_extensao_valido(monkeypatch):
    monkeypatch.setattr(security, "conectar", lambda: _FakeConnection())
    monkeypatch.setattr(security, "UsuarioDAO", _FakeUsuarioDAO)
    monkeypatch.setattr(
        security,
        "decode_token",
        lambda _token: {
            "sub": "9",
            "tv": 1,
            "type": "extension",
            "aud": security.EXTENSION_TOKEN_AUDIENCE,
        },
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake")
    usuario = security.get_current_user(creds)

    assert usuario.id_usuario == 9
