import oracledb

from app.models.vendedor import Vendedor


class VendedorDAO:
    """Camada de acesso a dados para vendedores."""

    def __init__(self, conexao: oracledb.Connection) -> None:
        """Inicializa DAO com conexão Oracle.

        Args:
            conexao: Conexão Oracle ativa.
        """
        self.conexao = conexao
        self.cursor = conexao.cursor()

    def Create(self, vendedor: Vendedor) -> int:
        """Cria um vendedor no banco.

        Args:
            vendedor: Entidade do vendedor.

        Returns:
            int: ID do vendedor criado.

        Raises:
            Exception: Repropaga falha após rollback.
        """
        try:
            id_novo = self.cursor.var(oracledb.NUMBER)
            sql = (
                "INSERT INTO TB_VENDEDORES "
                "(NOME_VENDEDOR, NOME_LOJA, LINK_LOJA, ID_USUARIO_CRIADOR) "
                "VALUES (:1, :2, :3, :4) RETURNING ID_VENDEDOR INTO :5"
            )
            self.cursor.execute(
                sql,
                [
                    vendedor.nome,
                    vendedor.loja,
                    vendedor.link_loja,
                    vendedor.id_usuario_criador,
                    id_novo,
                ],
            )
            self.conexao.commit()
            return int(id_novo.getvalue()[0])
        except Exception as exc:
            self.conexao.rollback()
            raise exc

    def ReadAll(self, id_usuario_criador: int) -> list[Vendedor]:
        """Lista vendedores de um usuário.

        Args:
            id_usuario_criador: ID do usuário dono dos vendedores.

        Returns:
            list[Vendedor]: Vendedores pertencentes ao usuário.
        """
        sql = (
            "SELECT ID_VENDEDOR, NOME_VENDEDOR, NOME_LOJA, LINK_LOJA, ID_USUARIO_CRIADOR "
            "FROM TB_VENDEDORES "
            "WHERE ID_USUARIO_CRIADOR = :1"
        )
        self.cursor.execute(sql, [id_usuario_criador])
        lista: list[Vendedor] = []
        for linha in self.cursor:
            lista.append(
                Vendedor(
                    id_vendedor=linha[0],
                    nome=linha[1],
                    loja=linha[2],
                    link_loja=linha[3],
                    id_usuario_criador=linha[4],
                )
            )
        return lista

    def Read(self, id_vendedor: int, id_usuario_criador: int) -> Vendedor | None:
        """Busca vendedor por ID e dono.

        Args:
            id_vendedor: ID do vendedor.
            id_usuario_criador: ID do usuário dono.

        Returns:
            Vendedor | None: Vendedor encontrado ou `None`.
        """
        sql = (
            "SELECT ID_VENDEDOR, NOME_VENDEDOR, NOME_LOJA, LINK_LOJA, ID_USUARIO_CRIADOR "
            "FROM TB_VENDEDORES "
            "WHERE ID_VENDEDOR = :1 AND ID_USUARIO_CRIADOR = :2"
        )
        self.cursor.execute(sql, [id_vendedor, id_usuario_criador])
        linha = self.cursor.fetchone()
        if not linha:
            return None

        return Vendedor(
            id_vendedor=linha[0],
            nome=linha[1],
            loja=linha[2],
            link_loja=linha[3],
            id_usuario_criador=linha[4],
        )

    def Update(
        self,
        id_vendedor: int,
        id_usuario_criador: int,
        nome: str,
        loja: str,
        link_loja: str | None,
    ) -> None:
        """Atualiza vendedor do usuário.

        Args:
            id_vendedor: ID do vendedor.
            id_usuario_criador: ID do usuário dono.
            nome: Nome atualizado.
            loja: Loja atualizada.
            link_loja: URL da loja.
        """
        sql = (
            "UPDATE TB_VENDEDORES SET NOME_VENDEDOR = :1, NOME_LOJA = :2, LINK_LOJA = :3 "
            "WHERE ID_VENDEDOR = :4 AND ID_USUARIO_CRIADOR = :5"
        )
        self.cursor.execute(sql, [nome, loja, link_loja, id_vendedor, id_usuario_criador])
        self.conexao.commit()

    def Delete(self, id_vendedor: int, id_usuario_criador: int) -> None:
        """Exclui vendedor por ID e dono.

        Args:
            id_vendedor: ID do vendedor.
            id_usuario_criador: ID do usuário dono.
        """
        sql = "DELETE FROM TB_VENDEDORES WHERE ID_VENDEDOR = :1 AND ID_USUARIO_CRIADOR = :2"
        self.cursor.execute(sql, [id_vendedor, id_usuario_criador])
        self.conexao.commit()
