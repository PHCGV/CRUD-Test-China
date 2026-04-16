import os
import logging

import oracledb
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def conectar() -> oracledb.Connection | None:
    """Abre uma conexão Oracle usando variáveis de ambiente.

    Returns:
        oracledb.Connection | None: Conexão válida quando o acesso é
        bem-sucedido; `None` quando ocorre falha.
    """
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")

    if not user or not password or not dsn:
        logger.error("Erro nas variaveis")
        return None

    try:
        return oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.DatabaseError:
        logger.exception("Falha ao conectar ao banco de dados")
        return None