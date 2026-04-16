import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.config.banco import conectar
from app.daos.usuarioDAO import UsuarioDAO
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)


def _parse_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    """Lê e valida inteiro de variável de ambiente com limites.

    Args:
        name: Nome da variável de ambiente.
        default: Valor padrão.
        min_value: Menor valor aceito.
        max_value: Maior valor aceito.

    Returns:
        int: Valor validado dentro dos limites.
    """
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default

    return max(min_value, min(max_value, value))


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
if len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY deve estar configurada com ao menos 32 caracteres.")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()
if ALGORITHM not in {"HS256", "HS384", "HS512"}:
    raise RuntimeError("JWT_ALGORITHM invalido. Use HS256, HS384 ou HS512.")

ACCESS_TOKEN_EXPIRE_MINUTES = _parse_int_env(
    name="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    default=120,
    min_value=5,
    max_value=480,
)
EXTENSION_TOKEN_EXPIRE_MINUTES = _parse_int_env(
    name="JWT_EXTENSION_TOKEN_EXPIRE_MINUTES",
    default=120,
    min_value=15,
    max_value=10080,
)
TOKEN_ISSUER = os.getenv("JWT_ISSUER", "citychina-api-49").strip() or "citychina-api-49"
EXTENSION_TOKEN_AUDIENCE = os.getenv("JWT_EXTENSION_AUDIENCE", "citychina-extension").strip() or "citychina-extension"

AUTH_MAX_FAILED_ATTEMPTS = _parse_int_env(
    name="AUTH_MAX_FAILED_ATTEMPTS",
    default=5,
    min_value=3,
    max_value=20,
)
AUTH_ATTEMPT_WINDOW_SECONDS = _parse_int_env(
    name="AUTH_ATTEMPT_WINDOW_SECONDS",
    default=300,
    min_value=30,
    max_value=3600,
)
AUTH_LOCK_SECONDS = _parse_int_env(
    name="AUTH_LOCK_SECONDS",
    default=900,
    min_value=30,
    max_value=86400,
)

_FAILED_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOCKED_LOGIN_UNTIL: dict[str, float] = {}


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(senha: str) -> str:
    """Gera hash seguro da senha.

    Args:
        senha: Senha em texto plano.

    Returns:
        str: Hash criptografado no formato suportado pelo passlib.
    """
    return pwd_context.hash(senha)


def verify_password(senha_plain: str, senha_hash: str) -> bool:
    """Valida senha em texto plano contra hash armazenado.

    Args:
        senha_plain: Senha informada pelo usuário.
        senha_hash: Hash persistido no banco.

    Returns:
        bool: `True` quando a senha é válida.
    """
    return pwd_context.verify(senha_plain, senha_hash)


