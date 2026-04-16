import math


class Produto:
    """Entidade de produto com cálculo de preço convertido e frete."""

    def __init__(
        self,
        nome: str,
        link_produto: str,
        link_imagem: str | None,
        valor: float,
        peso: int,
        data_atualizacao,
        id_modalidade: int,
        id_vendedor: int | None = None,
        nome_vendedor: str | None = None,
        id_usuario_criador: int | None = None,
        valor_convertido: float | None = None,
        valor_frete: float | None = None,
        id_produto: int | None = None,
    ) -> None:
        """Inicializa os dados do produto.

        Args:
            nome: Nome do produto.
            link_produto: URL de origem do anúncio.
            link_imagem: URL da imagem principal.
            valor: Valor em yuan.
            peso: Peso em gramas.
            data_atualizacao: Data de atualização no banco.
            id_modalidade: Identificador da modalidade logística.
            id_vendedor: Identificador do vendedor relacionado.
            nome_vendedor: Nome do vendedor para leitura agregada.
            id_usuario_criador: Dono do registro.
            valor_convertido: Valor convertido para real.
            valor_frete: Valor de frete calculado.
            id_produto: Identificador do produto.
        """
        self.id_produto = id_produto
        self.nome = nome
        self.link_produto = link_produto
        self.link_imagem = link_imagem
        self.valor = valor  # Valor em yuan.
        self.id_modalidade = id_modalidade
        self.id_vendedor = id_vendedor
        self.nome_vendedor = nome_vendedor
        self.id_usuario_criador = id_usuario_criador
        self.peso = peso
        self.data_atualizacao = data_atualizacao
        self.valor_convertido = valor_convertido
        self.valor_frete = valor_frete if valor_frete is not None else 0.0

    def calcular_valor(self, cotacao: float) -> float:
        """Converte valor do produto para real.

        Args:
            cotacao: Taxa de conversão cambial.

        Returns:
            float: Valor convertido para real.
        """
        if cotacao and cotacao > 0:
            self.valor_convertido = self.valor / cotacao  # Valor em real.
        else:
            self.valor_convertido = 0.0
        return self.valor_convertido

    def calcular_valor_frete(self, frete) -> float:
        """Calcula frete total usando a regra de 100g base + adicional.

        Args:
            frete: Entidade de frete com valores convertidos preenchidos.

        Returns:
            float: Valor total de frete.
        """
        peso_frete2 = self.peso - 100  # Reduz as primeiras 100g já cobradas no base.
        if peso_frete2 > 0:
            self.valor_frete = frete.valor_100g_convertido + (
                frete.valor_100g_plus_convertido * math.ceil(peso_frete2 / 100)
            )
        else:
            self.valor_frete = frete.valor_100g_convertido
        return self.valor_frete
    