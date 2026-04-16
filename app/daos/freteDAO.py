import oracledb
from app.models.frete import Frete

class FreteDAO:
    """Camada de acesso a dados para operações de frete."""

    def __init__(self, conexao: oracledb.Connection) -> None:
        """Inicializa o DAO com conexão Oracle.

        Args:
            conexao: Conexão Oracle ativa.
        """
        self.conexao = conexao
        self.cursor = conexao.cursor()

    def CreateFrete(self, frete: Frete, lista_modalidades: list[int]) -> int:
        """Cria frete e seus vínculos de modalidades.

        Args:
            frete: Entidade de frete.
            lista_modalidades: IDs de modalidades relacionadas.

        Returns:
            int: ID do frete criado.

        Raises:
            Exception: Repropaga falhas de banco após rollback.
        """
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = "INSERT INTO TB_FRETE (NOME_FRETE, SERVICO_FRETE, VALOR_100G, VALOR_100G_PLUS) VALUES (:1, :2, :3, :4) RETURNING ID_FRETE INTO :5"

            self.cursor.execute(
                sql,
                [
                    frete.nome,
                    frete.servico,
                    frete.valor_100g,
                    frete.valor_100g_plus,
                    id_novo,
                ],
            )
            id_gerado = int(id_novo.getvalue()[0])

            if lista_modalidades:
                sql_modalidade = "INSERT INTO TB_FRETE_MODALIDADE (ID_FRETE, ID_MODALIDADE) VALUES (:1, :2)"

                dados_modalidade = [(id_gerado, id_modalidade) for id_modalidade in lista_modalidades]
                self.cursor.executemany(sql_modalidade, dados_modalidade)

            self.conexao.commit()
            return id_gerado

        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def ReadAll(self) -> list[Frete]:
        """Lista todos os fretes cadastrados.

        Returns:
            list[Frete]: Coleção de fretes com modalidades associadas.
        """
        sql = "SELECT ID_FRETE, NOME_FRETE, SERVICO_FRETE, VALOR_100G, VALOR_100G_PLUS, VALOR_100G_CONVERTIDO, VALOR_100G_PLUS_CONVERTIDO FROM TB_FRETE"
        self.cursor.execute(sql)
        lista_frete: list[Frete] = []
        for linha in self.cursor:
            frete = Frete(
                id_frete=linha[0],
                nome=linha[1],
                servico=linha[2],
                valor_100g=linha[3],
                valor_100g_plus=linha[4],
            )
            if linha[5]:
                frete.valor_100g_convertido = linha[5]
                frete.valor_100g_plus_convertido = linha[6]
            frete.modalidades = self.GetModalidades(frete.id_frete)
            lista_frete.append(frete)
        return lista_frete

    def ReadModalidade(self, id_modalidade_produto: int) -> list[Frete]:
        """Lista fretes disponíveis para uma modalidade de produto.

        Args:
            id_modalidade_produto: ID da modalidade do produto.

        Returns:
            list[Frete]: Fretes vinculados à modalidade.
        """
        sql = """
        SELECT F.ID_FRETE, F.NOME_FRETE, F.SERVICO_FRETE, F.VALOR_100G, F.VALOR_100G_PLUS
        FROM TB_FRETE F
        JOIN TB_FRETE_MODALIDADE FM ON F.ID_FRETE = FM.ID_FRETE
        WHERE FM.ID_MODALIDADE = :1
        """
        self.cursor.execute(sql, [id_modalidade_produto])

        lista_resultado: list[Frete] = []
        for linha in self.cursor:
            frete = Frete(
                id_frete=linha[0],
                nome=linha[1],
                servico=linha[2],
                valor_100g=linha[3],
                valor_100g_plus=linha[4],
            )
            lista_resultado.append(frete)
        return lista_resultado

    def GetModalidades(self, id_frete: int) -> list[str]:
        """Busca nomes de modalidades vinculadas a um frete.

        Args:
            id_frete: ID do frete.

        Returns:
            list[str]: Lista de nomes de modalidades.
        """
        sql = """
            SELECT M.NOME_MODALIDADE 
            FROM TB_MODALIDADE M
            JOIN TB_FRETE_MODALIDADE FM ON M.ID_MODALIDADE = FM.ID_MODALIDADE
            WHERE FM.ID_FRETE = :1
        """
        cursor_aux = self.conexao.cursor()
        cursor_aux.execute(sql, [id_frete])
        return [row[0] for row in cursor_aux]

    def ReadAllModalidades(self) -> list[tuple[int, str]]:
        """Lista modalidades de frete cadastradas com id e nome.

        Returns:
            list[tuple[int, str]]: Colecao de (id_modalidade, nome_modalidade).
        """
        sql = "SELECT ID_MODALIDADE, NOME_MODALIDADE FROM TB_MODALIDADE ORDER BY NOME_MODALIDADE"
        self.cursor.execute(sql)
        return [(int(row[0]), str(row[1])) for row in self.cursor]
