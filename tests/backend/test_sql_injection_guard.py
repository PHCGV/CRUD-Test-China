from app.daos.produtoDAO import ProdutoDAO
from app.daos.usuarioDAO import UsuarioDAO
from app.daos.vendedorDAO import VendedorDAO


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return None

    def __iter__(self):
        return iter([])


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_usuario_dao_read_by_username_uses_bind_parameter_for_input():
    cursor = FakeCursor()
    dao = UsuarioDAO(FakeConnection(cursor))
    payload = "' OR '1'='1"

    dao.ReadByUsername(payload)

    sql, params = cursor.executed[0]
    assert "LOWER(:1)" in sql
    assert params == [payload]


def test_produto_dao_read_uses_bind_parameters_for_identifiers():
    cursor = FakeCursor()
    dao = ProdutoDAO(FakeConnection(cursor))
    payload_produto = "1 OR 1=1"
    payload_usuario = "9 OR 1=1"

    dao.Read(payload_produto, payload_usuario)

    sql, params = cursor.executed[0]
    assert "P.ID_PRODUTO = :1" in sql
    assert "P.ID_USUARIO_CRIADOR = :2" in sql
    assert params == [payload_produto, payload_usuario]


def test_vendedor_dao_read_uses_bind_parameters_for_identifiers():
    cursor = FakeCursor()
    dao = VendedorDAO(FakeConnection(cursor))
    payload_vendedor = "2 OR 1=1"
    payload_usuario = "3 OR 1=1"

    dao.Read(payload_vendedor, payload_usuario)

    sql, params = cursor.executed[0]
    assert "ID_VENDEDOR = :1" in sql
    assert "ID_USUARIO_CRIADOR = :2" in sql
    assert params == [payload_vendedor, payload_usuario]