def create_access_token(
    data: dict[str, Any],
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    token_type: str | None = None,
    audience: str | None = None,
) -> str:
    """Cria token JWT de acesso.

    Args:
        data: Claims que serão serializadas no token.
        expires_minutes: Tempo de expiração em minutos.

    Returns:
        str: JWT assinado.
    """
    resolved_token_type = "access" if token_type is None else token_type
    payload = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload.update(
        {
            "iat": now,
            "nbf": now,
            "exp": expire,
            "iss": TOKEN_ISSUER,
            "type": resolved_token_type,
        }
    )
    if audience:
        payload["aud"] = audience
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_extension_token(
    data: dict[str, Any],
    expires_minutes: int = EXTENSION_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Cria token JWT de uso exclusivo na extensao.

    Args:
        data: Claims que serao serializadas no token.
        expires_minutes: Tempo de expiração em minutos.

    Returns:
        str: JWT assinado para uso na extensao.
    """
    return create_access_token(
        data=data,
        expires_minutes=expires_minutes,
        token_type="extension", # nosec
        audience=EXTENSION_TOKEN_AUDIENCE, # nosec
    )


def _matches_extension_audience(token_aud: Any) -> bool: #nosec
    """Valida se claim de audiencia corresponde ao esperado para extensao."""
    if isinstance(token_aud, str):
        return token_aud == EXTENSION_TOKEN_AUDIENCE

    if isinstance(token_aud, list):
        return EXTENSION_TOKEN_AUDIENCE in token_aud

    return False


def decode_token(token: str) -> dict[str, Any] | None:
    """Decodifica um JWT e retorna o payload.

    Args:
        token: Token JWT.

    Returns:
        dict[str, Any] | None: Payload decodificado ou `None` se inválido.
    """
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            options={
                "verify_aud": False,
                "require": ["exp", "iat", "nbf", "sub", "iss"],
            },
        )
    except InvalidTokenError:
        return None


def _build_login_key(username: str, client_ip: str) -> str:
    """Monta chave canônica para controle de tentativas de login.

    Args:
        username: Nome de usuário informado.
        client_ip: IP de origem da requisição.

    Returns:
        str: Chave para rastreio de tentativas.
    """
    safe_user = username.strip().lower() or "unknown"
    safe_ip = client_ip.strip().lower() or "unknown"
    return f"{safe_user}|{safe_ip}"


def check_login_allowed(username: str, client_ip: str) -> None:
    """Valida se tentativa de login pode continuar.

    Args:
        username: Nome de usuário informado.
        client_ip: IP da requisição.

    Raises:
        HTTPException: Quando usuário/IP está temporariamente bloqueado.
    """
    key = _build_login_key(username, client_ip)
    now = time.time()
    locked_until = _LOCKED_LOGIN_UNTIL.get(key, 0)

    if locked_until > now:
        wait_seconds = max(1, int(locked_until - now))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Tente novamente em {wait_seconds}s.",
        )


def register_failed_login(username: str, client_ip: str) -> None:
    """Registra falha e aplica bloqueio temporário quando necessário.

    Args:
        username: Nome de usuário informado.
        client_ip: IP da requisição.
    """
    key = _build_login_key(username, client_ip)
    now = time.time()
    cutoff = now - AUTH_ATTEMPT_WINDOW_SECONDS

    attempts = [ts for ts in _FAILED_LOGIN_ATTEMPTS.get(key, []) if ts >= cutoff]
    attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[key] = attempts

    if len(attempts) >= AUTH_MAX_FAILED_ATTEMPTS:
        _LOCKED_LOGIN_UNTIL[key] = now + AUTH_LOCK_SECONDS
        _FAILED_LOGIN_ATTEMPTS[key] = []


def clear_login_failures(username: str, client_ip: str) -> None:
    """Limpa histórico de falhas após login bem-sucedido.

    Args:
        username: Nome de usuário informado.
        client_ip: IP da requisição.
    """
    key = _build_login_key(username, client_ip)
    _FAILED_LOGIN_ATTEMPTS.pop(key, None)
    _LOCKED_LOGIN_UNTIL.pop(key, None)


def _get_user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    allowed_token_types: set[str],
) -> Usuario:
    """Resolve usuário autenticado a partir do token Bearer com tipos permitidos.

    Args:
        credentials: Credenciais HTTP extraídas automaticamente pelo FastAPI.
        allowed_token_types: Tipos de token permitidos para o endpoint.

    Raises:
        HTTPException: Quando token é ausente, inválido ou usuário não existe.

    Returns:
        Usuario: Usuário autenticado.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido ou ausente",
        )

    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido",
        )

    token_type = payload.get("type")
    if token_type not in allowed_token_types:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido",
        )

    if token_type == "extension" and not _matches_extension_audience(payload.get("aud")): # nosec
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido",
        )

    token_version_claim = payload.get("tv")
    if token_version_claim is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido",
        )

    try:
        user_id = int(payload["sub"])
        token_version = int(token_version_claim)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso invalido",
        )

    conexao = conectar()
    if conexao is None:
        logger.error("Falha ao obter conexao durante autenticacao")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha interna do servidor",
        )

    try:
        dao = UsuarioDAO(conexao)
        usuario = dao.ReadById(user_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario nao encontrado",
            )
        if usuario.token_version != token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de acesso invalido",
            )
        return usuario
    finally:
        conexao.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Usuario:
    """Recupera usuário autenticado aceitando token de acesso ou extensão."""
    return _get_user_from_credentials(credentials, {"access", "extension"})


def get_current_access_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Usuario:
    """Recupera usuário autenticado exigindo token do tipo access."""
    return _get_user_from_credentials(credentials, {"access"})


def require_admin(usuario: Usuario = Depends(get_current_access_user)) -> Usuario:
    """Garante acesso apenas para usuários com perfil ADMIN.

    Args:
        usuario: Usuário autenticado.

    Raises:
        HTTPException: Quando o perfil não é ADMIN.

    Returns:
        Usuario: Usuário autenticado com perfil ADMIN.
    """
    if usuario.perfil != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a usuarios com permissão ADMIN",
        )
    return usuario


def require_same_user_or_admin(
    id_usuario: int,
    usuario: Usuario = Depends(get_current_access_user),
) -> Usuario:
    """Permite operação no próprio recurso ou para ADMIN.

    Args:
        id_usuario: Identificador do recurso alvo.
        usuario: Usuário autenticado.

    Raises:
        HTTPException: Quando o usuário não possui permissão.

    Returns:
        Usuario: Usuário autenticado autorizado.
    """
    if usuario.perfil == "ADMIN" or usuario.id_usuario == id_usuario:
        return usuario

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissao para operar neste usuario",
    )


def require_roles(*roles: str) -> Callable[[Usuario], Usuario]:
    """Cria dependência para validar perfis permitidos.

    Args:
        *roles: Perfis autorizados para o endpoint.

    Returns:
        Callable[[Usuario], Usuario]: Dependência de autorização.
    """
    allowed_roles = set(roles)

    def _checker(usuario: Usuario = Depends(get_current_access_user)) -> Usuario:
        """Valida se o perfil do usuário está autorizado.

        Args:
            usuario: Usuário autenticado.

        Raises:
            HTTPException: Quando perfil não autorizado.

        Returns:
            Usuario: Usuário autorizado.
        """
        if usuario.perfil not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissao para esta operacao",
            )
        return usuario

    return _checker
