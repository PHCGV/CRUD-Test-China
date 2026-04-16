import logging
import hashlib
import os
import secrets
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.config.banco import conectar
from app.config.security import (
    EXTENSION_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_extension_token,
    check_login_allowed,
    clear_login_failures,
    get_current_access_user,
    get_current_user,
    hash_password,
    register_failed_login,
    require_admin,
    require_same_user_or_admin,
    verify_password,
)

from app.daos.usuarioDAO import UsuarioDAO
from app.models.usuario import Usuario
from app.schemas.usuario_schema import (
    ExtensionTokenResponse,
    MensagemResponse,
    TokenResponse,
    UsuarioAdminUpdate,
    UsuarioCreate,
    UsuarioEsqueciSenha,
    UsuarioLogin,
    UsuarioRedefinirSenha,
    UsuarioResponse,
    UsuarioTrocaSenha,
    UsuarioUpdate,
)

router = APIRouter(prefix="/auth", tags=["Autenticacao"])
logger = logging.getLogger(__name__)
INTERNAL_ERROR_DETAIL = "Falha interna do servidor"
RESET_GENERIC_MESSAGE = "Caso haja um email cadastrado será enviado instrucoes de recuperacao"


def _parse_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(min_value, min(max_value, value))


RESET_TOKEN_EXPIRE_MINUTES = _parse_int_env(
    name="AUTH_RESET_TOKEN_EXPIRE_MINUTES",
    default=20,
    min_value=5,
    max_value=180,
)
RESET_REQUEST_WINDOW_SECONDS = _parse_int_env(
    name="AUTH_RESET_REQUEST_WINDOW_SECONDS",
    default=900,
    min_value=60,
    max_value=3600,
)
RESET_REQUEST_MAX_ATTEMPTS = _parse_int_env(
    name="AUTH_RESET_REQUEST_MAX_ATTEMPTS",
    default=3,
    min_value=1,
    max_value=20,
)

RESET_TOKEN_PEPPER = (
    os.getenv("AUTH_RESET_TOKEN_PEPPER", "").strip()
    or os.getenv("JWT_SECRET_KEY", "").strip()
)
APP_PUBLIC_URL = os.getenv("APP_PUBLIC_URL", "https://phcgv-import.vercel.app").strip() or "https://phcgv-import.vercel.app"

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = _parse_int_env("SMTP_PORT", 587, 1, 65535)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"

_RESET_REQUEST_ATTEMPTS: dict[str, list[float]] = {}


def _build_reset_key(email: str, client_ip: str) -> str:
    safe_email = email.strip().lower() or "unknown"
    safe_ip = client_ip.strip().lower() or "unknown"
    return f"{safe_email}|{safe_ip}"


def _check_reset_allowed(email: str, client_ip: str) -> None:
    key = _build_reset_key(email, client_ip)
    now = time.time()
    cutoff = now - RESET_REQUEST_WINDOW_SECONDS
    attempts = [ts for ts in _RESET_REQUEST_ATTEMPTS.get(key, []) if ts >= cutoff]
    _RESET_REQUEST_ATTEMPTS[key] = attempts
    if len(attempts) >= RESET_REQUEST_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas solicitacoes de reset. Aguarde alguns minutos e tente novamente.",
        )


def _register_reset_attempt(email: str, client_ip: str) -> None:
    key = _build_reset_key(email, client_ip)
    now = time.time()
    cutoff = now - RESET_REQUEST_WINDOW_SECONDS
    attempts = [ts for ts in _RESET_REQUEST_ATTEMPTS.get(key, []) if ts >= cutoff]
    attempts.append(now)
    _RESET_REQUEST_ATTEMPTS[key] = attempts


