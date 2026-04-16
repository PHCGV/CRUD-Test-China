from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UsuarioBase(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=50)


class UsuarioCreate(UsuarioBase):
    senha: str = Field(min_length=8, max_length=120)
    perfil: Literal["ADMIN", "USUARIO"] = "USUARIO"
    email: EmailStr | None = None


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None


class UsuarioAdminUpdate(UsuarioUpdate):
    perfil: Literal["ADMIN", "USUARIO"] | None = None


class UsuarioLogin(BaseModel):
    username: str
    senha: str


class UsuarioTrocaSenha(BaseModel):
    senha_atual: str = Field(min_length=8, max_length=120)
    nova_senha: str = Field(min_length=8, max_length=120)


class UsuarioResponse(UsuarioBase):
    id_usuario: int
    perfil: Literal["ADMIN", "USUARIO"] = "USUARIO"
    email: EmailStr | None = None
    data_criacao: datetime | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExtensionTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["extension"] = "extension"
    expires_in: int


class UsuarioEsqueciSenha(BaseModel):
    email: EmailStr


class UsuarioRedefinirSenha(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    nova_senha: str = Field(min_length=8, max_length=120)


class MensagemResponse(BaseModel):
    message: str
