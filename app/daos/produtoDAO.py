import oracledb
from app.models.produto import Produto

class ProdutoDAO:
    """Camada de acesso a dados para produtos."""

    def __init__(self, conexao: oracledb.Connection) -> None:
        """Inicializa DAO com conexão Oracle.

        Args:
            conexao: Conexão Oracle ativa.
        """
        self.conexao = conexao
        self.cursor = conexao.cursor()

    def Create(self, produto: Produto) -> int:
        """Cria um produto no banco.

        Args:
            produto: Entidade de produto.

        Returns:
            int: ID do produto criado.

        Raises:
            Exception: Repropaga falha após rollback.
        """
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = "INSERT INTO TB_PRODUTOS (NOME_PRODUTO, LINK_PRODUTO, LINK_IMAGEM, VALOR, PESO_GRAMAS, DATA_ATUALIZACAO, ID_MODALIDADE, ID_VENDEDOR, ID_USUARIO_CRIADOR) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9) RETURNING ID_PRODUTO INTO :10"

            dados = [
                produto.nome,
                produto.link_produto,
                produto.link_imagem,
                produto.valor,
                produto.peso,
                produto.data_atualizacao,
                produto.id_modalidade,
                produto.id_vendedor,
                produto.id_usuario_criador,
                id_novo,
            ]
            self.cursor.execute(sql, dados)
            self.conexao.commit()
            return int(id_novo.getvalue()[0])
        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def ReadAll(self, id_usuario_criador: int) -> list[Produto]:
        """Lista produtos de um usuário criador.

        Args:
            id_usuario_criador: ID do usuário dono dos produtos.

        Returns:
            list[Produto]: Produtos pertencentes ao usuário.
        """
        sql = (
            "SELECT P.ID_PRODUTO, P.NOME_PRODUTO, P.LINK_PRODUTO, P.LINK_IMAGEM, P.VALOR, "
            "P.PESO_GRAMAS, P.DATA_ATUALIZACAO, P.ID_MODALIDADE, P.ID_VENDEDOR, V.NOME_VENDEDOR, P.ID_USUARIO_CRIADOR "
            "FROM TB_PRODUTOS P "
            "LEFT JOIN TB_VENDEDORES V ON V.ID_VENDEDOR = P.ID_VENDEDOR "
            "WHERE P.ID_USUARIO_CRIADOR = :1"
        )
        self.cursor.execute(sql, [id_usuario_criador])
        lista_produtos: list[Produto] = []
        for linha in self.cursor:
            produto = Produto(
                id_produto=linha[0],
                nome=linha[1],
                link_produto=linha[2],
                link_imagem=linha[3],
                valor=linha[4],
                peso=linha[5],
                data_atualizacao=linha[6],
                id_modalidade=linha[7],
                id_vendedor=linha[8],
                nome_vendedor=linha[9],
                id_usuario_criador=linha[10],
            )
            lista_produtos.append(produto)
        return lista_produtos

    def Read(self, id_produto: int, id_usuario_criador: int) -> Produto | None:
        """Busca um produto por ID, respeitando dono do registro.

        Args:
            id_produto: ID do produto.
            id_usuario_criador: ID do usuário dono.

        Returns:
            Produto | None: Produto encontrado ou `None`.
        """
        sql = (
            "SELECT P.ID_PRODUTO, P.NOME_PRODUTO, P.LINK_PRODUTO, P.LINK_IMAGEM, P.VALOR, "
            "P.PESO_GRAMAS, P.DATA_ATUALIZACAO, P.ID_MODALIDADE, P.ID_VENDEDOR, V.NOME_VENDEDOR, P.ID_USUARIO_CRIADOR "
            "FROM TB_PRODUTOS P "
            "LEFT JOIN TB_VENDEDORES V ON V.ID_VENDEDOR = P.ID_VENDEDOR "
            "WHERE P.ID_PRODUTO = :1 AND P.ID_USUARIO_CRIADOR = :2"
        )
        self.cursor.execute(sql, [id_produto, id_usuario_criador])
        linha = self.cursor.fetchone()
        if linha:
            produto = Produto(
                id_produto=linha[0],
                nome=linha[1],
                link_produto=linha[2],
                link_imagem=linha[3],
                valor=linha[4],
                peso=linha[5],
                data_atualizacao=linha[6],
                id_modalidade=linha[7],
                id_vendedor=linha[8],
                nome_vendedor=linha[9],
                id_usuario_criador=linha[10],
            )
            return produto
        return None

    def UpdateDate(self, id_produto: int) -> None:
        """Atualiza data de modificação do produto.

        Args:
            id_produto: ID do produto.
        """
        sql = "UPDATE TB_PRODUTOS SET DATA_ATUALIZACAO = SYSDATE WHERE ID_PRODUTO = :1"
        self.cursor.execute(sql, [id_produto])
        self.conexao.commit()

    def UpdateValue(self, id_produto: int, valor: float) -> None:
        """Atualiza valor base do produto.

        Args:
            id_produto: ID do produto.
            valor: Novo valor em yuan.
        """
        sql = "UPDATE TB_PRODUTOS SET VALOR = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [valor, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def UpdateWeight(self, id_produto: int, peso: int) -> None:
        """Atualiza peso do produto.

        Args:
            id_produto: ID do produto.
            peso: Novo peso em gramas.
        """
        sql = "UPDATE TB_PRODUTOS SET PESO_GRAMAS = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [peso, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def UpdateLinkProduto(self, id_produto: int, link_novo: str) -> None:
        """Atualiza link de origem do produto.

        Args:
            id_produto: ID do produto.
            link_novo: Nova URL do produto.
        """
        sql = "UPDATE TB_PRODUTOS SET LINK_PRODUTO = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [link_novo, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def UpdateLinkImagem(self, id_produto: int, link: str | None) -> None:
        """Atualiza link da imagem do produto.

        Args:
            id_produto: ID do produto.
            link: Nova URL da imagem.
        """
        sql = "UPDATE TB_PRODUTOS SET LINK_IMAGEM = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [link, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def UpdateNome(self, id_produto: int, nome: str) -> None:
        """Atualiza nome do produto.

        Args:
            id_produto: ID do produto.
            nome: Novo nome.
        """
        sql = "UPDATE TB_PRODUTOS SET NOME_PRODUTO = :1 WHERE ID_PRODUTO = :2"
        self.cursor.execute(sql, [nome, id_produto])
        self.conexao.commit()
        self.UpdateDate(id_produto)

    def Update(
        self,
        id_produto: int,
        id_usuario_criador: int,
        nome: str,
        link_imagem: str | None,
        valor: float,
        peso: int,
        id_modalidade: int,
        id_vendedor: int | None,
    ) -> None:
        """Atualiza dados editáveis do produto para um usuário.

        Args:
            id_produto: ID do produto.
            id_usuario_criador: ID do usuário dono.
            nome: Nome atualizado.
            link_imagem: URL da imagem atualizada.
            valor: Valor atualizado em yuan.
            peso: Peso atualizado em gramas.
            id_modalidade: Modalidade logística atualizada.
            id_vendedor: Vendedor atualizado (ou None).
        """
        sql = (
            "UPDATE TB_PRODUTOS "
            "SET NOME_PRODUTO = :1, LINK_IMAGEM = :2, VALOR = :3, PESO_GRAMAS = :4, ID_MODALIDADE = :5, ID_VENDEDOR = :6, DATA_ATUALIZACAO = SYSDATE "
            "WHERE ID_PRODUTO = :7 AND ID_USUARIO_CRIADOR = :8"
        )
        self.cursor.execute(
            sql,
            [nome, link_imagem, valor, peso, id_modalidade, id_vendedor, id_produto, id_usuario_criador],
        )
        self.conexao.commit()

    def Delete(self, id_produto: int, id_usuario_criador: int) -> None:
        """Remove produto pelo ID.

        Args:
            id_produto: ID do produto.
            id_usuario_criador: ID do usuário dono.
        """
        sql = "DELETE FROM TB_PRODUTOS WHERE ID_PRODUTO = :1 AND ID_USUARIO_CRIADOR = :2"
        self.cursor.execute(sql, [id_produto, id_usuario_criador])
        self.conexao.commit()

    def ClearVendorLink(self, id_vendedor: int, id_usuario_criador: int) -> None:
        """Remove vínculo de vendedor de todos os produtos do usuário.

        Args:
            id_vendedor: ID do vendedor a desvincular.
            id_usuario_criador: ID do usuário dono dos produtos.
        """
        sql = (
            "UPDATE TB_PRODUTOS "
            "SET ID_VENDEDOR = NULL, DATA_ATUALIZACAO = SYSDATE "
            "WHERE ID_VENDEDOR = :1 AND ID_USUARIO_CRIADOR = :2"
        )
        self.cursor.execute(sql, [id_vendedor, id_usuario_criador])
        self.conexao.commit()

