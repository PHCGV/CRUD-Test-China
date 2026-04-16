class Usuario:
    """Entidade de usuário autenticável da aplicação."""

    def __init__(
        self,
        nome: str,
        username: str,
        senha_hash: str,
        email: str | None = None,
        perfil: str = "USUARIO",
        token_version: int = 1,
        data_criacao=None,
        id_usuario: int | None = None,
    ) -> None:
        """Inicializa dados do usuário.

        Args:
            nome: Nome completo.
            username: Nome de usuário único.
            senha_hash: Hash da senha.
            perfil: Perfil de autorização.
            data_criacao: Data de criação no banco.
            id_usuario: Identificador do usuário.
        """
        self.id_usuario = id_usuario
        self.nome = nome
        self.username = username
        self.senha_hash = senha_hash
        self.email = email
        self.perfil = perfil
        self.token_version = token_version
        self.data_criacao = data_criacao
