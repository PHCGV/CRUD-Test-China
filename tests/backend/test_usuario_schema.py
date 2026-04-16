import pytest
from pydantic import ValidationError
from app.schemas.usuario_schema import UsuarioCreate, UsuarioEsqueciSenha, UsuarioRedefinirSenha


def test_usuario_create_aplica_perfil_default_usuario():
    payload = UsuarioCreate(
        nome="Maria Silva",
        username="maria.silva",
        senha="SenhaForte123",
        email="maria@example.com",
    )

    assert payload.perfil == "USUARIO"


def test_usuario_esqueci_senha_valida_email():
    with pytest.raises(ValidationError):
        UsuarioEsqueciSenha(email="email-invalido")


def test_usuario_redefinir_senha_exige_token_minimo():
    with pytest.raises(ValidationError):
        UsuarioRedefinirSenha(token="x" * 31, nova_senha="NovaSenha123")

    ok = UsuarioRedefinirSenha(token="x" * 32, nova_senha="NovaSenha123")
    assert len(ok.token) == 32
