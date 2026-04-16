import oracledb

from app.models.usuario import Usuario


class UsuarioDAO:
    """Camada de acesso a dados para usuários."""

    def __init__(self, conexao: oracledb.Connection) -> None:
        """Inicializa DAO com conexão Oracle.

        Args:
            conexao: Conexão Oracle ativa.
        """
        self.conexao = conexao
        self.cursor = conexao.cursor()

    @staticmethod
    def _to_usuario(linha: tuple) -> Usuario:
        """Mapeia linha SQL para entidade Usuario."""
        token_version = int(linha[7]) if linha[7] is not None else 1
        return Usuario(
            id_usuario=linha[0],
            nome=linha[1],
            username=linha[2],
            senha_hash=linha[3],
            perfil=linha[4],
            data_criacao=linha[5],
            email=linha[6],
            token_version=token_version,
        )

    def Create(self, usuario: Usuario) -> int:
        """Insere um usuário no banco.

        Args:
            usuario: Entidade de usuário.

        Returns:
            int: ID do usuário criado.

        Raises:
            Exception: Repropaga falha após rollback.
        """
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = (
                "INSERT INTO TB_USUARIOS "
                "(NOME_USUARIO, USERNAME_USUARIO, SENHA_HASH, PERFIL_USUARIO, EMAIL_USUARIO, TOKEN_VERSION) "
                "VALUES (:1, :2, :3, :4, :5, 1) RETURNING ID_USUARIO INTO :6"
            )
            self.cursor.execute(
                sql,
                [
                    usuario.nome,
                    usuario.username,
                    usuario.senha_hash,
                    usuario.perfil,
                    usuario.email,
                    id_novo,
                ],
            )
            self.conexao.commit()
            return int(id_novo.getvalue()[0])
        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def ReadAll(self) -> list[Usuario]:
        """Lista todos os usuários.

        Returns:
            list[Usuario]: Coleção de usuários.
        """
        sql = (
            "SELECT ID_USUARIO, NOME_USUARIO, USERNAME_USUARIO, SENHA_HASH, PERFIL_USUARIO, "
            "DATA_CRIACAO, EMAIL_USUARIO, TOKEN_VERSION "
            "FROM TB_USUARIOS"
        )
        self.cursor.execute(sql)

        usuarios: list[Usuario] = []
        for linha in self.cursor:
            usuarios.append(self._to_usuario(linha))
        return usuarios

    def ReadById(self, id_usuario: int) -> Usuario | None:
        """Busca usuário por ID.

        Args:
            id_usuario: Identificador do usuário.

        Returns:
            Usuario | None: Usuário encontrado ou `None`.
        """
        sql = (
            "SELECT ID_USUARIO, NOME_USUARIO, USERNAME_USUARIO, SENHA_HASH, PERFIL_USUARIO, "
            "DATA_CRIACAO, EMAIL_USUARIO, TOKEN_VERSION "
            "FROM TB_USUARIOS WHERE ID_USUARIO = :1"
        )
        self.cursor.execute(sql, [id_usuario])
        linha = self.cursor.fetchone()
        if not linha:
            return None

        return self._to_usuario(linha)

    def ReadByUsername(self, username: str) -> Usuario | None:
        """Busca usuário por username.

        Args:
            username: Nome de usuário.

        Returns:
            Usuario | None: Usuário encontrado ou `None`.
        """
        sql = (
            "SELECT ID_USUARIO, NOME_USUARIO, USERNAME_USUARIO, SENHA_HASH, PERFIL_USUARIO, "
            "DATA_CRIACAO, EMAIL_USUARIO, TOKEN_VERSION "
            "FROM TB_USUARIOS WHERE LOWER(USERNAME_USUARIO) = LOWER(:1)"
        )
        self.cursor.execute(sql, [username])
        linha = self.cursor.fetchone()
        if not linha:
            return None

        return self._to_usuario(linha)

    def ReadByEmail(self, email: str) -> Usuario | None:
        """Busca usuário por e-mail."""
        sql = (
            "SELECT ID_USUARIO, NOME_USUARIO, USERNAME_USUARIO, SENHA_HASH, PERFIL_USUARIO, "
            "DATA_CRIACAO, EMAIL_USUARIO, TOKEN_VERSION "
            "FROM TB_USUARIOS WHERE LOWER(EMAIL_USUARIO) = LOWER(:1)"
        )
        self.cursor.execute(sql, [email])
        linha = self.cursor.fetchone()
        if not linha:
            return None

        return self._to_usuario(linha)

    def Update(self, id_usuario: int, nome: str, username: str, email: str | None) -> None:
        """Atualiza dados básicos do usuário.

        Args:
            id_usuario: ID do usuário.
            nome: Novo nome.
            username: Novo username.
        """
        sql = (
            "UPDATE TB_USUARIOS SET NOME_USUARIO = :1, USERNAME_USUARIO = :2, EMAIL_USUARIO = :3 "
            "WHERE ID_USUARIO = :4"
        )
        self.cursor.execute(sql, [nome, username, email, id_usuario])
        self.conexao.commit()

    def UpdateAdmin(
        self,
        id_usuario: int,
        nome: str,
        username: str,
        email: str | None,
        perfil: str,
    ) -> None:
        """Atualiza campos administrativos do usuário.

        Args:
            id_usuario: ID do usuário.
            nome: Nome atualizado.
            username: Username atualizado.
            perfil: Perfil do usuário.
        """
        sql = (
            "UPDATE TB_USUARIOS SET NOME_USUARIO = :1, USERNAME_USUARIO = :2, "
            "EMAIL_USUARIO = :3, PERFIL_USUARIO = :4 WHERE ID_USUARIO = :5"
        )
        self.cursor.execute(sql, [nome, username, email, perfil, id_usuario])
        self.conexao.commit()

    def UpdatePassword(self, id_usuario: int, senha_hash: str, increment_token_version: bool = True) -> None:
        """Atualiza hash de senha do usuário.

        Args:
            id_usuario: ID do usuário.
            senha_hash: Novo hash da senha.
        """
        sql = "UPDATE TB_USUARIOS SET SENHA_HASH = :1, TOKEN_VERSION = TOKEN_VERSION + :2 WHERE ID_USUARIO = :3"
        incremento = 1 if increment_token_version else 0
        self.cursor.execute(sql, [senha_hash, incremento, id_usuario])
        self.conexao.commit()

    def ReplacePasswordResetToken(
        self,
        id_usuario: int,
        token_hash: str,
        expira_em,
        ip_solicitacao: str,
        user_agent_solicitacao: str,
    ) -> int:
        """Invalida tokens antigos e cria novo token de reset para o usuário."""
        try:
            self.cursor.execute(
                "UPDATE TB_PASSWORD_RESET SET USADO_EM = SYSDATE "
                "WHERE ID_USUARIO = :1 AND USADO_EM IS NULL",
                [id_usuario],
            )

            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = (
                "INSERT INTO TB_PASSWORD_RESET "
                "(ID_USUARIO, TOKEN_HASH, EXPIRA_EM, IP_SOLICITACAO, USER_AGENT_SOLICITACAO) "
                "VALUES (:1, :2, :3, :4, :5) RETURNING ID_RESET INTO :6"
            )
            self.cursor.execute(
                sql,
                [
                    id_usuario,
                    token_hash,
                    expira_em,
                    ip_solicitacao,
                    user_agent_solicitacao,
                    id_novo,
                ],
            )
            self.conexao.commit()
            return int(id_novo.getvalue()[0])
        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def GetValidPasswordReset(self, token_hash: str) -> tuple[int, Usuario] | None:
        """Retorna token de reset válido e usuário associado."""
        sql = (
            "SELECT R.ID_RESET, U.ID_USUARIO, U.NOME_USUARIO, U.USERNAME_USUARIO, U.SENHA_HASH, "
            "U.PERFIL_USUARIO, U.DATA_CRIACAO, U.EMAIL_USUARIO, U.TOKEN_VERSION "
            "FROM TB_PASSWORD_RESET R "
            "JOIN TB_USUARIOS U ON U.ID_USUARIO = R.ID_USUARIO "
            "WHERE R.TOKEN_HASH = :1 AND R.USADO_EM IS NULL AND R.EXPIRA_EM > SYSDATE"
        )
        self.cursor.execute(sql, [token_hash])
        linha = self.cursor.fetchone()
        if not linha:
            return None

        reset_id = int(linha[0])
        usuario = self._to_usuario((linha[1], linha[2], linha[3], linha[4], linha[5], linha[6], linha[7], linha[8]))
        return (reset_id, usuario)

    def ConsumePasswordReset(
        self,
        reset_id: int,
        id_usuario: int,
        senha_hash: str,
        ip_uso: str,
        user_agent_uso: str,
    ) -> bool:
        """Consome token de reset, atualiza senha e invalida tokens remanescentes."""
        try:
            self.cursor.execute(
                "UPDATE TB_PASSWORD_RESET SET USADO_EM = SYSDATE, IP_USO = :1, USER_AGENT_USO = :2 "
                "WHERE ID_RESET = :3 AND USADO_EM IS NULL AND EXPIRA_EM > SYSDATE",
                [ip_uso, user_agent_uso, reset_id],
            )
            if self.cursor.rowcount != 1:
                self.conexao.rollback()
                return False

            self.cursor.execute(
                "UPDATE TB_USUARIOS SET SENHA_HASH = :1, TOKEN_VERSION = TOKEN_VERSION + 1 "
                "WHERE ID_USUARIO = :2",
                [senha_hash, id_usuario],
            )

            self.cursor.execute(
                "UPDATE TB_PASSWORD_RESET SET USADO_EM = NVL(USADO_EM, SYSDATE) "
                "WHERE ID_USUARIO = :1 AND ID_RESET <> :2 AND USADO_EM IS NULL",
                [id_usuario, reset_id],
            )

            self.conexao.commit()
            return True
        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def DeleteExpiredPasswordResets(self) -> None:
        """Remove tokens expirados e usados há mais de 30 dias."""
        sql = (
            "DELETE FROM TB_PASSWORD_RESET "
            "WHERE EXPIRA_EM <= SYSDATE OR (USADO_EM IS NOT NULL AND USADO_EM <= (SYSDATE - 30))"
        )
        self.cursor.execute(sql)
        self.conexao.commit()

    def Delete(self, id_usuario: int) -> None:
        """Remove usuário pelo ID.

        Args:
            id_usuario: ID do usuário.
        """
        self.cursor.execute("DELETE FROM TB_PASSWORD_RESET WHERE ID_USUARIO = :1", [id_usuario])
        sql = "DELETE FROM TB_USUARIOS WHERE ID_USUARIO = :1"
        self.cursor.execute(sql, [id_usuario])
        self.conexao.commit()
