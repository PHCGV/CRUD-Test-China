class Frete:
    """Entidade de frete com regras básicas de conversão monetária."""

    def __init__(
        self,
        nome: str,
        servico: str | None,
        valor_100g: float,
        valor_100g_plus: float,
        id_frete: int | None = None,
        valor_100g_convertido: float | None = None,
        valor_100g_plus_convertido: float | None = None,
        modalidades: list[str] | None = None,
    ) -> None:
        """Inicializa os dados da entidade de frete.

        Args:
            nome: Nome do método de envio.
            servico: Nome do serviço/provedor logístico.
            valor_100g: Valor base para as primeiras 100g.
            valor_100g_plus: Valor adicional por cada 100g extras.
            id_frete: Identificador do frete no banco.
            valor_100g_convertido: Valor convertido para moeda local.
            valor_100g_plus_convertido: Valor adicional convertido.
            modalidades: Modalidades associadas ao frete.
        """
        self.id_frete = id_frete
        self.nome = nome
        self.servico = (servico or "Nao informado").strip() or "Nao informado"
        self.valor_100g = valor_100g
        self.valor_100g_plus = valor_100g_plus
        self.valor_100g_convertido = valor_100g_convertido
        self.valor_100g_plus_convertido = valor_100g_plus_convertido
        self.modalidades = modalidades or []

    def calcular_valor_convertido(self, cotacao: float) -> tuple[float, float]:
        """Converte valores de frete pela cotação informada.

        Args:
            cotacao: Taxa de conversão cambial.

        Returns:
            tuple[float, float]: Valores convertidos base e adicional.
        """
        self.valor_100g_convertido = self.valor_100g / cotacao
        self.valor_100g_plus_convertido = self.valor_100g_plus / cotacao
        return self.valor_100g_convertido, self.valor_100g_plus_convertido
    