class Vendedor:
    """Entidade de vendedor vinculada a um usuário criador."""

    def __init__(
        self,
        nome: str,
        loja: str,
        link_loja: str | None = None,
        id_usuario_criador: int | None = None,
        id_vendedor: int | None = None,
    ) -> None:
        """Inicializa os dados de vendedor.

        Args:
            nome: Nome do vendedor.
            loja: Nome da loja.
            link_loja: URL da loja.
            id_usuario_criador: Dono do registro.
            id_vendedor: Identificador do vendedor.
        """
        self.id_vendedor = id_vendedor
        self.nome = nome
        self.loja = loja
        self.link_loja = link_loja
        self.id_usuario_criador = id_usuario_criador