def _hash_reset_token(raw_token: str) -> str:
    material = f"{raw_token}:{RESET_TOKEN_PEPPER}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _send_password_reset_email(nome: str, email_destino: str, token: str) -> None:
    reset_link = f"{APP_PUBLIC_URL.rstrip('/')}/reset-password?token={token}"

    if not SMTP_HOST or not SMTP_FROM:
        logger.warning("SMTP nao configurado. E-mail de reset nao enviado para %s.", email_destino)
        return

    assunto = "Recuperacao de senha"
    corpo = (
        f"Olá, {nome}.\n\n"
        "Recebemos uma solicitação para redefinir sua senha.\n"
        f"Use este link (válido por {RESET_TOKEN_EXPIRE_MINUTES} minutos):\n{reset_link}\n\n"
        "Se você não solicitou, ignore essa mensagem\n"
    )

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = SMTP_FROM
    msg["To"] = email_destino
    msg.set_content(corpo)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)


@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: UsuarioCreate) -> UsuarioResponse:
    """Registra usuário comum no sistema.

    Args:
        usuario: Dados de registro.

    Returns:
        UsuarioResponse: Usuário criado.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        if dao.ReadByUsername(usuario.username):
            raise HTTPException(status_code=400, detail="Username ja cadastrado")
        if usuario.email and dao.ReadByEmail(str(usuario.email)):
            raise HTTPException(status_code=400, detail="Email ja cadastrado")

        novo = Usuario(
            nome=usuario.nome,
            username=usuario.username,
            senha_hash=hash_password(usuario.senha),
            email=str(usuario.email) if usuario.email else None,
            perfil="USUARIO",
        )

        try:
            id_criado = dao.Create(novo)
            criado = dao.ReadById(id_criado)
            if criado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar usuario criado")
            return criado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao registrar usuario")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.post("/login", response_model=TokenResponse)
def login_usuario(dados: UsuarioLogin, request: Request) -> TokenResponse:
    """Autentica usuário e retorna token JWT.

    Args:
        dados: Credenciais de login.

    Returns:
        TokenResponse: Token de acesso.
    """
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    client_ip = request.client.host if request.client else "unknown"
    check_login_allowed(dados.username, client_ip)

    try:
        dao = UsuarioDAO(conexao)

        usuario = dao.ReadByUsername(dados.username)
        if not usuario or not verify_password(dados.senha, usuario.senha_hash):
            register_failed_login(dados.username, client_ip)
            raise HTTPException(status_code=401, detail="Credenciais invalidas")

        clear_login_failures(dados.username, client_ip)

        token = create_access_token(
            {
                "sub": str(usuario.id_usuario),
                "username": usuario.username,
                "perfil": usuario.perfil,
                "tv": usuario.token_version,
            }
        )
        return TokenResponse(access_token=token)
    finally:
        conexao.close()


@router.post("/extension-token", response_model=ExtensionTokenResponse)
def login_extensao(usuario_atual: Usuario = Depends(get_current_access_user)) -> ExtensionTokenResponse:
    """Gera token dedicado para sincronizacao de sessao com a extensao."""
    token = create_extension_token(
        {
            "sub": str(usuario_atual.id_usuario),
            "username": usuario_atual.username,
            "perfil": usuario_atual.perfil,
            "tv": usuario_atual.token_version,
            "source": "main-app",
        }
    )

    return ExtensionTokenResponse(
        access_token=token,
        expires_in=EXTENSION_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UsuarioResponse)
def me(usuario_atual: Usuario = Depends(get_current_user)) -> UsuarioResponse:
    """Retorna dados do usuário autenticado."""
    return usuario_atual


@router.put("/trocar-senha", status_code=status.HTTP_204_NO_CONTENT)
def trocar_senha(
    dados: UsuarioTrocaSenha,
    usuario_atual: Usuario = Depends(get_current_access_user),
) -> None:
    """Altera senha do usuário autenticado."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        if not verify_password(dados.senha_atual, usuario_atual.senha_hash):
            raise HTTPException(status_code=400, detail="Senha atual invalida")

        if dados.senha_atual == dados.nova_senha:
            raise HTTPException(status_code=400, detail="A nova senha deve ser diferente da senha atual")

        try:
            dao.UpdatePassword(usuario_atual.id_usuario, hash_password(dados.nova_senha))
        except Exception:
            logger.exception("Erro ao trocar senha")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.post(
    "/esqueci-senha",
    response_model=MensagemResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def esqueci_senha(dados: UsuarioEsqueciSenha, request: Request) -> MensagemResponse:
    """Solicita reset de senha por e-mail com resposta genérica anti-enumeração."""
    client_ip = request.client.host if request.client else "unknown"
    _check_reset_allowed(str(dados.email), client_ip)
    _register_reset_attempt(str(dados.email), client_ip)

    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        try:
            dao.DeleteExpiredPasswordResets()
            usuario = dao.ReadByEmail(str(dados.email))
            if not usuario:
                return MensagemResponse(message=RESET_GENERIC_MESSAGE)

            token = secrets.token_urlsafe(48)
            token_hash = _hash_reset_token(token)
            expira_em = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
            user_agent = (request.headers.get("user-agent") or "unknown")[:400]

            dao.ReplacePasswordResetToken(
                id_usuario=usuario.id_usuario,
                token_hash=token_hash,
                expira_em=expira_em,
                ip_solicitacao=client_ip[:45],
                user_agent_solicitacao=user_agent,
            )

            _send_password_reset_email(usuario.nome, str(dados.email), token)
            return MensagemResponse(message=RESET_GENERIC_MESSAGE)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao processar solicitacao de reset de senha")
            return MensagemResponse(message=RESET_GENERIC_MESSAGE)
    finally:
        conexao.close()


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(dados: UsuarioRedefinirSenha, request: Request) -> None:
    """Consome token de reset e redefine senha com uso único."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)
        token_hash = _hash_reset_token(dados.token)

        try:
            dao.DeleteExpiredPasswordResets()
            reset_info = dao.GetValidPasswordReset(token_hash)
            if not reset_info:
                raise HTTPException(status_code=400, detail="Token invalido ou expirado")

            reset_id, usuario = reset_info

            if verify_password(dados.nova_senha, usuario.senha_hash):
                raise HTTPException(status_code=400, detail="A nova senha deve ser diferente da senha atual")

            client_ip = (request.client.host if request.client else "unknown")[:45]
            user_agent = (request.headers.get("user-agent") or "unknown")[:400]
            sucesso = dao.ConsumePasswordReset(
                reset_id=reset_id,
                id_usuario=usuario.id_usuario,
                senha_hash=hash_password(dados.nova_senha),
                ip_uso=client_ip,
                user_agent_uso=user_agent,
            )
            if not sucesso:
                raise HTTPException(status_code=400, detail="Token invalido ou expirado")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao redefinir senha")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(usuario_admin: Usuario = Depends(require_admin)) -> list[UsuarioResponse]:
    """Lista todos os usuários (apenas ADMIN)."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)
        return dao.ReadAll()
    finally:
        conexao.close()


@router.post("/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario_admin(
    dados: UsuarioCreate,
    usuario_admin: Usuario = Depends(require_admin),
) -> UsuarioResponse:
    """Cria usuário com perfil definido por ADMIN."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        if dao.ReadByUsername(dados.username):
            raise HTTPException(status_code=400, detail="Username ja cadastrado")
        if dados.email and dao.ReadByEmail(str(dados.email)):
            raise HTTPException(status_code=400, detail="Email ja cadastrado")

        novo = Usuario(
            nome=dados.nome,
            username=dados.username,
            senha_hash=hash_password(dados.senha),
            email=str(dados.email) if dados.email else None,
            perfil=dados.perfil,
        )

        try:
            id_criado = dao.Create(novo)
            criado = dao.ReadById(id_criado)
            if criado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar usuario criado")
            return criado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao criar usuario via admin")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.get("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def obter_usuario(
    id_usuario: int,
    usuario_atual: Usuario = Depends(get_current_access_user),
) -> UsuarioResponse:
    """Obtém usuário por ID respeitando regra de autorização."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        alvo = dao.ReadById(id_usuario)
        if not alvo:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        if usuario_atual.perfil != "ADMIN" and usuario_atual.id_usuario != id_usuario:
            raise HTTPException(status_code=403, detail="Sem permissao para visualizar este usuario")

        return alvo
    finally:
        conexao.close()


@router.put("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def atualizar_usuario(
    id_usuario: int,
    dados: UsuarioUpdate,
    usuario_atual: Usuario = Depends(require_same_user_or_admin),
) -> UsuarioResponse:
    """Atualiza dados básicos do usuário (próprio usuário ou ADMIN)."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        alvo = dao.ReadById(id_usuario)
        if not alvo:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        novo_nome = dados.nome if dados.nome is not None else alvo.nome
        novo_username = dados.username if dados.username is not None else alvo.username
        novo_email = str(dados.email) if dados.email is not None else alvo.email

        existente_user = dao.ReadByUsername(novo_username)
        if existente_user and existente_user.id_usuario != id_usuario:
            raise HTTPException(status_code=400, detail="Username ja cadastrado")
        if novo_email:
            existente_email = dao.ReadByEmail(novo_email)
            if existente_email and existente_email.id_usuario != id_usuario:
                raise HTTPException(status_code=400, detail="Email ja cadastrado")

        try:
            dao.Update(id_usuario, novo_nome, novo_username, novo_email)
            atualizado = dao.ReadById(id_usuario)
            if atualizado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar usuario atualizado")
            return atualizado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao atualizar usuario")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.put("/usuarios/{id_usuario}/admin", response_model=UsuarioResponse)
def atualizar_usuario_admin(
    id_usuario: int,
    dados: UsuarioAdminUpdate,
    usuario_admin: Usuario = Depends(require_admin),
) -> UsuarioResponse:
    """Atualiza dados administrativos de usuário (apenas ADMIN)."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        alvo = dao.ReadById(id_usuario)
        if not alvo:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        novo_nome = dados.nome if dados.nome is not None else alvo.nome
        novo_username = dados.username if dados.username is not None else alvo.username
        novo_email = str(dados.email) if dados.email is not None else alvo.email
        novo_perfil = dados.perfil if dados.perfil is not None else alvo.perfil

        existente_user = dao.ReadByUsername(novo_username)
        if existente_user and existente_user.id_usuario != id_usuario:
            raise HTTPException(status_code=400, detail="Username ja cadastrado")
        if novo_email:
            existente_email = dao.ReadByEmail(novo_email)
            if existente_email and existente_email.id_usuario != id_usuario:
                raise HTTPException(status_code=400, detail="Email ja cadastrado")

        try:
            dao.UpdateAdmin(id_usuario, novo_nome, novo_username, novo_email, novo_perfil)
            atualizado = dao.ReadById(id_usuario)
            if atualizado is None:
                raise HTTPException(status_code=500, detail="Falha ao recuperar usuario atualizado")
            return atualizado
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erro ao atualizar usuario por admin")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()


@router.delete("/usuarios/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(
    id_usuario: int,
    usuario_atual: Usuario = Depends(require_same_user_or_admin),
) -> None:
    """Remove um usuário (próprio usuário ou ADMIN)."""
    conexao = conectar()
    if conexao is None:
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)

    try:
        dao = UsuarioDAO(conexao)

        alvo = dao.ReadById(id_usuario)
        if not alvo:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        if alvo.perfil == "ADMIN":
            usuarios = dao.ReadAll()
            admins = [u for u in usuarios if u.perfil == "ADMIN" and u.id_usuario != id_usuario]
            if not admins:
                raise HTTPException(status_code=400, detail="Nao e permitido remover o ultimo admin")

        try:
            dao.Delete(id_usuario)
        except Exception:
            logger.exception("Erro ao deletar usuario")
            raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL)
    finally:
        conexao.close()
